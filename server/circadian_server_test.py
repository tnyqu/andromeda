import logging, time, numpy as np
from flask import Flask, request, render_template
from threading import Thread

app = Flask(__name__)

num_nodes = 0;
connections = np.zeros((1,1))
total_energy_out = np.zeros((1,1))
total_energy_transfer = np.zeros((1,1))
total_energy_stored = np.zeros((1,1))
total_node_max_usage = np.zeros((1,1))
total_node_max_capacity = np.zeros((1,1))
total_node_energy_transfer = np.zeros((1,1))
total_energy_stored = np.zeros((1,1))

def node_set(request):
	global num_nodes, connections, total_energy_out, total_energy_transfer, total_energy_stored, total_node_energy_transfer, total_node_max_capacity, total_node_max_usage, total_energy_stored, total_energy_transfer
	num_nodes = num_nodes + 1
	#expand the array
	if (num_nodes > 1):
		connections = np.hstack((connections, np.zeros((num_nodes-1,1))))
		connections = np.vstack((connections, np.zeros((1,num_nodes))))	
		total_energy_out = np.zeros((num_nodes, num_nodes))
		total_energy_transfer = np.zeros((num_nodes, num_nodes))
		total_energy_stored = np.zeros(num_nodes)
		total_node_max_usage = np.zeros(num_nodes)
		total_node_max_capacity = np.zeros(num_nodes)
		total_node_energy_transfer = np.zeros(num_nodes)
	return str(num_nodes - 1)

def node_param(request):
	global total_node_max_usage, total_node_max_capacity	
	node_id = int(request.form['@node_id'])	
	e_use_max = int(request.form['@e_use_max'])	
	e_capacity = int(request.form['@e_capacity'])
	total_node_max_usage[node_id] = e_use_max
	total_node_max_capacity[node_id] = e_capacity	
	return str(1)

def node_connect(request):
	global connections
	node_id = int(request.form['@node_id'])	
	connect = int(request.form['@connect'])	
	connections[node_id][connect] = 1;
	connections[connect][node_id] = 1;
	return str(1)

def node_info(request):
	node_id = float(request.form['@node_id'])	
	connect = float(request.form['@connect'])	
	energy_out = float(request.form['@energy_out'])	
	
	global total_energy_out, total_energy_transfer 
	total_energy_out[node_id][connect] = energy_out;

	#energy out for the node (total)
	total_energy_transfer[node_id][connect] =  total_energy_out[node_id][connect] - total_energy_out[connect][node_id]
	total_energy_transfer[connect][node_id] = -total_energy_out[node_id][connect] + total_energy_out[connect][node_id]
	return str(1)

def node_status(request):
	global total_energy_stored
		
	node_id = float(request.form['@node_id'])	
	e_store = float(request.form['@e_store']) 
	e_gen = float(request.form['@e_gen'])
	e_need = float(request.form['@e_need'])
	e_use = float(request.form['@e_use'])
	
	total_energy_stored[node_id] = e_store;
	#check each and every node that it is connected to for e_need capabilities
	e_available = 0
	for n in range (num_nodes - 1):
		if connections[node_id][n] != 0:
			e_available = e_available + max(0, total_energy_stored[n] - total_node_max_usage[n])
	if (e_available > e_need):
		for n in range (1,num_nodes - 1):
			if connections[node_id][n] != 0:
				e_need / e_available * (total_energy_stored[n] - total_node_max_usage[n])
				total_node_energy_transfer[n] = total_node_energy_transfer[n] + e_need / e_available * (total_energy_stored[n] - total_node_max_usage[n])
				total_energy_stored[n] = total_energy_stored[n] - e_need / e_available * (total_energy_stored[n] - total_node_max_usage[n]) 
	else:
		for n in range (1,num_nodes - 1):
			if connections[node_id][n] != 0:
				total_node_energy_transfer[n] = total_node_energy_transfer[n] - total_energy_stored[n] - total_node_max_usage[n]
				total_energy_stored[n] = total_node_max_usage[n]
	# we need to track and communicate who sent energy
	return str(min(e_available, e_need)) #returns the given energy
	
def check_num_connect(request):
	node_id = float(request.form['@node_id'])	
	num_connections = 0;
	node_connections = ''
	for n in range (num_nodes - 1):
		if connections[node_id][n] != 0:
			num_connections = num_connections + 1
			node_connections = node_connections + '/' + str(n)
	return str(num_nodes) + '/' + str(num_connections) + str(node_connections)

def check_energy_share(request):
	node_id = int(request.form['@node_id'])	
	global total_node_energy_transfer
	energy_transfer_out = total_node_energy_transfer[node_id]
	total_node_energy_transfer[node_id] = 0
	# we need to communicate who we need to send energy to and how much
	return str(energy_transfer_out)
	
@app.route('/', methods=['PUT', 'POST'])
def set_info():
	error = None
	return_message = ''	
	cmd = int(request.form['@cmd'])
	if (cmd == 0):
		return_message = node_set(request)
	if (cmd == 1):
		return_message = node_connect(request)
	if (cmd == 2):
		return_message = node_param(request)
	if (cmd == 10):
		return_message = node_info(request)
	if (cmd == 11):
		return_message = node_status(request)
	if (cmd == 20):
		return_message = check_num_connect(request)
	if (cmd == 21):
		return_message = check_energy_share(request)
	return return_message

@app.route('/', methods=['GET'])
def get_info():
	return 'sent'

def server_monitor():
	for x in range(0,10):
		time.sleep(1)
		global total_energy_stored
		print total_energy_stored

if __name__ == '__main__':
	t = Thread(target=server_monitor, args=())
	t.start()
	
	log = logging.getLogger('werkzeug')
	log.setLevel(logging.ERROR)
	app.run(debug=True, host='127.0.0.1', port = 5000)
