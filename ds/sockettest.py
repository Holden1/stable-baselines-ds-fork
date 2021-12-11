#!/usr/bin/env python3
import time
import socket
from directkeys import W,A,S,D,P,U,E,Q,T,L,I,R,F1,F2,F3,F11,NUM1,NUM2,NUM4,SPACE,G,E,PressKey,ReleaseKey,ReleaseKeys,PressAndRelease,PressAndFastRelease

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 31000        # The port used by the server
DOTNETPORT = 31001        # The port used by the server
NUMTIMES=1
FRAME_DIFF=0.01


start_time=time.time()
start_time2=time.time() 
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, DOTNETPORT))
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        s.settimeout(100)
        s.send(b'updateAddress \n')

for i in range(NUMTIMES):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, DOTNETPORT))
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        s.settimeout(0.5)
        s.send(b'getState \n')
        try:
            data = s.recv(1024)
            print(data)
        except socket.timeout:
            print("timeout")
        if start_time != -1:
            elapsed = time.time() - start_time
            timeToSleep = FRAME_DIFF - elapsed
            if timeToSleep > 0:
                time.sleep(timeToSleep)
                #print("New elapsed ",time.time()-start_time)
            else:
                print("Didn't sleep:",elapsed)
        s.close()
        start_time=time.time()
print("state took:",time.time()-start_time2)