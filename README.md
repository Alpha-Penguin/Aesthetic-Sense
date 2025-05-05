# Aesthetic-Sense
Final Year Project

### Pre trained Model
This project uses a pre-trained model found at: https://github.com/aimerykong/deepImageAestheticsAnalysis/tree/master

Final file (initModel.caffemodel) related to this model can be downloaded from: https://drive.google.com/file/d/1p3FfvqvSghd80ANyWS-Fu3ReJFx7D5a4/view?usp=drive_link

### Features
- Analyse images using a pre-trained AI model
- Rate images based on aesthetic attributes
- Save scores in JPEG metadata (Exif)
- Filter images by rating
- View individual image scores/rating and feedback

### Installation
App can be run using the exe file found at: https://drive.google.com/file/d/1zcM5a51NLG5j3BE1NCIPCrG0NeYfGRkn/view?usp=sharing

Or by running source code that requires setup

### Setup without environment.yml
- Install Miniconda
- Install Prerequisites for Caffe: Visual Studio 2015 and Cmake 3.7.2
- Create envs in Miniconda: conda create -n “env_name” python=3.5.3
- Install Caffe: https://github.com/BVLC/caffe/tree/windows

- pip install all required packages

### Setup with environment.yml
- Install Miniconda
- Install Prerequisites for Caffe: Visual Studio 2015 and Cmake 3.7.2
- Create envs in Miniconda: conda env create -f environment.yml
- Install Caffe: https://github.com/BVLC/caffe/tree/windows


If you want to, Create exe file: pyinstaller --onefile --add-data "mean_AADB_regression_warp256.binaryproto;." --add-data "initModel.prototxt;." --add-data "initModel.caffemodel;." --add-data "fontlist-v300.json;." AestheticSense.py
