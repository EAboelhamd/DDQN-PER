import tensorflow as tf
import numpy as np
import per 
import time, os, cv2
import model
import utils
from emulator import *


class Atari:
	def __init__(self, args, sess):
		print('Initializing..')
		self.args = args
		self.sess = sess
		self.per = per.PER(self.args)
		self.engine = emulator(rom_name='breakout.bin', vis=self.args.visualize)
		self.args.num_actions = len(self.engine.legal_actions)
		# Build model
		self.build_model()	


	def build_model(self):
		print('Create online network and target network')
		self.q_net = model.Q_network(self.args, name='Q_net')
		self.target_net = model.Q_network(self.args, name='Target_net')
		self.sess.run(tf.global_variables_initializer())
 	 	# Choose which variable to save and restore, save parts of parameters, not all parameters, pass dictionary
 	 	# Before that, need to initialize
 	 	# Make dictionary
 	 	self.saver_dict = dict()
		print('Variable list to save')	
 	 	for i in self.q_net.tr_vrbs:
			print(i.name)
 	 	 	if i.name.startswith('Q_net/Conv1/weight'):
 	 	 	 	self.saver_dict['qw1'] = i
 	 	 	elif i.name.startswith('Q_net/Conv2/weight'):
 	 	 	 	self.saver_dict['qw2'] = i
 	 	 	elif i.name.startswith('Q_net/FC1/weight'):
 	 	 	 	self.saver_dict['qw3'] = i
 	 	 	elif i.name.startswith('Q_net/FC2/weight'):
 	 	 	 	self.saver_dict['qw4'] = i
 	 	 	elif i.name.startswith('Q_net/Conv1/bias'):
 	 	 	 	self.saver_dict['qb1'] = i
 	 	 	elif i.name.startswith('Q_net/Conv2/bias'):
 	 	 	 	self.saver_dict['qb2'] = i
 	 	 	elif i.name.startswith('Q_net/FC1/bias'):
 	 	 	 	self.saver_dict['qb3'] = i
 	 	 	elif i.name.startswith('Q_net/FC2/bias'):
 	 	 	 	self.saver_dict['qb4'] = i
 		for i in self.target_net.tr_vrbs:
			print(i.name)
			if i.name.startswith('Target_net/Conv1/weight'):
 	 	 	 	self.saver_dict['tw1'] = i
 	 	 	elif i.name.startswith('Target_net/Conv2/weight'):
 	 	 	 	self.saver_dict['tw2'] = i
 	 	 	elif i.name.startswith('Target_net/FC1/weight'):
 	 	 	 	self.saver_dict['tw3'] = i
 	 	 	elif i.name.startswith('Target_net/FC2/weight'):
 	 	 	 	self.saver_dict['tw4'] = i
 	 	 	elif i.name.startswith('Target_net/Conv1/bias'):
 	 	 	 	self.saver_dict['tb1'] = i
 	 	 	elif i.name.startswith('Target_net/Conv2/bias'):
 	 	 	 	self.saver_dict['tb2'] = i
 	 	 	elif i.name.startswith('Target_net/FC1/bias'):
 	 	 	 	self.saver_dict['tb3'] = i
 	 	 	elif i.name.startswith('Target_net/FC2/bias'):
 	 	 	 	self.saver_dict['tb4'] = i
 	 	self.saver_dict['step'] = self.q_net.global_step
		for k, v in self.saver_dict.items():
			print(v.op.name)
 	 	self.saver = tf.train.Saver(self.saver_dict)
 	 	# For copy to Target_net
		self.copy_network()

 	 	if self.load():
 	 	 	print('Loaded checkpoint..')
 	 	 	# Get global step
 	 	 	print('Continue from %s steps' % str(self.sess.run(self.qnet.global_step)))
 	 	else:
 	 	 	print('Not load checkpoint')


 	def train(self):
		self.sess.run(tf.global_variables_initializer())
  		self.step = 0
  		# Reset game
  		print('Reset before train start')
		self.reset_game()
  		self.reset_statistics()

  		# Increment global step as RMSoptimizer run
		utils.initialize_log()

		# Start time
		start_time = time.time()
  		print('Start training')
		
		# Collecting experiences before training
		print('Collecting replay memory for %d steps' % (self.args.train_start))

		# Epsilon
		self.eps = self.args.initial_eps
		# Beta
		self.beta = self.args.initial_beta

		while self.step < self.args.num_iterations:
			if self.per.get_size == self.args.train_start:
				print('\tTraing start')		
			
			if self.per.get_size > self.args.train_start:
				self.step += 1
				print('Current training step %d' % self.step)
				# Get batches
				batch_s, batch_act, batch_rwd, batch_ter, batch_next_s, priority_sum, sample_track, sample_priority = self.per.get_batches()
				# batch_act is action index, change it to one-hot encoded index
				batch_act = self.get_onehot(batch_act)
				# Loop in batch
				for i in xrange(self.args.batch_size):
					# Get one sample in minibatch
					sample_s = np.expand_dims(batch_next_s[i], axis=0)
					sample_act = np.expand_dims(batch_act[i], axis=0)
					sample_rwd = np.expand_dims(batch_rwd[i], axis=0)
					sample_ter = np.expand_dims(batch_ter[i], axis=0)
					sample_next_s = np.expand_dins(batch_next_s[i], axis=0)
					# Get target action by DDQN, by feeding next state, make [1,84,84,4]
					feed = {self.q_net.states : sample_next_s}
					# [1, num actions]
					online_q_values = self.sess.run([self.q_net.q_value], feed_dict = feed)
					# Get action index(argmax) which maximum q value, [1,]
					online_q_argmax = np.argmax(online_q_values, axis = 1) 
					# [1, num actions]
					target_value = self.sess.run([self.target_net.q_value], feed_dict = {self.traget_net.states : sample_next_s})
					# Q_target(next_state, argmax(Q_online(next_state))), Getting max value by argmax index
					# Make it [1,]
					target_max_value = tf.expand_dims(target_value[0][online_q_argmax],axis=0)
					feed = {self.q_net.states : sample_s, self.q_net.actions : sample_act, self.q_net.rewards : sample_rwd, self.q_net.terminals : sample_ter, self.q_net.q_max : target_max_value}
					# Get TD Error, gradient
					td_error_, grad_ = self.sess.run([self.q_net.td_error, self.q_net.grads], feed_dict=feed)
					# Calculate sample priority
					sample_pr = sample_priority[i] / priority_sum
					# Calculate sample importance sampling weight
					# Beta between [0,1], Tells how much compensate biased gradient
					sample_is_weight = (self.args.replay_size*sample_pr) ** (-self.beta)
					# Need to normalize by max(w)
					max_w = (self.args.replay_size * (self.per.max_priority / priority_sum))
					sample_is_weight = sample_is_weight / max_w

					acc_op = [self.q_net.accum_vars[i].assign_add(sample_is_weight*gv[0]) for i, gv in enumerate(grad_)]
					# Apply IS weight to gradient and accumulate
					_ = self.sess.run([acc_op], feed_dict = feed)	

					# Update clipped priority
					td_error = abs(td_error_ / max(1, abs(td_error_)))
					self.per.bt.update_transition(td_error, sample_track[i])	
				# Update weight
				_ = self.sess.run([self.train_op])
				
				# Copy network
				if np.mod(self.step, self.copy_interval) == 0:
					self.copy_network()
				# Save
				if np.mod(self.step, self.save_interval) == 0:
					self.save(self.step)
				# Write log
				if np.mod(self.step, self.log_interval) == 0:
					utils.write_log(self.step, self.total_reward, self.total_Q, self.eps, mode='train')
				
				# From initial beta to 1
				self.beta = min(1, self.args.initial_beta + float(self.step)/float(self.args.beta_step))

				# Decaying epsilon
				self.eps = max(self.args.eps_min, self.args.initial_eps - float(self.step)/float(self.args.eps_step))

			# When game is finished(One episode is over)
			if self.terminal:
				print('Reset for episode ends')
				self.reset_game()
				self.num_epi += 1
				self.total_reward += self.epi_reward
				self.epi_reward = 0

			# Get epsilon greedy action from state
			self.action_index, self.action, self.maxQ = self.select_action(self.state_proc)
			# Get reward and next state from environment
			self.state, self.reward, self.terminal = self.engine.next(self.action)
			# Scale rewards, all positive rewards to be 1, all negative rewards to be -1
			self.reward_scaled = self.reward // max(1,abs(self.reward))
			self.epi_reward += self.reward_scaled
			self.total_Q += self.maxQ

			# Change to next 4 consecutive images
			'''
			Using np.copy not to change 'self.state_gray_old'
			'''
			self.state_gray_old = np.copy(self.state_gray)
			# Save current state for feeding batch
			self.cur_state_proc = np.copy(self.state_proc)
			self.state_proc[:,:,0:3] = self.state_proc[:,:,1:4]
			# Preprocess
			self.state_resized = cv2.resize(self.state, (84,110))
			self.state_gray = cv2.cvtColor(self.state_resized, cv2.COLOR_BGR2GRAY)
			# Next state
			self.state_proc[:,:,3] = self.state_gray[26:110,:]/self.args.img_scale

			
			# Get one sample in minibatch, make batch index
			new_sample_s = np.expand_dims(self.cur_state_proc, axis=0)
			new_sample_act = np.expand_dims(self.action_index, axis=0)
			new_sample_rwd = np.expand_dims(self.reward_scaled, axis=0)
			new_sample_ter = np.expand_dims(self.terminal, axis=0)
			new_sample_next_s = np.expand_dins(self.state_proc, axis=0)
			# Get target action by DDQN, by feeding next state, make [1,84,84,4]
			feed = {self.q_net.states : new_sample_next_s}
			# [1, num actions]
			new_online_q_values = self.sess.run([self.q_net.q_value], feed_dict = feed)
			# Get action index(argmax) which maximum q value, [1,]
			new_online_q_argmax = np.argmax(new_online_q_values, axis = 1) 
			# [1, num actions]
			new_target_value = self.sess.run([self.target_net.q_value], feed_dict = {self.traget_net.states : new_sample_next_s})
			# Q_target(next_state, argmax(Q_online(next_state))), Getting max value by argmax index
			# Make it [1,]
			target_max_value = tf.expand_dims(new_target_value[0][new_online_q_argmax],axis=0)
			feed = {self.q_net.states : sample_s, self.q_net.actions : new_sample_act, self.q_net.rewards : new_sample_rwd, self.q_net.terminals : new_sample_ter, self.q_net.q_max : new_target_max_value}
			# Get TD Error, gradient
			new_td_error_ = self.sess.run([self.q_net.td_error], feed_dict=feed)
			# Clipping to 1
			self.priority = abs(new_td_error_ / max(1, abs(new_td_error_)))

			if self.state_gray_old is not None:
				self.per.insert(self.cur_state_proc, self.action_index, self.reward_scaled, self.terminal, self.priority) 		
							


	def copy_network(self):
		''' Copy from target network parameters to online network
			17 parameters, qnet parameter/step/targetnet parameters
		'''
		print('Copying qnet to targetnet')
		self.sess.run([self.saver_dict['tw1'].assign(self.saver_dict['qw1']), 
	                  self.saver_dict['tw2'].assign(self.saver_dict['qw2']),
	                  self.saver_dict['tw3'].assign(self.saver_dict['qw3']),
	                  self.saver_dict['tw4'].assign(self.saver_dict['qw4'])])
		self.sess.run([self.saver_dict['tb1'].assign(self.saver_dict['qb1']),
	                  self.saver_dict['tb2'].assign(self.saver_dict['qb2']),
	                  self.saver_dict['tb3'].assign(self.saver_dict['qb3']),
	                  self.saver_dict['tb4'].assign(self.saver_dict['qb4'])])
		print('Copy targetnet from qnet!')
 
	
	def reset_statistics(self):
   		self.epi_reward = 0
		self.num_epi = 0
		self.total_reward = 0
		self.total_Q = 0
		self.total_loss = 0

 	
	def reset_game(self):
  		print('Reset game at : %s ' % str(self.step))
		# Initialize all thing to zero
  		self.state_proc = np.zeros([84,84,4])
  		self.action = -1
  		self.reward = 0
  		self.terminal = False
  		# [screen_height, screen_width, 3]
  		self.state = self.engine.new_game()
  		# Preprocess by first converting RGB representation to gray-scale and down-sampling it to 110*84
  		# cv2.resize(image, (width, height) => 110 * 84 * 3
  		self.state_resized = cv2.resize(self.state, (84,110))
  		# To gray-scale
  		self.state_gray = cv2.cvtColor(self.state_resized, cv2.COLOR_BGR2GRAY)
  		# Reset, no previous state
  		self.state_gray_old = None
  		# state_proc[:,:,:3] will remain as zero
  		self.state_proc[:,:,3] = self.state_gray[26:110,:]/self.args.img_scale

	
	def select_action(self, state):
		# Greedy action
		if np.random.rand() > self.eps:
			print('Greedy action')
			# batch size for 'x' is 1 since we choose action for specific state
			q_prediction = self.sess.run(self.q_net.q_value, feed_dict={self.qnet.states : np.reshape(state, [1,84,84,4])})[0]
   			# Consider case when there are several same q max value
			# argwhere(if statement), return 2 dim array
			max_action_indices = np.argwhere(q_prediction == np.max(q_prediction))
			# If max_action_indices has more than 1 element, Choose 1 of them
			if len(max_action_indices) > 1:
				action_idx = max_action_indices[np.random.randint(0, len(max_action_indexs))][0]
				return action_idx, self.engine.legal_actions[action_idx], np.max(q_prediction)
			else:
				action_idx = max_action_indices[0][0]
				return action_idx, self.engine.legal_actions[action_idx], np.max(q_prediction)
		# episilon greedy action
		else:
			action_idx = np.random.randint(0,len(self.engine.legal_actions))
			print('Episilon greedy action : %d ' %self.engine.legal_actions[action_idx])
			q_prediction = self.sess.run(self.q_net.q_value, feed_dict={self.q_net.states : np.reshape(state, [1,84,84,4])})[0]
			return action_idx, self.engine.legal_actions[action_idx], q_prediction[action_idx]
	

	# action : [batch_size,] and element is integer, environment gives it as an integer
	def get_onehot(self, action):
		one_hot = np.zeros([self.args.batch_size, self.args.num_actions])
		for i in xrange(self.args.batch_size):
			one_hot[i, int(action[i])] = 1
		return one_hot

	@property
	def model_dir(self):
		return '{}_batch'.format(self.args.batch_size)

	def save(self, total_step):
		model_name = 'DQN'
		checkpoint_dir = os.path.join(self.args.checkpoint_dir, self.model_dir)
		if not os.path.exists(chekcpoint_dir):
			os.mkdir(checkpoint_dir)
		self.saver.save(self.sess, os.path.join(chekcpoint_dir, model_name, global_step=total_step))
		print('Model saved at %s in %d steps' % (checkpoint_dir, total_step))

 	def load(self):
  		print('Loading checkpoint..')
		checkpoint_dir = os.path.join(self.args.checkpoint_dir, self.model_dir)
  		ckpt = tf.train.get_checkpoint_state(checkpoint_dir)
		if ckpt and ckpt.model_checkpoint_path:
			ckpt_name = os.path.basename(ckpt.model_checkpoint_path)
			print(ckpt_name)
			self.saver.restore(self.sess, ckpt.model_checkpoint_path)
			print('Success to load %s' % (ckpt_name))
			return True
		else:
			print('Failed to find a checkpoint')
			return False   