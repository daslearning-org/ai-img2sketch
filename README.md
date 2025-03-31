# Image to WhiteBoard Sketch Video Generation
Let's use Python with NumPy & Cv2 to generate this videos. This do not require any fancy pre-trained AI models. This one uses NumPy and OpenCV to do the job. Please visit [daslearning.in](https://daslearning.in) for more.

# Demo
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
