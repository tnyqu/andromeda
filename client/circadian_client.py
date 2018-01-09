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

network_true_energy = []
network_apparent_energy = []

daily_generation_profile = [0,0,0,0,0,1,7,18,38,59,57,87,92,95,92,87,72,56,38,19,7,1,0,0]
daily_home_usage_profile = [20,10,5,5,5,5,10,20,50,30,5,5,5,5,5,5,5,40,70,80,80,90,70,50]
daily_business_usage_profile = [10,10,10,10,10,10,30,70,80,80,80,80,80,80,80,80,80,80,50,30,10,10,10,10]
 
def new_node_connection(request):
	new_connection = int(request.form['@connect'])
	node_distance = float(request.form['@distance'])
	global node_reference, node_id, num_connections,  node_connections, node_server_connections, connections, energy_in, energy_out, node_distances, network_true_energy, network_apparent_energy
	node_exists = False

	if (new_connection > len(node_reference) - 1):
		node_reference = np.hstack((node_reference, np.zeros(new_connection - len(node_reference) + 1)))
	for n in range (len(node_connections)):
		if (node_connections[n] == new_connection):
			node_exists = True
	if (node_exists == False):
		energy_in = np.hstack((energy_in,[0]))	
		energy_out = np.hstack((energy_out,[0]))	
		network_true_energy = np.hstack((network_true_energy,[0]))	
		network_apparent_energy = np.hstack((network_apparent_energy,[0]))	
		node_distances = np.hstack((node_distances,[node_distance]))	
		node_connections = np.hstack((node_connections,[new_connection]))	
		
		node_connection_addr = "127.0.0.1:" + str(6000 + new_connection)
 		node_connection = httplib.HTTPConnection(node_connection_addr)
		node_server_connections = np.hstack((node_server_connections,[node_connection]))	
		node_reference[new_connection] = int(num_connections)
		num_connections += 1
	return '1'

def get_true_energy(request):		
	global energy_storage, min_energy
	return str(max(energy_storage - min_energy, 0))

def get_apparent_energy(request):
	global node_distances, node_connections, energy_storage, network_true_energy
	apparent_energy = energy_storage
	connected_node_id = int(request.form['@node_id'])
	for n in range(0,len(network_true_energy)):
		if (node_connections[n] != connected_node_id):
			apparent_energy += network_true_energy[n] * (100 - node_distances[n]/500) / 100	
	return str(apparent_energy)


def get_energy(request):
	global min_energy, energy_out, energy_storage, node_reference
	connected_node_id = int(request.form['@node_id'])
	energy_request = float(request.form['@energy_request']) / ( (100 - node_distances[node_reference[connected_node_id]]/500) / 100)
	elapsed_time = float(request.form['@time'])
	energy_transfer = 0
		
	#transfer rate is per hour
	if ((energy_storage - min_energy) > energy_request):
		energy_transfer = energy_request 
		energy_storage -= energy_transfer	
	elif ((energy_storage - min_energy) > 0):
		energy_transfer = energy_storage - min_energy
		energy_storage = min_energy
	else:
		energy_transfer = 0
	return str(energy_transfer)

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
		return_message = get_true_energy(request)
	if (cmd == 51):
		return_message = get_apparent_energy(request)
	if (cmd == 60):
		return_message = get_energy(request)
	if (cmd == 62):
		return_message = terminate_from_sender(request)
	if (cmd == 63):
		return_message = terminate_from_receiver(request)
	return return_message

def client_task():
	#sets up transmisison variables
	global node_id, location, num_connections, node_connections, energy_out, energy_in, node_server_connections, energy_storage, network_apparent_energy, network_true_energy
	
	global daily_generation_profile, min_energy
	max_usage = 100
	
	if (node_id == 0):
		solar_panel_capacity = randint(5,20) * 10 
		energy_usage_capacity =  randint(5,10) * 10
		storage_capacity = randint(5,20) * 10
		daily_usage_profile = daily_business_usage_profile
	else:
		solar_panel_capacity = randint(0,5) * 10
		energy_usage_capacity = randint(5,20)
		storage_capacity = randint(3,10) * 10
		daily_usage_profile = daily_home_usage_profile
	min_energy = energy_usage_capacity
	location = [randint(0,500), randint(0,500)]
	
	energy_generation = 0
	energy_distribution = 0
	energy_usage_true = 0
	energy_usage_desired = 0
	energy_diff = 0
	energy_deficit = 0
	energy_waste = 0
	energy_received = 0

	#set node parameters
	params = urllib.urlencode({'@cmd': 2, '@node_id': node_id,'@e_capacity': storage_capacity, '@e_use_max': max_usage, '@x_loc':location[0], '@y_loc': location[1]})
	conn.request("PUT", "", params, headers)
	r1 = conn.getresponse()	
	
	if (node_id > 0):
		for n in range (0, randint(0,node_id-1)):
			params = urllib.urlencode({'@cmd': 1,'@node_id': node_id, '@connect': randint(0,node_id - 1) })
			conn.request("PUT", "", params, headers)
			r1 = conn.getresponse()
	total_time = 0
	prev_time = time.time()
	#main loop
	while (1):
		time.sleep(0.1)
		sleep_time = time.time() - prev_time
		total_time = total_time + sleep_time
		prev_time = time.time()
			
		energy_generation = sleep_time * solar_panel_capacity * daily_generation_profile[int(total_time) % 24] / 100.0 * uniform(0.5,1.0)
		energy_usage_desired = sleep_time * energy_usage_capacity * daily_usage_profile[int(total_time) % 24] / 100.0 * uniform(0.0,3.0)
		#energy_usage_desired = uniform(50,150) * sleep_time
		energy_diff = energy_generation - energy_usage_desired + energy_received
		energy_received = 0
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
		
		params = urllib.urlencode({'@cmd': 10, '@node_id': node_id, '@storage': energy_storage, '@deficit': energy_deficit, '@waste': energy_waste,'@generation': energy_generation/sleep_time, '@usage': energy_usage_desired/sleep_time})
		conn.request("PUT", "", params, headers)
		r1 = conn.getresponse()
		
		'''	
		#here is how it is done!!!!
		1. check if itself has a deficit, if so, ask all for their energy and divide need amonst group
		2. get its own *network_stats*, verses each other node, if it is lower, then request based on the difference
		'''
		
		total_available_apparent_energy = 0
		
		for n in range(len(node_connections)):
			current_connection = node_server_connections[n]
		
			#get true energy	
			params = urllib.urlencode({'@cmd':50, '@node_id': node_id})
			current_connection.request("PUT", "", params, headers)
			r = current_connection.getresponse()
			network_true_energy[n] = float(r.read())
		
			#get apparent energy	
			params = urllib.urlencode({'@cmd':51, '@node_id': node_id})
			current_connection.request("PUT", "", params, headers)
			r = current_connection.getresponse()
			network_apparent_energy[n] = float(r.read())
			network_apparent_energy[n] = network_apparent_energy[n] * (100 - node_distances[n]/500) / 100.0
			if (network_apparent_energy[n] > 0):
				total_available_apparent_energy = total_available_apparent_energy + network_apparent_energy[n]
				
		if (energy_storage < min_energy):
			for n in range(len(node_connections)):
				if (network_apparent_energy[n] > 0):
					energy_request = network_apparent_energy[n] / total_available_apparent_energy * current_deficit
					current_connection = node_server_connections[n]
					params = urllib.urlencode({'@cmd':60, '@node_id':node_id, '@energy_request':energy_request, '@time': sleep_time})
					current_connection.request("PUT", "", params, headers)
					r = current_connection.getresponse()
					energy_received += float(r.read()) * (100 - node_distances[n]/500) / 100.0
			
		elif (energy_storage < storage_capacity): 
			for n in range(len(node_connections)):						
				apparent_energy = 0
				for c in range(len(node_connections)):
					if (n != c):
						apparent_energy = apparent_energy + network_true_energy[c] * (100 - node_distances[c]/500) / 100.0
				if (apparent_energy < network_apparent_energy[n]):
					energy_request = (network_apparent_energy[n] - apparent_energy) / 10.0
					current_connection = node_server_connections[n]
					params = urllib.urlencode({'@cmd':60, '@node_id':node_id, '@energy_request':energy_request, '@time': sleep_time})
					current_connection.request("PUT", "", params, headers)
					r = current_connection.getresponse()
					energy_received += float(r.read()) * (100 - node_distances[n]/500) / 100.0
		
		if (energy_received > 0):
			print node_id, energy_diff, energy_received		
		
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
