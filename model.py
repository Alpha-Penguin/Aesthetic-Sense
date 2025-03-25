import caffe
import os
import glob
import cv2
import caffe
import numpy as np
from caffe.proto import caffe_pb2


# AVA
AVA_ROOT = 'C:\\Users\\tranj\\OneDrive\\Desktop\\Aesthetic-Sense\\'
IMAGE_MEAN= AVA_ROOT + 'mean_AADB_regression_warp256.binaryproto'
DEPLOY = AVA_ROOT + 'initModel.prototxt'
MODEL_FILE = AVA_ROOT + 'initModel.caffemodel'
IMAGE_FILE = AVA_ROOT + "*jpg"
IMAGE_FILE_JPEG = AVA_ROOT + "*jpeg"


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
    print(img_path, '\t', pred_score)

    return img_path, pred_score

def predict_multiple_images(test_img_paths, best_score):
    for img_path in test_img_paths:
        img_path, pred_score = predict_image(img_path)
        if pred_score > best_score:
            print("Better score!")
            best_score = pred_score
            best_image = img_path
    print("Best image, based only on fc11_score = ", best_image)

#predict_multiple_images(test_img_paths, best_score)