import numpy as np
import tensorflow as tf
import os, time

LOG_DIR = './logs'
TRAIN = 'train.csv'
EVAL = 'eval.csv'

def initialize_log():
	try:
		train_log = open(os.path.join(LOG_DIR, TRAIN), 'a')
	except:
		print('Initialize log..')
		train_log = open(os.path.join(LOG_DIR, TRAIN), 'w')
		train_log.write('Step\t'+',avg_reward\t'+',avg_q\t'+',epsilon\t'+',time\n')
	try:
		eval_log = open(os.path.join(LOG_DIR, EVAL), 'a')
	except:
		eval_log = open(os.path.join(LOG_DIR, EVAL), 'w')
		eval_log.write('Step\t'+',avg_reward\t+'+',avg_q\t'+',epsilon\t'+',time\n')

	return train_log, eval_log


def write_log(steps, total_rwd, total_q, total_loss, num_episode, epsilon, start_time, mode):
	print('At Training step %d, %d episodes => Avg.Q : %3.4f, Avg.rwd : %3.4f, Avg_loss : % 3.4f' % \
		(steps, num_episode, total_q / num_episode, total_rwd / num_episode, total_loss / steps))
	
	train_log, eval_log = initialize_log(mode=mode)
	if mode == 'train':
		train_log.write(str(steps)+'\t,' + str(total_rwd/num_episode)+'\t,' + str(total_q/num_episode)+'\t,' \
		+ str(epsilon) + '\t,' + str(time.time() - start_time) + '\n')
		train_log.flush()
	elif mode == 'eval':
		eval_logs.write(str(steps)+'\t,' + str(total_rwd/num_episode)+'\t,' + str(total_q/num_episode)+'\t,' \
		+ str(epsilon) + '\t,' + str(time.time() - start_time) + '\n')
		eval_log.flush()


# Define convolutional layer
# 'inp' : [batch, in_height, in_widht, in_channels]
# truncated_normal : bound with 2*stddev
def conv2d(inp, output_dim, filter_height, filter_width, stride,stddev=0.02, name=None):
	with tf.variable_scope(name or 'conv2d'):
		weight = tf.get_variable('weight', [filter_height, filter_width, inp.get_shape()[-1], output_dim], initializer=tf.truncated_normal_initializer(stddev=stddev))
		# padding=SAME : ceil(float(in_height))/float(stride)
		# padding=VALID: cell(float(in_height-filter_height)+1)/float(stride)
		conv = tf.nn.conv2d(inp, weight, strides=[1,stride,stride,1], padding='VALID')
		bias = tf.get_variable('bias', [output_dim], initializer=tf.constant_initializer(0))
		conv_wb = tf.add(conv,bias)
		return conv_wb, conv_wb.get_shape().as_list()
 
def linear(inp, output_size, name=None, stddev=0.02):
	with tf.variable_scope(name or 'linear'):
		weight = tf.get_variable('weight', [inp.get_shape()[-1], output_size], initializer=tf.truncated_normal_initializer(stddev=stddev))
		bias = tf.get_variable('bias', [output_size], initializer=tf.constant_initializer(0))
		weighted_sum = tf.matmul(inp, weight) + bias
    	return weighted_sum



	
	