import logging, httplib, urllib, time, numpy as np
from random import *
from threading import Thread
from flask import Flask, request, render_template

app = Flask(__name__)

conn = httplib.HTTPConnection("127.0.0.1:5000")	
headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
node_id = 0
num_connections = 0
min_energy = 10

node_connections = [] #can be less than the total number, because it only needs to include the ones it needs. 
node_distances = []
node_server_connections = []
energy_out = []
energy_in = []

node_reference = []

energy_storage = 0
location = [0,0]

def new_node_connection(request):
	new_connection = int(request.form['@connect'])
	node_distance = float(request.form['@distance'])
	global node_reference, node_id, num_connections,  node_connections, node_server_connections, connections, energy_in, energy_out, node_distances
	node_exists = False

	if (new_connection > len(node_reference) - 1):
		node_reference = np.hstack((node_reference, np.zeros(new_connection - len(node_reference) + 1)))
	for n in range (len(node_connections)):
		if (node_connections[n] == new_connection):
			node_exists = True
	if (node_exists == False):
		energy_in = np.hstack((energy_in,[0]))	
		energy_out = np.hstack((energy_out,[0]))	
		node_distances = np.hstack((node_distances,[node_distance]))	
		node_connections = np.hstack((node_connections,[new_connection]))	
		
		node_connection_addr = "127.0.0.1:" + str(6000 + new_connection)
 		node_connection = httplib.HTTPConnection(node_connection_addr)
		node_server_connections = np.hstack((node_server_connections,[node_connection]))	
		node_reference[new_connection] = int(num_connections)
		num_connections = num_connections + 1		
	return '1'

def get_energy_available(request):
	global energy_storage
	return str(max(energy_storage - min_energy,0))

def is_energy_available(request):
	global energy_storage
	if energy_storage > min_energy:
		return str(1)
	else:
		return str(0)

def get_energy(request):
	global energy_out, energy_storage, node_reference
	connected_node_id = int(request.form['@node_id'])
	connected_node_deficit = float(request.form['@deficit'])
	connected_node_transfer_rate = float(request.form['@rate'])
	
	#transfer rate is per hour
	if (energy_storage - min_energy > connected_node_transfer_rate):
		energy_out[node_reference[node_id]] = connected_node_transfer_rate		
	elif (energy_storage - min_energy > 0):
		connected_node_transfer_rate = energy_storage - min_energy
	else:
		connected_node_transfer_rate = 0
	energy_out[node_reference[node_id]] = connected_node_transfer_rate
	return str(connected_node_transfer_rate)

def energy_transfer(request):
	connected_node_id = int(request.form['@node_id'])
	connected_node_rate = int(request.form['@rate'])
	connected_node_time_diff = int(request.form['@sleep_time'])
	global energy_in, energy_stored, node_reference
	energy_in[node_reference[connected_node_id]] = connected_node_rate
	energy_stored = energy_stored + connected_node_rate * connected_node_time_diff
	return str(1)

def terminate_from_sender(request):
	global energy_in, node_reference
	connected_node_id = int(request.form['@node_id'])
	energy_in[node_reference[connected_node_id]] = 0
	return (1)

def terminate_from_receiver(request):
	global energy_out, node_reference
	connected_node_id = int(request.form['@node_id'])
	energy_out[node_reference[connected_node_id]] = 0
	return (1)

#processes data coming in
@app.route('/', methods = ['PUT', 'POST'])
def client_server():
	error = None
	return_message = ''
	cmd = int(request.form['@cmd'])
	if (cmd == 40):
		return_message = new_node_connection(request)
	if (cmd == 50):
		return_message = get_energy_available(request)
	if (cmd == 51):
		return_message = is_energy_available(request)
	if (cmd == 60):
		return_message = get_energy(request)
	if (cmd == 61):
		return_message = energy_transfer(request)
	if (cmd == 62):
		return_message = terminate_from_sender(request)
	if (cmd == 63):
		return_message = terminate_from_receiver(request)
	return return_message

def client_task():
	#sets up transmisison variables
	global node_id, location, num_connections, node_connections, energy_out, energy_in, node_server_connections, energy_storage
	storage_capacity = randint(0,5) * 100
	max_usage = 100

	location = [randint(0,500), randint(0,500)]
	energy_generation = 0
	energy_distribution = 0
	energy_usage_true = 0
	energy_usage_desired = 0
	energy_diff = 0
	energy_deficit = 0
	energy_waste = 0

	#set node parameters
	params = urllib.urlencode({'@cmd': 2, '@node_id': node_id,'@e_capacity': storage_capacity, '@e_use_max': max_usage, '@x_loc':location[0], '@y_loc': location[1]})
	conn.request("PUT", "", params, headers)
	r1 = conn.getresponse()	
	
	if (node_id > 0):
		for n in range (0, randint(0,node_id-1)):
			params = urllib.urlencode({'@cmd': 1,'@node_id': node_id, '@connect': randint(0,node_id - 1) })
			conn.request("PUT", "", params, headers)
			r1 = conn.getresponse()
		
	#main loop
	while (1):
		sleep_time = uniform(0.01, 0.01)
		time.sleep(sleep_time)
		energy_generation = uniform(0,200) * sleep_time
		energy_usage_desired = uniform(50,150) * sleep_time
		energy_diff = energy_generation - energy_usage_desired
		
		current_deficit = 0

		requires_energy = False
		# adds energy
		if (energy_diff > 0): 
			if (energy_storage + energy_diff >= storage_capacity):
				energy_waste = energy_waste + (energy_storage + energy_diff - storage_capacity)
				energy_storage = storage_capacity
			else:
				energy_storage = energy_storage + energy_diff	
	
		# uses energy
		elif (energy_diff < 0):
			if (energy_storage + energy_diff < 0):
				energy_usage_true = energy_usage_desired + energy_storage + energy_diff
				energy_storage = 0
				energy_deficit = energy_deficit - (energy_storage + energy_diff)
				requires_energy = True
				current_deficit = -energy_storage - energy_diff + min_energy
			else:
				energy_storage = energy_storage + energy_diff			
					
		params = urllib.urlencode({'@cmd': 10, '@node_id': node_id, '@storage': energy_storage, '@deficit': energy_deficit, '@waste': energy_waste})
		conn.request("PUT", "", params, headers)
		r1 = conn.getresponse()

		if (requires_energy):
			total_energy_available = 0
			for c in range(len(node_connections)):
				params = urllib.urlencode({'@cmd': 51})
				current_connection = node_server_connections[c]
				current_connection.request("PUT", "", params, headers)
				r = current_connection.getresponse()
				
				if (int(r.read()) == 1):
					params = urllib.urlencode({'@cmd': 60, '@node_id': node_id, '@deficit': energy_deficit, '@rate': min(energy_deficit,min_energy)})
					current_connection.request("PUT", "", params, headers)
					r = current_connection.getresponse()
					energy_in[c] = float(r.read())
		
	connected_node_id = int(request.form['@node_id'])
	connected_node_deficit = int(request.form['@deficit'])
	connected_node_transfer_rate = int(request.form['@rate'])

	#check its own connections. 
	for c in range(len(energy_out)):
		if (energy_out[c] * sleep_time < energy_stored - min_energy):
			params = urllib.urlencode({'@cmd':61, '@node_id': node_id, '@rate':energy_out[c], '@time_diff': sleep_time})
			current_connection = node_server_connections[c]
			current_connection.request("PUT", "", params, headers)
			r = current_connection.getresponse()
			energy_storage = energy_storage - energy_out[c] * sleep_time
		else:
			params = urllib.urlencode({'@cmd':62, '@node_id': node_id})
			current_connection = node_server_connections[c]
			current_connection.request("PUT", "", params, headers)
			r = current_connection.getresponse()
			energy_out[c] = 0
				
if __name__ == '__main__':
	#get node index
	params = urllib.urlencode({'@cmd': 0})
	conn.request("PUT", "", params, headers)
	r1 = conn.getresponse()
	node_id = int(r1.read())

	node_reference = np.zeros(node_id + 1)	
	
	#start background task
	client_task_thread = Thread(target=client_task, args=())
	client_task_thread.start()

	# create a client server
	log = logging.getLogger('werkzeug')
	log.setLevel(logging.ERROR)
	port_num = 6000 + node_id
	app.run(host='127.0.0.1', port = port_num)
