import os
import sys
import time
import math
import json
import datetime
import cv2
import numpy as np
import gradio as gr

def euc_dist(arr1, point):
    square_sub = (arr1 - point) ** 2
    return np.sqrt(np.sum(square_sub, axis=1))


def preprocess_image(img, variables):
    #img = cv2.imread(img_path)
    img_ht, img_wd = img.shape[0], img.shape[1]
    img = cv2.resize(img, (variables.resize_wd, variables.resize_ht))
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # color histogram equilization
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(3, 3))
    cl1 = clahe.apply(img_gray)

    # gaussian adaptive thresholding
    img_thresh = cv2.adaptiveThreshold(
        img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 10
    )

    # adding all the computed required items in variables object
    variables.img_ht = img_ht
    variables.img_wd = img_wd
    variables.img_gray = img_gray
    variables.img_thresh = img_thresh
    variables.img = img
    return variables


def preprocess_hand_image(hand_path, hand_mask_path, variables):
    hand = cv2.imread(hand_path)
    hand_mask = cv2.imread(hand_mask_path, cv2.IMREAD_GRAYSCALE)

    top_left, bottom_right = get_extreme_coordinates(hand_mask)
    hand = hand[top_left[1] : bottom_right[1], top_left[0] : bottom_right[0]]
    hand_mask = hand_mask[top_left[1] : bottom_right[1], top_left[0] : bottom_right[0]]
    hand_mask_inv = 255 - hand_mask

    # standardizing the hand masks
    hand_mask = hand_mask / 255
    hand_mask_inv = hand_mask_inv / 255

    # making the hand background black
    hand_bg_ind = np.where(hand_mask == 0)
    hand[hand_bg_ind] = [0, 0, 0]

    # getting the img and hand dim
    hand_ht, hand_wd = hand.shape[0], hand.shape[1]

    variables.hand_ht = hand_ht
    variables.hand_wd = hand_wd
    variables.hand = hand
    variables.hand_mask = hand_mask
    variables.hand_mask_inv = hand_mask_inv
    return variables


def get_extreme_coordinates(mask):
    indices = np.where(mask == 255)
    # Extract the x and y coordinates of the pixels.
    x = indices[1]
    y = indices[0]

    # Find the minimum and maximum x and y coordinates.
    topleft = (np.min(x), np.min(y))
    bottomright = (np.max(x), np.max(y))

    return topleft, bottomright


def draw_hand_on_img(
    drawing,
    hand,
    drawing_coord_x,
    drawing_coord_y,
    hand_mask_inv,
    hand_ht,
    hand_wd,
    img_ht,
    img_wd,
):
    remaining_ht = img_ht - drawing_coord_y
    remaining_wd = img_wd - drawing_coord_x
    if remaining_ht > hand_ht:
        crop_hand_ht = hand_ht
    else:
        crop_hand_ht = remaining_ht

    if remaining_wd > hand_wd:
        crop_hand_wd = hand_wd
    else:
        crop_hand_wd = remaining_wd

    hand_cropped = hand[:crop_hand_ht, :crop_hand_wd]
    hand_mask_inv_cropped = hand_mask_inv[:crop_hand_ht, :crop_hand_wd]

    drawing[
        drawing_coord_y : drawing_coord_y + crop_hand_ht,
        drawing_coord_x : drawing_coord_x + crop_hand_wd,
    ][:, :, 0] = (
        drawing[
            drawing_coord_y : drawing_coord_y + crop_hand_ht,
            drawing_coord_x : drawing_coord_x + crop_hand_wd,
        ][:, :, 0]
        * hand_mask_inv_cropped
    )
    drawing[
        drawing_coord_y : drawing_coord_y + crop_hand_ht,
        drawing_coord_x : drawing_coord_x + crop_hand_wd,
    ][:, :, 1] = (
        drawing[
            drawing_coord_y : drawing_coord_y + crop_hand_ht,
            drawing_coord_x : drawing_coord_x + crop_hand_wd,
        ][:, :, 1]
        * hand_mask_inv_cropped
    )
    drawing[
        drawing_coord_y : drawing_coord_y + crop_hand_ht,
        drawing_coord_x : drawing_coord_x + crop_hand_wd,
    ][:, :, 2] = (
        drawing[
            drawing_coord_y : drawing_coord_y + crop_hand_ht,
            drawing_coord_x : drawing_coord_x + crop_hand_wd,
        ][:, :, 2]
        * hand_mask_inv_cropped
    )

    drawing[
        drawing_coord_y : drawing_coord_y + crop_hand_ht,
        drawing_coord_x : drawing_coord_x + crop_hand_wd,
    ] = (
        drawing[
            drawing_coord_y : drawing_coord_y + crop_hand_ht,
            drawing_coord_x : drawing_coord_x + crop_hand_wd,
        ]
        + hand_cropped
    )
    return drawing


def draw_masked_object(
    variables, object_mask=None, skip_rate=5, black_pixel_threshold=10
):
    """
    skip_rate is not provided via variables because this function does not
    know it is drawing object or background or an entire image
    """
    print("Skip Rate: ", skip_rate)
    # if there is object mask, then the img_thresh will only correspond to the mask provided
    img_thresh_copy = variables.img_thresh.copy()
    if object_mask is not None:
        # get the object and its background indices
        object_mask_black_ind = np.where(object_mask == 0)
        object_ind = np.where(object_mask == 255)

        # make area other than object white
        img_thresh_copy[object_mask_black_ind] = 255

    selected_ind = 0
    n_cuts_vertical = int(math.ceil(variables.resize_ht / variables.split_len))
    n_cuts_horizontal = int(math.ceil(variables.resize_wd / variables.split_len))

    # cut the image into grids
    grid_of_cuts = np.array(np.split(img_thresh_copy, n_cuts_horizontal, axis=-1))
    grid_of_cuts = np.array(np.split(grid_of_cuts, n_cuts_vertical, axis=-2))
    print(grid_of_cuts.shape)

    # find grids where there is atleast one black pixel
    # as only these grids will be drawn
    cut_having_black = (grid_of_cuts < black_pixel_threshold) * 1
    cut_having_black = np.sum(np.sum(cut_having_black, axis=-1), axis=-1)
    cut_black_indices = np.array(np.where(cut_having_black > 0)).T

    counter = 0
    while len(cut_black_indices) > 1:
        selected_ind_val = cut_black_indices[selected_ind].copy()
        range_v_start = selected_ind_val[0] * variables.split_len
        range_v_end = range_v_start + variables.split_len
        range_h_start = selected_ind_val[1] * variables.split_len
        range_h_end = range_h_start + variables.split_len

        temp_drawing = np.zeros((variables.split_len, variables.split_len, 3))
        temp_drawing[:, :, 0] = grid_of_cuts[selected_ind_val[0]][selected_ind_val[1]]
        temp_drawing[:, :, 1] = grid_of_cuts[selected_ind_val[0]][selected_ind_val[1]]
        temp_drawing[:, :, 2] = grid_of_cuts[selected_ind_val[0]][selected_ind_val[1]]

        variables.drawn_frame[range_v_start:range_v_end, range_h_start:range_h_end] = (
            temp_drawing
        )

        hand_coord_x = range_h_start + int(variables.split_len / 2)
        hand_coord_y = range_v_start + int(variables.split_len / 2)
        drawn_frame_with_hand = draw_hand_on_img(
            variables.drawn_frame.copy(),
            variables.hand.copy(),
            hand_coord_x,
            hand_coord_y,
            variables.hand_mask_inv.copy(),
            variables.hand_ht,
            variables.hand_wd,
            variables.resize_ht,
            variables.resize_wd,
        )

        # delete the selected ind from the d_array
        cut_black_indices[selected_ind] = cut_black_indices[-1]
        cut_black_indices = cut_black_indices[:-1]

        del selected_ind

        # select the next new index
        euc_arr = euc_dist(cut_black_indices, selected_ind_val)
        selected_ind = np.argmin(euc_arr)

        counter += 1
        if counter % skip_rate == 0:
            variables.video_object.write(drawn_frame_with_hand)

        if counter % 40 == 0:
            print("len of black indices: ", len(cut_black_indices))

    if object_mask is not None:
        variables.drawn_frame[:, :, :][object_ind] = variables.img[object_ind]
    else:
        variables.drawn_frame[:, :, :] = variables.img


def draw_whiteboard_animations(
    img, mask_path, hand_path, hand_mask_path, save_video_path, variables
):
    if mask_path is not None:
        object_mask_exists = True
    else:
        object_mask_exists = False

    # reading the image and converting it to grayscale,
    # computing clahe and later therholding
    variables = preprocess_image(img=img, variables=variables)

    # reading hand image and preprocess
    variables = preprocess_hand_image(
        hand_path=hand_path, hand_mask_path=hand_mask_path, variables=variables
    )

    # calculate how much time it takes to make video for 1 image
    start_time = time.time()

    # defining the video object
    variables.video_object = cv2.VideoWriter(
        save_video_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        variables.frame_rate,
        (variables.resize_wd, variables.resize_ht),
    )

    # creating an emtpy frame and select 0th index as the starting point to draw
    variables.drawn_frame = np.zeros(variables.img.shape, np.uint8) + np.array(
        [255, 255, 255], np.uint8
    )

    if object_mask_exists:

        # reading the object masks
        with open(mask_path) as file:
            object_masks = json.load(file)

        background_mask = (
            np.zeros((variables.resize_ht, variables.resize_wd), dtype=np.uint8) + 255
        )

        for object in object_masks["shapes"]:
            # Create an empty mask array
            object_mask = np.zeros((variables.img_ht, variables.img_wd), dtype=np.uint8)

            # Get the object points as a list of tuples
            object_points = np.array(object["points"], dtype=np.int32)
            object_points = np.expand_dims(object_points, axis=0)

            # Fill the polygon with white color (255) on the mask array using cv2
            cv2.fillPoly(object_mask, object_points, 255)

            # resizing the object_mask
            object_mask = cv2.resize(
                object_mask, (variables.resize_wd, variables.resize_ht)
            )

            # get the object and its background indices
            object_ind = np.where(object_mask == 255)

            # remove the object from backgrond mask
            background_mask[object_ind] = 0

            # create animation for the selected object
            draw_masked_object(
                variables=variables,
                object_mask=object_mask,
                skip_rate=variables.object_skip_rate,
            )

        # now draw the last remaing background part
        """
        # update the split len for background part by which the 
        # area covered in one loop iteration will be much larger
        """
        # Optional:
        print("Drawing the blakground region..")
        variables.split_len = 20
        draw_masked_object(
            variables=variables,
            object_mask=background_mask,
            skip_rate=variables.bg_object_skip_rate,
        )
    else:
        #variables.split_len = 15
        #variables.object_skip_rate = 8
        # draw the entire image without any mask
        draw_masked_object(
            variables=variables,
            skip_rate=variables.object_skip_rate,
        )

    # Ending the video with original original image
    for i in range(variables.frame_rate * variables.end_gray_img_duration_in_sec):
        variables.video_object.write(variables.img)

    # Calculating the total execution time
    end_time = time.time()
    print("total time: ", end_time - start_time)

    # closing the video object
    variables.video_object.release()

def find_nearest_res(given):
    arr = np.array([640, 360, 480, 1280, 720, 1920, 1080, 2560, 1440, 3840, 2160, 7680, 4320])
    idx = (np.abs(arr - given)).argmin()  # Find index of minimum difference
    return arr[idx]

class AllVariables:
    def __init__(
        self,
        frame_rate=None,
        resize_wd=None,
        resize_ht=None,
        split_len=None,
        object_skip_rate=None,
        bg_object_skip_rate=None,
        end_gray_img_duration_in_sec=None,
    ):
        self.frame_rate = frame_rate
        self.resize_wd = resize_wd
        self.resize_ht = resize_ht
        self.split_len = split_len
        self.object_skip_rate = object_skip_rate
        self.bg_object_skip_rate = bg_object_skip_rate
        self.end_gray_img_duration_in_sec = end_gray_img_duration_in_sec

def common_divisors(num1, num2):
    """
    Finds all common divisors of two numbers, stores them in a list,
    and returns the list sorted in ascending order.
    """
    divisors1 = []
    divisors2 = []
    common_divs = []

    # Find divisors of num1
    for i in range(1, num1 + 1):
        if num1 % i == 0:
            divisors1.append(i)

    # Find divisors of num2
    for i in range(1, num2 + 1):
        if num2 % i == 0:
            divisors2.append(i)

    # Find common divisors
    for divisor in divisors1:
        if divisor in divisors2:
            common_divs.append(divisor)

    common_divs.sort()  # Sort the list in ascending order
    return common_divs


def main_func(image, split_len, frame_rate, object_skip_rate, bg_object_skip_rate, end_gray_img_duration_in_sec):
    if image is not None:
        # selected settings
        #split_len = 10
        #frame_rate = 25
        #object_skip_rate = 8
        #bg_object_skip_rate = 14
        #end_gray_img_duration_in_sec = 2

        # path related things
        script_path = os.path.abspath(sys.argv[0])
        last_backslash_index = script_path.rfind("\\") # For windows
        last_frdslash_index = script_path.rfind("/") # For linux & other OS
        if last_backslash_index != -1:
            script_path = script_path[:last_backslash_index]
        if last_frdslash_index != -1:
            script_path = script_path[:last_frdslash_index]
        save_path = os.path.join(script_path, "./save_videos")
        mask_path = None # To be added later
        hand_path = os.path.join(script_path, "./images/drawing-hand.png")
        hand_mask_path = os.path.join(script_path,"./images/hand-mask.png")

        # video save path
        now = datetime.datetime.now()
        current_time = str(now.strftime("%H%M%S"))
        video_save_name = "vid" + "-" + current_time + ".mp4"
        save_video_path = os.path.join(save_path, video_save_name)
        print("save_video_path: ", save_video_path)

        # Get image width & height. If the resolution is not standard & split length is not a common divisor, get the nearest standard res
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        img_ht, img_wd = image_bgr.shape[0], image_bgr.shape[1]
        if img_ht % split_len != 0:
            img_ht = find_nearest_res(img_ht)
            split_len = 10
        if img_wd % split_len != 0:
            img_wd = find_nearest_res(img_wd)
            split_len = 10
        print(f"image width: {img_wd} x image height: {img_ht}")

        # constants and variables object
        variables = AllVariables(
            frame_rate = frame_rate,  # frame rate for the output video
            resize_wd = img_wd,  # output video width
            resize_ht = img_ht,  # output video height
            split_len = split_len,  # the image is devided into grids. When split_len = 10, the image is devided as: img_ht/10, img_wd/10
            object_skip_rate = object_skip_rate,  # when drawing, 8 pixels colored will be saved together in the video
            # increase this number to make the video runtime smaller (draws faster)
            bg_object_skip_rate = bg_object_skip_rate,  # assuming background region is larger, hence increasing the skip rate
            end_gray_img_duration_in_sec = end_gray_img_duration_in_sec,  # the last few secs of the video, for every image will have the entire original image shown as is
        )

        # invoking the drawing function
        draw_whiteboard_animations(
            image_bgr, mask_path, hand_path, hand_mask_path, save_video_path, variables
        )
        return save_video_path
    else:
        return None

def process_image(image, split_len):
    # Get image width & height. If the resolution is not standard & split length is not a common divisor, get the nearest standard res
    image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    img_ht, img_wd = image_bgr.shape[0], image_bgr.shape[1]
    if img_ht % split_len != 0:
        img_ht = find_nearest_res(img_ht)
        split_len = 10
    if img_wd % split_len != 0:
        img_wd = find_nearest_res(img_wd)
        split_len = 10
    hcf_list = common_divisors(img_ht, img_wd)
    return gr.update(value=img_wd), gr.update(value=img_ht), gr.update(choices=hcf_list, value=split_len)


# The UI part
ui = gr.Blocks()
with ui:
    gr.Markdown(
    """
    # Image to Sketch Video!
    Select an image and Submit to see the magic. Please visit [daslearning.in](https://daslearning.in/) for more topics.
    """
    )
    with gr.Row() as ioRow:
        with gr.Column(scale=1) as inputCol:
            image_input = gr.Image(type="numpy")
        with gr.Column(scale=1) as outputCol:
            video_output = gr.Video(label="Generated Video") # TO be fixed 
    with gr.Row() as paramRow:
        img_wd = gr.Number(label="Image Width", info="best value is auto decided")
        img_ht = gr.Number(label="Image Height", info="best value is auto decided")
        split_len = gr.Dropdown(
            [5, 10, 20], value=5, label="Split Len", info="Higher number for speedier sketch!"
        )
        frame_rate = gr.Number(value=25, label="Frame Rate", info="default: 25")
        obj_skip_rt = gr.Number(value=8, label="Object Skip Rate", info="should be lower than background skip rate, default: 8")
        bg_skip_rt = gr.Number(value=14, label="Background Skip Rate", info="higher number than object skip rate, default: 14")
        clr_img_duration = gr.Number(value=2, label="Colour Image Duration", info="No of Seconds to display the colour image after the sketch")
    image_button = gr.Button("Submit")

    image_input.upload(
        fn=process_image,
        inputs=[image_input, split_len],
        outputs=[img_wd, img_ht, split_len,]
    )

    image_button.click(
        fn=main_func,
        inputs=[image_input, split_len, frame_rate, obj_skip_rt, bg_skip_rt, clr_img_duration],
        outputs=video_output,
    )

ui.launch()

# End