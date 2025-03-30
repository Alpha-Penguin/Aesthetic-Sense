import caffe
import os
import glob
import cv2
import piexif
import piexif.helper
import json

import caffe
import numpy as np
from caffe.proto import caffe_pb2


# AVA
AVA_ROOT = 'C:\\Users\\tranj\\OneDrive\\Desktop\\Aesthetic-Sense\\'
IMAGE_MEAN= AVA_ROOT + 'mean_AADB_regression_warp256.binaryproto'
DEPLOY = AVA_ROOT + 'initModel.prototxt'
MODEL_FILE = AVA_ROOT + 'initModel.caffemodel'
IMAGE_FILE = AVA_ROOT + "*.jpg"
IMAGE_FILE_JPEG = AVA_ROOT + "*.jpeg"


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
print("Shape mean_array : ", mean_array.shape)
print("Shape net : ", net.blobs[input_layer].data.shape)
net.blobs[input_layer].reshape(1,        # batch size
                              3,         # channel
                              IMAGE_WIDTH, IMAGE_HEIGHT)  # image size
transformer = caffe.io.Transformer({input_layer: net.blobs[input_layer].data.shape})
transformer.set_mean(input_layer, mean_array)
transformer.set_transpose(input_layer, (2,0,1))

'''
Making predicitions
'''
#Reading image paths
test_img_paths = [img_path for img_path in glob.glob(IMAGE_FILE)]
test_img_paths += [img_path for img_path in glob.glob(IMAGE_FILE_JPEG)]
print(test_img_paths)

#Making predictions
best_image = ''
best_score = 0.0

def predict_image(img_path):
    img = cv2.imread(img_path, cv2.IMREAD_COLOR)
    img = transform_img(img, img_width=IMAGE_WIDTH, img_height=IMAGE_HEIGHT)

    #Show Image with GUI
    cv2.imshow('image',img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    net.blobs[input_layer].data[...] = transformer.preprocess(input_layer, img)
    out = net.forward()

    # Loop through the dictionary and print key-value pairs using .format()
    for key in out:
        print("Key: {} => Value: {}".format(key, out[key][0][0]))

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

#def predict_multiple_images(test_img_paths, best_score):
#    for img_path in test_img_paths:
#        img_path, pred_score, out = predict_image(img_path)
#        if pred_score > best_score:
#            print("Better score!")
#            best_score = pred_score
#            best_image = img_path
#    print("Best image, based only on fc11_score = ", best_image)

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


#predict_multiple_images(test_img_paths, best_score)
print("done")
#Testing
#custom_dict = {
#    'fc9_VividColor': 0.999999999,
#    'fc9_Symmetry': 0.2,
#    'fc9_RuleOfThirds': 0.3,
#    'fc11_score': 0.4,
#    'fc9_MotionBlur': -0.5,
#    'fc9_Repetition': 0.6,
#    'fc9_Content': 0.7,
#    'fc9_Light': 0.8,
#    'fc9_Object': -0.9,
#    'fc9_ColorHarmony': 0.10,
#    'fc9_DoF': 0.1,
#    'fc9_BalancingElement': 0.12
#}



#exif_bytes = piexif.dump(exif_dict)
#piexif.insert(exif_bytes, "C:\\Users\\tranj\\OneDrive\\Desktop\\Aesthetic-Sense\\test1.jpg")

#exif_dict = piexif.load("C:\\Users\\tranj\\OneDrive\\Desktop\\Aesthetic-Sense\\Red.jpg")

#try:
#    user_comment = piexif.helper.UserComment.load(exif_dict["Exif"][piexif.ExifIFD.UserComment])
#except:
#    user_comment = None

#rating = exif_dict["0th"].get(18246, None)
#rating_percent = exif_dict["0th"].get(18249, None)  # Preferred

#print(exif_dict)
#print(user_comment)
#print(rating)
#print(rating_percent)

#if user_comment is not None:
#    # Convert string to dictionary
#    dict_obj = json.loads(user_comment)
#    print(dict_obj)
#    print(dict_obj['fc9_VividColor'])#

#    for key in dict_obj:
#            print("Key: {} => Value: {}".format(key, dict_obj[key]))



#exif_dict = piexif.load("C:\\Users\\tranj\\OneDrive\\Desktop\\Aesthetic-Sense\\Red.jpg")
#rating = exif_dict["0th"].get(18246, None)
#print(rating)

#rating_percent = exif_dict["0th"].get(18249, None)  
#print("RP" + str(rating_percent))

#img_path = "C:\\Users\\tranj\\OneDrive\\Desktop\\Aesthetic-Sense\\badqual2.jpg"
#predict_image(img_path)