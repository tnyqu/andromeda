import logging, httplib, urllib, time, numpy as np, math
from flask import Flask, request, render_template
from threading import Thread

app = Flask(__name__)

headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

num_nodes = 0
total_energy_stored = []
#np.zeros((1,3))

node_server_connections = []
node_locations = []

def node_init(request):
	global num_nodes, connections, total_energy_stored, node_server_connections, node_locations

	num_nodes = num_nodes + 1
	#expand the array
	total_energy_stored = np.zeros((num_nodes,5))
	if (num_nodes > 1):
		node_locations = np.vstack((node_locations,np.zeros((1,2))))
	else:
		node_locations = np.zeros((1,2))
	#add new connection
	node_connection_addr = "127.0.0.1:" + str(6000 + num_nodes - 1)
	node_connection = httplib.HTTPConnection(node_connection_addr)
	node_server_connections.append( node_connection)
	
	return str(num_nodes - 1)

def node_set_param(request):
	global node_locations

	node_id = int(request.form['@node_id'])	
	x_loc = float(request.form['@x_loc'])	
	y_loc = float(request.form['@y_loc'])
	node_locations[node_id][0] = x_loc
	node_locations[node_id][1] = y_loc
	return str(1)

def node_add_connection(request):
	node_id = int(request.form['@node_id'])	
	connect = int(request.form['@connect'])	
	
	#tell node at connection that we have a new connection for them
	node_distance = math.sqrt(math.pow(node_locations[connect][0] - node_locations[node_id][0], 2) + math.pow(node_locations[connect][1] - node_locations[node_id][1], 2))	
	
	params = urllib.urlencode({'@cmd': 40, '@connect': node_id, '@num_nodes': num_nodes, '@distance': node_distance})
	current_connection = node_server_connections[connect]
	current_connection.request("PUT", "", params, headers)
	r = current_connection.getresponse()
	
	params = urllib.urlencode({'@cmd': 40, '@connect': connect, '@num_nodes': num_nodes, '@distance': node_distance})
	current_connection = node_server_connections[node_id]
	current_connection.request("PUT", "", params, headers)
	r = current_connection.getresponse()
	return str(1)

def node_update(request):
	global total_energy_stored
	node_id = int(request.form['@node_id'])	
	storage = float(request.form['@storage'])	
	waste = float(request.form['@waste'])	
	deficit = float(request.form['@deficit'])	
	generation = float(request.form['@generation'])	
	usage = float(request.form['@usage'])	
	total_energy_stored[node_id][0] = int(storage)
	total_energy_stored[node_id][1] = int(generation)
	total_energy_stored[node_id][2] = int(usage)
	total_energy_stored[node_id][3] = int(waste)
	total_energy_stored[node_id][4] = int(deficit)
	return str(1)

@app.route('/', methods=['PUT', 'POST'])
def set_info():
	error = None
	return_message = ''	
	cmd = int(request.form['@cmd'])
	if (cmd == 0):
		return_message = node_init(request)
	if (cmd == 1):
		return_message = node_add_connection(request)
	if (cmd == 2):
		return_message = node_set_param(request)
	if (cmd == 10):

		return_message = node_update(request)
	return return_message

def server_monitor():
	loop = 0
	while (loop < 60):
		time.sleep(1)
		global total_energy_stored
		if (len(total_energy_stored) != 0):
			print loop, ['stored', 'generation','usage','waste', 'deficit']
			print total_energy_stored
			loop = loop + 1

if __name__ == '__main__':
	t = Thread(target=server_monitor, args=())
	t.start()
	
	log = logging.getLogger('werkzeug')
	log.setLevel(logging.ERROR)
	app.run(host='127.0.0.1', port = 5000)
