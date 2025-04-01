# 📷 Image to WhiteBoard Sketch Animation Video Generation
Simply upload your image and see the magic after clicking the `Submit` button. This do not require any fancy pre-trained AI models. This one uses NumPy and OpenCV to do the job. You can visit my website [daslearning.in](https://daslearning.in) for more topics.

# 📽️ Demo
To be added later

## ⚒️ Automatic Installation
```bash
git clone https://github.com/daslearning-org/ai-img2sketch.git
cd ai-img2sketch
pip install -r requirements.txt
```

## ⚒️ Manual Installation
```bash
git clone https://github.com/daslearning-org/ai-img2sketch.git
cd ai-img2sketch
python -m venv .env
source .env/bin/activate # Optional if you do not want virtual environment
pip install numpy
pip install opencv-python
pip install gradio
```

## 🤖 Known Issues
1. Video codec `mp4v` might not be compatible with browser or some video players (The default codec of this app)
    > Fixes (Tested on Debian based Linux only): The gradio's video module will try to use ffmpeg to convert the video automatically.
    ```bash
    # Install FFMPEG related packages
    sudo apt update
    sudo apt install ffmpeg libavformat-dev libavcodec-dev libswscale-dev -y
    ```

## ▶️ Run the App
```bash
python img2SketchUI.py
```

## 📝 Next Plan
* Users can manually change the required video resolution (current one does the best by taking the most suitable resolution for a given image).

## 🚀 Future Plan
Make this project more powerful and include some of the components like (though current solution works realy fast)
* [CuPy](https://cupy.dev/), the NumPy alternative with GPU support
* [CV-CUDA](https://github.com/CVCUDA/CV-CUDA), the OpenCV with GPU

## 🙏🏻 Acknowledgements
* I would like to thank [Yogendra Yatnalkar](https://github.com/yogendra-yatnalkar/storyboard-ai) for solving the complex math on images and sharing the python code.
