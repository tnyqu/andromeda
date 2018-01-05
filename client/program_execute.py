import os
import subprocess
import sys

proc = subprocess.Popen([sys.executable, 'circadian_client.py'])
proc.wait()
