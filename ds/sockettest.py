#!/usr/bin/env python3
import time
import socket
from directkeys import W,A,S,D,P,U,E,Q,T,L,I,R,F1,F2,F3,F11,NUM1,NUM2,NUM4,SPACE,G,E,PressKey,ReleaseKey,ReleaseKeys,PressAndRelease,PressAndFastRelease

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 31000        # The port used by the server
DOTNETPORT = 31001        # The port used by the server
NUMTIMES=100
FRAME_DIFF=0.01


start_time=time.time()
start_time2=time.time() 
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, DOTNETPORT))
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        s.settimeout(100)
        s.send(b'getState \n')
        data = s.recv(1024)
        loglines=data.decode("utf-8")
        print(loglines)
print("state took:",time.time()-start_time2)