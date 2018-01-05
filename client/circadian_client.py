import logging, httplib, urllib, time, numpy as np
from random import *
from threading import Thread
from flask import Flask, request, render_template

app = Flask(__name__)

conn = httplib.HTTPConnection("127.0.0.1:5000")	
headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

def client_task(node_id):
	print ('client_task')

	connections = []
	num_connections = 0
	node_connections = []
	energy_out = []
	
	storage_capacity = randint(0,3) * 100
	max_usage = 10;
	
	generation = 0
	distribution = 0
	storage = 0
	desired_usage = 0
	true_usage = 0
	
	#set node parameters
	params = urllib.urlencode({'@cmd': 2, '@node_id': node_id,'@e_capacity': storage_capacity, '@e_use_max': max_usage})
	conn.request("PUT", "", params, headers)
	r1 = conn.getresponse()	
		
	# set up connections
	if (node_id > 0):
		connections.append(randint(0,node_id - 1))	
	if (node_id > 1):
		for n in range(0, min(2,int(randint(0,node_id - 1)))):	
			connections.append(randint(0,node_id - 1))	
	if (len(connections) > 0):
		for c in range(0, len(connections)):
			connection =  connections[c]
			params = urllib.urlencode({'@cmd': 1,'@node_id': node_id, '@connect': connection})
			conn.request("PUT", "", params, headers)
			r1 = conn.getresponse()
		
	
	#main loop
	while (1):
		time.sleep(randint(10,1000)/1000)
		# check if any other nodes are connected
		params = urllib.urlencode({'@cmd': 20,'@node_id': node_id})
		conn.request("PUT", "", params, headers)
		r1 = conn.getresponse()
		response = r1.read()
		response = response.split("/")	
		if (len(node_connections) != response[0]):
			node_connections = np.zeros((int(response[0]), 1))
			energy_out =  np.zeros((int(response[0]), 1))

		params = urllib.urlencode({'@cmd': 21,'@node_id': node_id})
		conn.request("PUT", "", params, headers)
		r1 = conn.getresponse()
		energy_shared = float(r1.read())
	
		#sharing
		generation = randint(0,20)	
		storage = storage + generation - energy_shared
		desired_usage = randint(0,20)
 		true_usage = min(storage, desired_usage)
		energy_need = max(0,10 + true_usage - storage)
		storage = storage - true_usage
		
		params = urllib.urlencode({'@cmd': 11,'@node_id': node_id, '@e_store': storage, '@e_gen': generation, '@e_use': true_usage, '@e_need': energy_need})
		conn.request("PUT", "", params, headers)
		r1 = conn.getresponse()
		energy_received = float(r1.read())	

#get node index
params = urllib.urlencode({'@cmd': 0})
conn.request("PUT", "", params, headers)
r1 = conn.getresponse()
node_id = int(r1.read())
	
client_task_thread = Thread(target=client_task, args=(node_id))
client_task_thread.start()

@app.route('/', methods = ['PUT', 'POST'])
def client_server():
	error = None
	return_message = ''
	cmd = int(request.form['@cmd'])
	return return_message

# create a client server
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app.run(debug=True, host='127.0.0.1', port = 6000)
