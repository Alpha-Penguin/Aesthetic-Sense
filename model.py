import os
import glob
import cv2
import piexif
import piexif.helper
import json
import sys


# Function for EXE (PyInstaller) so files are accessed via correct path due to how
# the Exe uses temp folders 
def resourcePath(relativePath):
    try:
        basePath = sys._MEIPASS
    except Exception:
        basePath = os.path.abspath(".")
    
    return os.path.join(basePath, relativePath)

os.environ["MPLCONFIGDIR"] = resourcePath(".")

import caffe
import numpy as np
from caffe.proto import caffe_pb2

# Loading model files using resourcePath
IMAGE_MEAN = resourcePath('mean_AADB_regression_warp256.binaryproto')
DEPLOY = resourcePath('initModel.prototxt')
MODEL_FILE = resourcePath('initModel.caffemodel')

caffe.set_mode_cpu()

#Size of images
IMAGE_WIDTH = 227
IMAGE_HEIGHT = 227

input_layer = 'imgLow'

'''
Image processing helper function
'''
def transform_img(img, img_width=IMAGE_WIDTH, img_height=IMAGE_HEIGHT):
    #Image Resizing
    img = cv2.resize(img, (img_width, img_height), interpolation = cv2.INTER_CUBIC)
    return img

'''
Reading mean image, caffe model and its weights
'''
#Read mean image
mean_blob = caffe_pb2.BlobProto()
with open(IMAGE_MEAN, "rb") as f:
    mean_blob.ParseFromString(f.read())
mean_array = np.asarray(mean_blob.data, dtype=np.float32).reshape(
    (mean_blob.channels, mean_blob.height, mean_blob.width))

#Cropping mean image to correct dimensions for model
mean_array = mean_array[:, 15:242, 15:242]

#Read model architecture and trained model's weights
net = caffe.Net(DEPLOY, caffe.TEST, weights=MODEL_FILE)


#Define image transformers
net.blobs[input_layer].reshape(1,        # batch size
                              3,         # channel
                              IMAGE_WIDTH, IMAGE_HEIGHT)  # image size
transformer = caffe.io.Transformer({input_layer: net.blobs[input_layer].data.shape})
transformer.set_mean(input_layer, mean_array)
transformer.set_transpose(input_layer, (2,0,1))

def predict_image(img_path):
    img = cv2.imread(img_path, cv2.IMREAD_COLOR)
    img = transform_img(img, img_width=IMAGE_WIDTH, img_height=IMAGE_HEIGHT)

    net.blobs[input_layer].data[...] = transformer.preprocess(input_layer, img)
    out = net.forward()

    pred_score = out['fc11_score'][0][0]
    
    exif_dict = piexif.load(img_path)
    rating_percent = int(pred_score*100)
    exif_dict['0th'][piexif.ImageIFD.RatingPercent] = rating_percent
    rating = calculate_rating(rating_percent)
    exif_dict['0th'][piexif.ImageIFD.Rating] = rating

    custom_dict = calculate_custom_dict(out)
    user_comment = json.dumps(custom_dict)
    user_comment = piexif.helper.UserComment.dump(user_comment)
    exif_dict["Exif"][piexif.ExifIFD.UserComment] = user_comment

    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, img_path)

    return img_path

def calculate_rating(rating_percent):
    if rating_percent <= 12:
        rating = 1
    elif rating_percent <= 37:
        rating = 2
    elif rating_percent <= 62:
        rating = 3
    elif rating_percent <= 87:
        rating = 4
    else:
        rating = 5
    return rating

def calculate_rating_percent(rating):
    if rating == 1:
        rating_percent = 10
    elif rating == 2:
        rating_percent = 35
    elif rating == 3:
        rating_percent = 60
    elif rating == 4:
        rating_percent = 80
    else:
        rating_percent = 95
    return rating_percent

def calculate_custom_dict(out):
    custom_dict = {
    'fc9_VividColor': float(out['fc9_VividColor'][0][0]),
    'fc9_Symmetry': float(out['fc9_Symmetry'][0][0]),
    'fc9_RuleOfThirds': float(out['fc9_RuleOfThirds'][0][0]),
    'fc11_score': float(out['fc11_score'][0][0]),
    'fc9_MotionBlur': float(out['fc9_MotionBlur'][0][0]),
    'fc9_Repetition': float(out['fc9_Repetition'][0][0]),
    'fc9_Content': float(out['fc9_Content'][0][0]),
    'fc9_Light': float(out['fc9_Light'][0][0]),
    'fc9_Object': float(out['fc9_Object'][0][0]),
    'fc9_ColorHarmony': float(out['fc9_ColorHarmony'][0][0]),
    'fc9_DoF': float(out['fc9_DoF'][0][0]),
    'fc9_BalancingElement': float(out['fc9_BalancingElement'][0][0])
    }

    return custom_dict

def save_changes(img_path, rating):
    exif_dict = piexif.load(img_path)
    rating_percent = calculate_rating_percent(rating)
    exif_dict['0th'][piexif.ImageIFD.RatingPercent] = rating_percent
    exif_dict['0th'][piexif.ImageIFD.Rating] = rating
    exif_dict['0th'][piexif.ImageIFD.RatingPercent] = 10

    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, img_path)
