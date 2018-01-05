import os, subprocess, sys
from threading import Thread

def client_process():
	proc = subprocess.Popen([sys.executable, 'circadian_client.py'])
	proc.wait()

if __name__ == '__main__':
	for i in range(0,10):
		client_process_thread = Thread(target=client_process, args=())
		client_process_thread.start()
