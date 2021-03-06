import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import tensorflow as tf
import argparse
import cv2
import numpy as np
from glob import glob

num_classes = 2
img_height, img_width = 64, 64



def Mynet(x, train=False):
    x = tf.layers.conv2d(inputs=x, filters=32, kernel_size=[3, 3], padding='same', activation=tf.nn.relu, name='conv1_1')
    x = tf.layers.max_pooling2d(inputs=x, pool_size=[2, 2], strides=2)
    x = tf.layers.conv2d(inputs=x, filters=32, kernel_size=[3, 3], padding='same', activation=tf.nn.relu, name='conv2')
    x = tf.layers.max_pooling2d(inputs=x, pool_size=[2, 2], strides=2)   

    mb, h, w, c = x.get_shape().as_list()
    x = tf.reshape(x, [-1, h*w*c])
    x = tf.layers.dense(inputs=x, units=128, activation=tf.nn.relu, name='fc1')
    x = tf.layers.dropout(inputs=x, rate=0.25, training=train)
    x = tf.layers.dense(inputs=x, units=num_classes, name="fc_cls")
    return x


# get train data
def data_load(dir_path):
    xs = np.ndarray((0, img_height, img_width, 3))
    ts = np.ndarray((0, num_classes))
    paths = []
    
    for dir_path in glob(dir_path + '/*'):
        for path in glob(dir_path + '/*'):
            x = cv2.imread(path)
            x = cv2.resize(x, (img_width, img_height)).astype(np.float32)
            x /= 255.
            xs = np.r_[xs, x[None, ...]]

            t = np.zeros((num_classes))
            if 'akahara' in path:
                t[0] = 1
            elif 'madara' in path:
                t[1] = 1
            ts = np.r_[ts, t[None, ...]]

            paths += [path]

    return xs, ts, paths


# train
def train():
    tf.reset_default_graph()

    # place holder
    X = tf.placeholder(tf.float32, [None, img_height, img_width, 3])
    Y = tf.placeholder(tf.float32, [None, num_classes])
    keep_prob = tf.placeholder(tf.float32)
    
    logits = Mynet(X, train=True)
    preds = tf.nn.softmax(logits)
    loss = tf.reduce_mean(tf.losses.softmax_cross_entropy(logits=logits, onehot_labels=Y))
    optimizer = tf.train.AdamOptimizer(learning_rate=0.001)
    train = optimizer.minimize(loss)

    correct_pred = tf.equal(tf.argmax(preds, 1), tf.argmax(Y, 1))
    accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))
    

    xs, ts, paths = data_load('../Dataset/train/images/')

    # training
    mb = 8
    mbi = 0
    train_ind = np.arange(len(xs))
    np.random.seed(0)
    np.random.shuffle(train_ind)

    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    config.gpu_options.visible_device_list="0"
    with tf.Session(config=config) as sess:
        sess.run(tf.global_variables_initializer())
    
        for i in range(100):
            if mbi + mb > len(xs):
                mb_ind = train_ind[mbi:]
                np.random.shuffle(train_ind)
                mb_ind = np.hstack((mb_ind, train_ind[:(mb-(len(xs)-mbi))]))
                mbi = mb - (len(xs) - mbi)
            else:
                mb_ind = train_ind[mbi: mbi+mb]
                mbi += mb

            x = xs[mb_ind]
            t = ts[mb_ind]

            _, acc, los = sess.run([train, accuracy, loss], feed_dict={X: x, Y: t, keep_prob: 0.5})
            print("iter >>", i+1, ',loss >>', los / mb, ',accuracy >>', acc)

        saver = tf.train.Saver()
        saver.save(sess, './cnn.ckpt')

# test
def test():
    tf.reset_default_graph()

    X = tf.placeholder(tf.float32, [None, img_height, img_width, 3])
    Y = tf.placeholder(tf.float32, [None, num_classes])
    keep_prob = tf.placeholder(tf.float32)

    logits = Mynet(X, train=False)
    out = tf.nn.softmax(logits)

    xs, ts, paths = data_load("../Dataset/test/images/")

    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    config.gpu_options.visible_device_list="0"
    with tf.Session(config=config) as sess:
        saver = tf.train.Saver()
        #saver = tf.train.import_meta_graph("./cnn.ckpt.meta")
        saver.restore(sess, "./cnn.ckpt")

        for i in range(len(paths)):
            x = xs[i]
            t = ts[i]
            path = paths[i]
            
            x = np.expand_dims(x, axis=0)

            pred = out.eval(feed_dict={X: x, keep_prob: 1.0})[0]

            print("in {}, predicted probabilities >> {}".format(path, pred))
    

def arg_parse():
    parser = argparse.ArgumentParser(description='CNN implemented with Keras')
    parser.add_argument('--train', dest='train', action='store_true')
    parser.add_argument('--test', dest='test', action='store_true')
    args = parser.parse_args()
    return args

# main
if __name__ == '__main__':
    args = arg_parse()

    if args.train:
        train()
    if args.test:
        test()

    if not (args.train or args.test):
        print("please select train or test flag")
        print("train: python main.py --train")
        print("test:  python main.py --test")
        print("both:  python main.py --train --test")
