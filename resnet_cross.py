import numpy as np
import os
from matplotlib import pyplot as plt
from tensorflow import keras
import tensorflow as tf
from keras.models import Sequential
from keras.constraints import max_norm
from keras.layers import Layer, Conv2D,Reshape,multiply,Permute, BatchNormalization, AveragePooling2D, Flatten, Dense, Dropout, Activation
from keras.layers import Conv1D,DepthwiseConv2D, SeparableConv2D, Attention, GlobalAveragePooling2D,MaxPooling2D
from keras import backend as K
from keras import layers
from sklearn.utils import shuffle
from sklearn.model_selection import train_test_split

# data process functions

def prepro_x(x: np.array, downrate : int) -> np.array:
    """down sampling from different time points to augmentate data"""

    x_agu = np.zeros((downrate*x.shape[0], x.shape[1], int(x.shape[2]/downrate)))
    for k in range(len(x)):
        for i in range(downrate):
            x_agu[downrate*k + i] = x[k, :, i:downrate*int(x.shape[2]/downrate):downrate]
    return x_agu

def getdata(downrate : int) -> np.array:
    """read data, downsample, split train set into train set and validation set"""

    x_train_ori = np.load(r'cross_train_set_nor.npy')
    x_test1_ori = np.load(r'cross_test1_set_nor.npy')
    x_test2_ori = np.load(r'cross_test2_set_nor.npy')
    x_test3_ori = np.load(r'cross_test3_set_nor.npy')

    x_train_agu = np.array(prepro_x(x_train_ori, downrate), dtype=np.float32)
    x_test1_agu  = np.array(prepro_x(x_test1_ori, downrate), dtype=np.float32)
    x_test2_agu  = np.array(prepro_x(x_test2_ori, downrate), dtype=np.float32)
    x_test3_agu  = np.array(prepro_x(x_test3_ori, downrate), dtype=np.float32)

    y_train0 = np.eye(4)[np.repeat(np.load(r'cross_train_label.npy') - 1, downrate)]
    y_test1  = np.eye(4)[np.repeat(np.load(r'cross_test1_label.npy') - 1, downrate)]
    y_test2  = np.eye(4)[np.repeat(np.load(r'cross_test2_label.npy') - 1, downrate)]
    y_test3  = np.eye(4)[np.repeat(np.load(r'cross_test3_label.npy') - 1, downrate)]

    # reshape: numbers, channels, samplingrate, 1
    x_train0 = x_train_agu.reshape(x_train_agu.shape[0], x_train_agu.shape[1], x_train_agu.shape[2], 1)
    x_test1   = x_test1_agu.reshape(x_test1_agu.shape[0], x_test1_agu.shape[1], x_test1_agu.shape[2], 1)
    x_test2   = x_test2_agu.reshape(x_test2_agu.shape[0], x_test2_agu.shape[1], x_test2_agu.shape[2], 1)
    x_test3   = x_test3_agu.reshape(x_test3_agu.shape[0], x_test3_agu.shape[1], x_test3_agu.shape[2], 1)
    
    x_train, x_val, y_train, y_val = train_test_split(x_train0, y_train0, test_size=0.2, random_state=42)
    
    return x_train, y_train, x_val, y_val, x_test1, y_test1, x_test2, y_test2, x_test3, y_test3

# model functions

def Model2(input_shape):

    #Substituting 2D by 1D convolutions in order to convolved over the temporal dimension first.
    # Convolution over the temporal domain
    inputs = keras.Input(shape=input_shape, name="img")
    x = Conv1D(4, 3, activation="relu", padding="same")(inputs)
    x = Conv1D(8, 3, activation="relu", padding="same")(x)
    x = BatchNormalization(axis = -1)(x)
    block_1_output = MaxPooling2D(3)(x)

    x = Conv1D(8, 3, activation="relu", padding="same")(block_1_output)
    x = Conv1D(8, 3, activation="relu", padding="same")(x)
    x = BatchNormalization(axis = -1)(x)
    block_2_output = layers.add([x, block_1_output])

    x = Conv1D(8, 3, activation="relu", padding="same")(block_1_output)
    x = Conv1D(8, 3, activation="relu", padding="same")(x)
    x = BatchNormalization(axis = -1)(x)
    block_3_output = layers.add([x, block_1_output])

    # Convolution over the spatial domain
    x = Conv2D(8, (3,1), activation="relu")(block_3_output)
    x = GlobalAveragePooling2D()(x)
    x = Dense(64, activation="relu")(x)
    x = Dropout(0.5)(x)
    outputs = Dense(4,activation = 'softmax',
                    #kernel_regularizer = 0.001,
                    kernel_constraint = max_norm(0.25))(x)

    model = keras.Model(inputs, outputs, name="toy_resnet")
    return model


def myGenerator(x : np.array, y : np.array, batch_size : int):
    """set generator for model fitting to load data piece by piece
        OOM can be avoided in this way"""

    total_size = len(x)
    while 1:
        for i in range(total_size // batch_size):
            yield x[i*batch_size:(i+1)*batch_size], y[i*batch_size:(i+1)*batch_size]


def train_eegnet(X : np.array, Y : np.array, X_val : np.array, Y_val : np.array, batch_size : int, nb_epoch : int) :
    """Train model, save model, plot training history, save training history"""

    # !!!!!!!!change the path every run!!!!!!!!!! better use a breakpoint here
    model_savepath = r'testmodel_cat1.tf'    
    trainloss_savepath = r'trainloss_cat1.npy'
    validloss_savepath = r'validloss_cat1.npy'
    checkpoint_path = r'bestmodel_cat1.tf'
    # Training  
    checkpoint_dir = os.path.dirname(checkpoint_path)
    checkpoint = keras.callbacks.ModelCheckpoint(filepath = checkpoint_path,
                                                monitor='val_loss',
                                                verbose = 1,
                                                save_best_only=True,
                                                save_freq= 'epoch') 
    eegnet_model.compile(loss = 'categorical_crossentropy',
                        optimizer = 'adam')
                        #metrics = ['categorical_accuracy']
    
    history = eegnet_model.fit_generator(myGenerator(X, Y, batch_size),
                                        steps_per_epoch = len(X)//(batch_size), 
                                        validation_data = (X_val, Y_val),                            
                                        epochs     = nb_epoch, 
                                        verbose    = 1,
                                        callbacks  = [checkpoint])                

    train_loss = history.history['loss']
    val_loss = history.history['val_loss']
    epochs = range(1, len(train_loss) + 1)

    # plot the training and validation loss
    plt.plot(epochs, train_loss, '-', color = 'red',label='Training loss')
    plt.plot(epochs, val_loss, '--', color ='green',label='Validation loss')
    plt.title('Training and validation loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()
    plt.show()

    # save the final trained model and history
    eegnet_model.save(model_savepath)
    np.save(trainloss_savepath, train_loss)
    np.save(validloss_savepath, val_loss)

    return history, checkpoint_path


def predict_eegnet(model_loadpath, x_test, y_test):
    """predict"""

    model = keras.models.load_model(model_loadpath)
    predictions = np.zeros((len(y_test)))

    for i in range(len(x_test)):
        probability = model.predict(x_test[i:i+1])
        predictions[i] = probability.argmax(axis = -1)

    label = np.array([one_label.tolist().index(1) for one_label in y_test], dtype = np.float64)
    pre_accuracy = np.sum(label == predictions) / len(predictions)
    print(predictions)
    print(pre_accuracy)

    return predictions, pre_accuracy


if __name__ == '__main__':

    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    print(tf.config.list_physical_devices('GPU'))
    tf.config.optimizer.set_experimental_options({'layout_optimizer': False})
    config = tf.compat.v1.ConfigProto()
    config.gpu_options.per_process_gpu_memory_fraction = 0.5  # programs can only use up to 50% of a given gpu memory
    config.gpu_options.allow_growth = False  
    sess = tf.compat.v1.Session(config = config)

    downrate = 8 #downsampling rate
    x_train, y_train, x_val, y_val, x_test1, y_test1, x_test2, y_test2, x_test3, y_test3 = getdata(downrate)
    input_shape = (x_train.shape[1], x_train.shape[2], 1) #inputshape = (channels, time, 1) e.i.(248, 35624, 1)
    K.clear_session()
    # built model
    nb_classes = 4  #classification numbers
    eegnet_model = Model2(input_shape)
    # print model
    eegnet_model.summary()
    # train model
    history, modelpath = train_eegnet(x_train, y_train, x_val, y_val, batch_size = 8, nb_epoch = 100)
    # predict
    y_pre1, acc1 = predict_eegnet(modelpath, x_test1, y_test1)
    y_pre2, acc2 = predict_eegnet(modelpath, x_test2, y_test2)
    y_pre3, acc3 = predict_eegnet(modelpath, x_test3, y_test3)
