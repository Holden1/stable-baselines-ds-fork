from collections import deque
from os import system
import numpy as np
import win32ui
from grabber import Grabber
import time
import os
import sys
from directkeys import W,A,S,D,P,U,E,Q,T,L,I,R,F1,F2,F3,F11,NUM1,NUM2,NUM4,SPACE,G,E,PressKey,ReleaseKey,ReleaseKeys,PressAndRelease,PressAndFastRelease
from numpy import genfromtxt
from windowMgr import WindowMgr
import os
import subprocess
import threading
from gym import spaces
import math
import pickle
import socket
import yaml


DARKSOULSDIR="C:\Program Files (x86)\Steam\steamapps\common\DARK SOULS III\Game\DarkSoulsIII.exe"
FRAME_DIFF=0.2
SAVE_PROGRESS_SHADOWPLAY=False
SAVE_KILLS_SHADOWPLAY=True


HERO_BASE_HP=454
HEALTH_REWARD_MULTIPLIER=2.5
REWARD_DISTANCE=5
ESTUS_NEGATIVE_REWARD=0.1
PARRY_REWARD=0.1
TIMESTEPS_DEFENSIVE_BEHAVIOR=2000
DEFENSIVE_BEHAVIOR_NEGATIVE_REWARD =0.002
BEHIND_REWARD=0.002
NOT_IN_FRONT_REWARD=0.001
CLOSE_DISTANCE_REWARD=0.001


not_responding_lock=threading.Lock()

areaKey="locationArea"
charHpKey="heroHp"
charSpKey="heroSp"
bossHpKey="targetedEntityHp"

num_state_scalars=243
num_history_states=5
num_prev_animations=1

parryAnimationName='DamageParryEnemy1' 

# Cheat engine socket info
HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 31000        # The port used by the cheat engine server     
DOTNETPORT = 31001        # The port used by the dotnet server     

def parse_val(value):
    try:
        val=float(value)
        return val
    except ValueError:
        if value=="??":
            return 0
        return value

class dsgym:
    
    observation_space=spaces.Box(-100,1000,shape=(num_history_states*num_state_scalars,))
    
    metadata=None
    def __init__(self, isMultiDiscrete=True):
        with open("bossconfigs/Vordt.yaml", "r") as ymlfile:
            self.boss_config = yaml.safe_load(ymlfile)
        self.bossAnimationSet = []
        self.charAnimationSet = []
        self.stateDict={}
        self.best_so_far=-100
        self.spawnCheckRespondingThread()
        self.paused=False
        self.start_time=-1
        stateDict=self.readState()
        self.isMultiDiscrete=isMultiDiscrete

        if (isMultiDiscrete):
            self.no_action=[0,0]
            #1) WASD Keys:  Discrete 5  - NOOP[0], W[1], A[2], S[3], D[4]  - params: min: 0, max: 4
            #2) Action:     Discrete 6  - NOOP[0], Jump[1], Attack[2], Block[3], estus[4], , Parry[5] - params: min: 0, max: 5
            if(self.boss_config["parryable"]):
                print("Multidiscrete action: Boss is parryable")
                self.action_space=spaces.MultiDiscrete([5,6])
            else:
                print("Multidiscrete action: Boss is NOT parryable")
                self.action_space=spaces.MultiDiscrete([5,5])
        else:
            self.no_action=0
            #1) WASD Keys:  Discrete 10  - NOOP[0], W[1], A[2], S[3], D[4], Jump[5], Attack[6], Block[7], estus[8], Parry[9]  - params: min: 0, max: 9
            if(self.boss_config["parryable"]):
                print("Discrete action: Boss is parryable")
                self.action_space=spaces.Discrete(10)
            else:
                print("Discrete action: Boss is NOT parryable")
                self.action_space=spaces.Discrete(9)
        
        self.set_initial_state()          
        if(stateDict[areaKey]!=self.boss_config["bonfire_area"] and stateDict[areaKey]!=self.boss_config["boss_area"]):
            print("starting and not in bonfire or boss area, will set bonfire correct and suicide")
            self.suicide_and_set_bonfire()

    def set_initial_state(self):
        self.prev_input_actions = self.no_action
        self.prev_char_animations = deque([],maxlen=num_prev_animations)
        self.prev_boss_animations = deque([],maxlen=num_prev_animations)
        self.prev_state = deque([], maxlen=num_history_states)
        self.fill_frame_buffer=True
        self.within_reward_range=False
        self.episode_rew=0
        self.episode_len=0
        self.bossHpLastFrame=self.boss_config["base_hp"]
        self.bossAnimationLastFrame='??'
        self.bossAnimationFrameCount=0
        self.charHpLastFrame=HERO_BASE_HP
        self.charAnimationLastFrame='??'
        self.charAnimationFrameCount=0
        self.timesincecharacterattack=100
        self.timesincebossattack=100
        self.timesincebosslosthp=100
        self.timesinceherolosthp=100
        self.timesinceheroparry=100
        self.bosshpdiff=0
        self.charhpdiff=0
        self.numEstusLastFrame=0
        self.start_time=time.time()
        self.info={}
        for _ in range(num_prev_animations):
            self.prev_boss_animations.append(0)
            self.prev_char_animations.append(0)

    def unpause_wrapper(self):
        if(self.paused):
            PressAndFastRelease(U)
            self.paused=False

    def pause_wrapper(self):
        PressAndRelease(P)
        self.paused=True
    def speed_up_wrapper(self):
        PressAndRelease(I)
    def normal_speed_wrapper(self):
        PressAndFastRelease(U)

    def notresponding(self,name):
        #os.system('tasklist /FI "IMAGENAME eq %s" /FI "STATUS eq not responding" > tmp.txt' % name)
        #x = subprocess.check_output()
        a = subprocess.Popen('tasklist /FI "IMAGENAME eq %s" /FI "STATUS eq running"' % name,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        a=a.communicate()[0].decode("utf-8")
        b = subprocess.Popen('tasklist /FI "IMAGENAME eq WerFault.exe" /FI "STATUS eq running"',stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        b=b.communicate()[0].decode("utf-8")
        c = subprocess.Popen('tasklist /FI "IMAGENAME eq %s" /FI "STATUS ne running"' % name,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        c=c.communicate()[0].decode("utf-8")
        #tmp.close()
        if c.split("\n")[-2].startswith(name) or "INFO:" not in b:
            return True
        elif a.split("\n")[-2].startswith(name):
            return False
        else:
            return True

    def setDsInFocus(self):
        self.releaseAll()
        w=WindowMgr()
        w.find_window_wildcard(".*ARK SOULS.*")
        try:
            w.set_foreground()
        except:
            print("Had issues setting to foreground")
    def spawnCheckRespondingThread(self):
        thread = threading.Thread(target=self.CheckAndHandleNotResponding, args=())
        thread.daemon = True  # Daemonize thread
        thread.start()  # Start the execution

    def window_exists(self,window_name):
        try:
            win32ui.FindWindow(None, window_name)
            return True
        except win32ui.error:
            return False
    def CheckAndHandleNotResponding(self):
        while True:
            #Cheat engine might not be responding if it fails to attach debugger
            if(self.notresponding("DarkSoulsIII.exe") or self.window_exists("Error") or self.notresponding("cheatengine-x86_64.exe")):
                with not_responding_lock:
                    self.releaseAll()
                    print("Game not responding, waiting 5 seconds until restart")
                    PressAndRelease(U)
                    time.sleep(5)
                    if (self.notresponding("DarkSoulsIII.exe")or self.window_exists("Error") or self.notresponding("cheatengine-x86_64.exe")):
                        self.kill_processes()
                        os.system('".\\DarkSoulsIII.CT"')
                        time.sleep(5)
                        os.system('"'+DARKSOULSDIR+'"')
                        w=WindowMgr()
                        time.sleep(40)
                        PressAndRelease(T)
                        PressAndRelease(I)
                        w.find_window_wildcard(".*ARK SOULS.*")
                        iter=0
                        print("Spamming E to get into game",iter)
                        while iter<1000:
                            try:
                                w.set_foreground()
                            except:
                                print("Had issues setting to foreground")
                                                   
                            PressAndFastRelease(E)
                            iter+=1
                            stateDict=self.readState()

                            if(stateDict[areaKey]==self.boss_config["bonfire_area"]):
                                break #we are in game

                        time.sleep(5)
                        print("Assuming in game now")
                        PressAndRelease(T)
                        ReleaseKey(E)
            time.sleep(5)


    def teleToBoss(self):
        print("Teleporting to",self.boss_config["name"])
        self.setDsInFocus()
        for i in range(10):
            time.sleep(1)
            stateDict=self.readState()
            print(stateDict[areaKey])
            if(stateDict[areaKey]==self.boss_config["bonfire_area"]):
                print("Currently at bonfire area")
                break
        time.sleep(1)
        for i in range(100):
            self.waitForUnpause()
            self.check_responding_lock()   
            PressAndFastRelease(F1)
            self.setCeState(self.boss_config["fog_gate_teleport"])
            PressAndFastRelease(Q)
            PressAndFastRelease(F1)
            PressAndRelease(U)#Normal speed
            time.sleep(1)
            PressAndRelease(E)
            PressAndRelease(E)#Twice, bloodstain can be at entrance
            time.sleep(2)
            #Check whether we have entered boss area
            stateDict=self.readState()
            if(stateDict[areaKey]==self.boss_config["boss_area"]):
                self.setCeState(self.boss_config["boss_teleport"])
                PressAndFastRelease(F1)
                PressAndFastRelease(Q)
                PressAndFastRelease(F2)
                PressAndFastRelease(T)
                self.sendString("updateAddress \n",DOTNETPORT)
                time.sleep(0.2)
                stateDict = self.readState(1,DOTNETPORT)
                bossHp=self.parseStateDictValue(stateDict,"targetedEntityHp")
                if(stateDict["targetLock"]=="1" and bossHp!=0 and bossHp < (self.boss_config["base_hp"]*2)):
                    break # Make sure we have target and correct targeted entity by checking hp
                else:
                    print("Retrying teleport as we either didn't have target or bosshp was wrong targetlock: ",stateDict["targetLock"], " bossHp: ",bossHp)
            elif i%50==49:
                print("Tried 50 times, killing self and resetting boss")
                self.suicide_and_set_bonfire()
                time.sleep(20)

        else:   #For loop else, not if else
                #didn't get to boss area in many tries, commit sudoku and kill both processes
            self.suicide_and_set_bonfire()
            print("Couldn't get to boss in 50 tries, something wrong, killing processes as well")
            self.kill_processes()

    def kill_or_wait(self,start_read):
        elapsed = int(time.time() - start_read)
        max_wait_time = 30
        print("waiting for loading screen", elapsed, " of max", max_wait_time)
        if elapsed >= max_wait_time:
            self.kill_processes()
            # wait for restart thread to pick it up, then wait for lock
            time.sleep(10)
            self.check_responding_lock()
        else:
            time.sleep(1)
    def suicide_and_set_bonfire(self):
        self.setCeState({"LastBonfire": self.boss_config["bonfire_id"]})
        PressAndRelease(F2)
        PressAndRelease(F3)

    def setCeState(self,dict):
        str_to_send = ""
        
        for key,value in dict.items():
            str_to_send+=str(key)+"="+str(value)+" "
        str_to_send+="\n"
        self.sendString(str_to_send)
    
    def sendString(self, stringToSend,port=PORT):
        hasSent=False
        while (hasSent==False):
            try:
                print("Trying to send: ",stringToSend)
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((HOST, port))
                self.socket.setblocking(False)
                self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
                self.socket.send(bytes(stringToSend,"utf-8"))
            except BaseException as err:
                print("Couldn't send to socket, will retry connecting , err: ",err)
            finally:
                self.socket.close()
            hasSent=True


    def readState(self,timeout=10,port=31000):
        hasRead=False
        start_read=time.time()

        while (hasRead==False):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((HOST, port))
                self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
                self.socket.send(b'getState \n')
                self.socket.settimeout(timeout)
                data = self.socket.recv(1024)
                loglines=data.decode("utf-8")
            except socket.timeout:
                print("Timeout using prev state instead, closing socket so data flushed")
                break
            except Exception:
                print("Couldn't read from socket, will retry connecting")
                continue
            finally:
                self.socket.close()
            if not loglines or len(loglines.split(";;"))<22:
                continue
            for line in loglines.split(";;"):
                try:
                    (key,val) = line.split("::")
                    self.stateDict[key]=val
                except:
                    print("Had issues reading state, will try again, state was ",loglines)
                    break
            else:
                hasRead = True
        self.stateDict["didRead"]=hasRead
        return self.stateDict
    def reset(self):
        self.setDsInFocus()
        self.releaseAll()
        self.waitForUnpause()
        self.teleToBoss()
        self.setDsInFocus()
        self.set_initial_state()
        return self.step(self.no_action)[0]
    
    def waitForUnpause(self):
        #Using Global Speed as a pause button (f7 and f8 in cheatengine)
        stateDict=self.readState()
        if stateDict["Global Speed"]=="0":
            self.releaseAll()
            print("Script paused as Global Speed is 0, waiting for unpause ....")
            while stateDict["Global Speed"]=="0":
                time.sleep(1)
                stateDict=self.readState()
            print("Global Speed is not 0 anymore, script is unpaused")


    def can_reset(self):
        self.releaseAll()
        stateDict=self.readState()
        #self.CheckAndHandleNotResponding()
        return stateDict[charHpKey] !=0

    def kill_processes(self):
        os.system("taskkill /f /im  DarkSoulsIII.exe /T")
        # also kill cheat engine
        os.system("taskkill /f /im  cheatengine-x86_64.exe /T")
    def check_responding_lock(self):
        not_responding_lock.acquire()
        not_responding_lock.release()

    def step(self,input_actions):
        terminal=False
        reward=0.0

        self.unpause_wrapper()
        #Check if able to take not responding lock
        
        self.check_responding_lock()
        self.ensure_framerate()
        stateDict = self.readState(10,DOTNETPORT)

        #Check if we died
        if(stateDict[charHpKey]=="0" or stateDict[areaKey]!=self.boss_config["boss_area"] or stateDict[areaKey]=="??"):
            #Unpause game and wait for hp>0
            self.releaseAll()
            PressAndRelease(U)
            terminal=True
            reward=-1
        #Check if we killed the boss or missing boss into
        elif stateDict[bossHpKey]=="0" or stateDict[bossHpKey]=="??":
            self.releaseAll()
            if stateDict[bossHpKey]=="0":
                terminal=True
                print("killed boss")
                PressAndRelease(G)
                PressAndRelease(E)
                time.sleep(5)
                reward=1
            PressAndRelease(U)
            self.suicide_and_set_bonfire()
            
        #Check if lost target on boss
        elif stateDict["targetLock"]=="0":
            print("Lost target, retargeting until i die or 1000 times")
            numtries=1000
            while stateDict["targetLock"]=="0" and stateDict[charHpKey]!="0" and numtries >0:
                self.releaseAll()
                PressAndFastRelease(Q)
                stateDict=self.readState()
                numtries = numtries-1      
        #Input action
        self.handleAction(input_actions)    

        #handle lost life of boss or char  
        self.bosshpdiff=0
        self.charhpdiff=0
        if stateDict[bossHpKey]!="??" and self.bossHpLastFrame>int(stateDict[bossHpKey]):
            self.bosshpdiff=self.bossHpLastFrame-int(stateDict[bossHpKey])
            reward+=(self.bosshpdiff/self.boss_config["base_hp"])*HEALTH_REWARD_MULTIPLIER
            self.timesincebosslosthp=0
        else:
            self.timesincebosslosthp = self.timesincebosslosthp+1
            if self.timesincebosslosthp > TIMESTEPS_DEFENSIVE_BEHAVIOR:
                print("Agent is playing too defensively, negative reward")
                reward -=DEFENSIVE_BEHAVIOR_NEGATIVE_REWARD

        #If our hp is different from last frame, can result in reward if char got healed
        if stateDict[charHpKey]!="??" and int(stateDict[charHpKey])!=int(self.charHpLastFrame):
            self.charhpdiff=int(self.charHpLastFrame)-int(stateDict[charHpKey])
            reward-=self.charhpdiff/HERO_BASE_HP
            self.timesinceherolosthp=0
        else:
            self.timesinceherolosthp+=1

        if self.bossAnimationLastFrame!=parryAnimationName and stateDict['targetAnimationName']==parryAnimationName:
            reward+=PARRY_REWARD
            print("Got reward for parrying, last animation: ", self.bossAnimationLastFrame, " current animation: ", stateDict['targetAnimationName'])
            self.timesinceheroparry=0
        else:
            self.timesinceheroparry+=1

        #Keep hero close to boss and incentivise being alive
        if self.calc_dist(stateDict) < REWARD_DISTANCE:
            reward+=CLOSE_DISTANCE_REWARD
            self.within_reward_range=True
        else:
            reward-=CLOSE_DISTANCE_REWARD
            self.within_reward_range=False

        #Reward for being behind boss
        diffAngle = self.calc_diff_angle(stateDict)
        if (abs(diffAngle)>45):
            print(f"Not in front of boss getting {NOT_IN_FRONT_REWARD} reward")
            reward+=NOT_IN_FRONT_REWARD
        if (abs(diffAngle)>135):
            print(f"Behind boss, getting {BEHIND_REWARD} reward")
            reward+=BEHIND_REWARD
        #penalize using estus to prevent spam
        numEstus=self.parseStateDictValue(stateDict,"numEstus")
        if (self.numEstusLastFrame>numEstus):
            #penalize using estus to prevent spam
            #also prevents estus being used above ~80%life
            reward-=ESTUS_NEGATIVE_REWARD
        self.numEstusLastFrame=numEstus

        if stateDict[bossHpKey]!="??":
            self.bossHpLastFrame=int(stateDict[bossHpKey])
        if stateDict[charHpKey]!="??":
            self.charHpLastFrame=int(stateDict[charHpKey])
        
        if self.bossAnimationLastFrame == stateDict['targetAnimationName']:
            self.bossAnimationFrameCount+=1
        else:
            self.bossAnimationLastFrame=stateDict['targetAnimationName']
            if self.bossAnimationLastFrame in self.bossAnimationSet:
                self.prev_boss_animations.append(self.bossAnimationSet.index(self.bossAnimationLastFrame))
            else:
                self.bossAnimationSet.append(self.bossAnimationLastFrame)
                self.prev_boss_animations.append(self.bossAnimationSet.index(self.bossAnimationLastFrame))
                print(self.bossAnimationLastFrame,"did not exist in bossAnimationList, adding it")
            
            self.bossAnimationFrameCount=0
        
        if self.charAnimationLastFrame == stateDict['heroAnimationName']:
            self.charAnimationFrameCount+=1
        else:
            self.charAnimationLastFrame=stateDict['heroAnimationName']
            if self.charAnimationLastFrame in self.charAnimationSet:
                self.prev_char_animations.append(self.charAnimationSet.index(self.charAnimationLastFrame))
            else:
                self.charAnimationSet.append(self.charAnimationLastFrame)
                self.prev_char_animations.append(self.charAnimationSet.index(self.charAnimationLastFrame))
                print(stateDict['heroAnimationName'],"did not exist in heroAnimationList adding it")
            self.charAnimationFrameCount=0
        if "Attack" in stateDict['targetAnimationName']:
            self.timesincebossattack=0
        else:
            self.timesincebossattack+=1

        stateDict["reward"]=reward
        self.add_state(input_actions,stateDict)
        self.episode_len+=1
        self.episode_rew+=reward
        if terminal:
            self.releaseAll()
            self.info={'episode':{'r':self.episode_rew,'l':self.episode_len,'kill':stateDict[bossHpKey]=="0",'bosshp':self.bossHpLastFrame}}
            #Save shadowplay recording
            
            if(self.episode_rew>self.best_so_far and SAVE_PROGRESS_SHADOWPLAY):
                print("Saving shadowplay because of best ep rew>best so far")
                print("Episode rew:",self.episode_rew)
                print("Best episode rew:",self.best_so_far)
                PressAndFastRelease(F11)
                self.best_so_far=self.episode_rew
            if(stateDict[bossHpKey]=="0" and SAVE_KILLS_SHADOWPLAY):
                print("Saving shadowplay as boss was killed")
                PressAndFastRelease(F11)
            self.episode_rew=0
            self.episode_len=0
            self.fill_frame_buffer=True #Fill buffer next time, if we died
            PressAndRelease(I) #speed up when dead
        
        return np.hstack(self.prev_state), reward, terminal, self.info

    def releaseAll(self):
        ReleaseKeys([P,W,A,S,D,E,R,SPACE,NUM1,NUM2,NUM4])

    def handleAction(self,input_actions):
        self.releasePreviousActions(self.prev_input_actions,input_actions)
        if(self.isMultiDiscrete):
            if input_actions[0] == 1:
                PressKey(W)
            if input_actions[0] == 2:
                PressKey(A)
            if input_actions[0] == 3:
                PressKey(S)
            if input_actions[0] == 4:
                PressKey(D)
            if input_actions[1] == 1:
                PressKey(SPACE)
            if input_actions[1] == 2:
                self.timesincecharacterattack=0
                PressKey(NUM1)
            else:
                self.timesincecharacterattack+=1
            if input_actions[1] == 3:
                PressKey(NUM2)
            if input_actions[1] == 4:
                if self.numEstusLastFrame == 0:
                    pass
                else:
                    PressKey(R)
            if input_actions[1] == 5:
                PressKey(NUM4)
        else:
            if input_actions == 1:
                PressKey(W)
            if input_actions == 2:
                PressKey(A)
            if input_actions == 3:
                PressKey(S)
            if input_actions== 4:
                PressKey(D)
            if input_actions== 5:
                PressKey(SPACE)
            if input_actions == 6:
                self.timesincecharacterattack=0
                PressKey(NUM1)
            else:
                self.timesincecharacterattack+=1
            if input_actions == 7:
                PressKey(NUM2)
            if input_actions == 8:
                if self.numEstusLastFrame == 0:
                    pass
                else:
                    PressKey(R)
            if input_actions == 9:
                PressKey(NUM4)
        
        self.prev_input_actions=input_actions

    def releasePreviousActions(self, prevaction, curaction):
        keys = []
        if(self.isMultiDiscrete):
            if prevaction[0] != curaction[0]:
                if prevaction[0] ==1:
                    keys.append(W)
                if prevaction[0] ==2:
                    keys.append(A)
                if prevaction[0] ==3:
                    keys.append(S)
                if prevaction[0] ==4:
                    keys.append(D)
            
            if prevaction[1] != curaction[1]:
                if prevaction[1] ==1:        
                    keys.append(SPACE)
                if prevaction[1] ==2:
                    keys.append(NUM1)
                if prevaction[1] ==3:
                    keys.append(NUM2)
                if prevaction[1] ==4:
                    keys.append(NUM4)
                if prevaction[1] ==5:
                    keys.append(R)
        else:
            if(prevaction==curaction):
                return
            else:
                if curaction <5: #only release movement key if new movement detected 
                    if curaction !=1:
                        keys.append(W)
                    if curaction !=2:
                        keys.append(A)
                    if curaction !=3:
                        keys.append(S)
                    if curaction !=4:
                        keys.append(D)
                if curaction >=5: #only release action key if new action is detected
                    if curaction !=5:        
                        keys.append(SPACE)
                    if curaction !=6:
                        keys.append(NUM1)
                    if curaction !=7:
                        keys.append(NUM2)
                    if curaction !=8:
                        keys.append(NUM4)
                    if curaction !=9:
                        keys.append(R)

        ReleaseKeys(keys)

#Function makes it possible to hold key pressed, valuable for blocking or moving
    def releaseAllExcept(self, action):
        #Always release attack key and parry key. Holding attack key does not make sense
        keys=[P,E,NUM1,NUM4,R]

        if action[0] !=1:
            keys.append(W)
        if action[0] !=2:
            keys.append(A)
        if action[0] !=3:
            keys.append(S)
        if action[0] !=4:
            keys.append(D)
        if action[1] !=1:        
            keys.append(SPACE)
        if action[1] !=2:
            keys.append(NUM1)
        if action[1] !=3:
            keys.append(NUM2)
        if action[1] !=4:
            keys.append(NUM4)

        ReleaseKeys(keys)

    def ensure_framerate(self):
         # Sleep to ensure consistency in frames
        if self.start_time != -1:
            elapsed = time.time() - self.start_time
            timeToSleep = FRAME_DIFF - elapsed
            if timeToSleep > 0:
                time.sleep(timeToSleep)
                #print("New elapsed ",time.time()-start_time)
            else:
                print("Didn't sleep:",elapsed)
        self.start_time = time.time()

    def parseStateDictValue(self,stateDict,key):
        if (stateDict[key]=="??" or stateDict[key]==""):
            return 0
        else:
            try:
                return float(stateDict[key].replace(",","."))
            except:
                print("Couldn't transform value to float for key: ",key, "using 0 instead, value was: ",stateDict[key])
                return 0
    def calc_dist(self,stateDict):
        targetx=self.parseStateDictValue(stateDict,"targetedEntityX")
        targety=self.parseStateDictValue(stateDict,"targetedEntityY")
        herox=self.parseStateDictValue(stateDict,"heroX")
        heroy=self.parseStateDictValue(stateDict,"heroY")
        return math.sqrt((targetx-herox)**2+(targety-heroy)**2)

    def calc_diff_angle(self,stateDict):
        targetAngle=self.parseStateDictValue(stateDict,"targetedEntityAngle")
        heroAngle=self.parseStateDictValue(stateDict,"heroAngle")
        heroX=self.parseStateDictValue(stateDict,"heroX")
        heroY=self.parseStateDictValue(stateDict,"heroY")
        targetedEntityX=self.parseStateDictValue(stateDict,"targetedEntityX")
        targetedEntityY=self.parseStateDictValue(stateDict,"targetedEntityY")
        
        angleBetween=(math.atan2(targetedEntityX-heroX,targetedEntityY-heroY)+math.pi)*57.29
        if angleBetween >180:
            angleBetween= 360-angleBetween
        targetAngle=targetAngle*90

        diffAngle = targetAngle-angleBetween
    def print_state_dict(self,stateDict):
        _ = system('cls') 
        for k in stateDict:
            print (k,stateDict[k])

    def save_state(self,save_path):
        with open(save_path+"envstate.pkl", "wb") as file_handler:
            objtosave={}
            objtosave["bossAnimation"]= self.bossAnimationSet
            objtosave["charAnimation"]= self.charAnimationSet
            pickle.dump(objtosave, file_handler)
    def load_state(self,load_path):
        with open(load_path.replace(".zip","envstate.pkl"), "rb") as file_handler:
            loadedobj = pickle.load(file_handler)
            self.bossAnimationSet=loadedobj["bossAnimation"]
            self.charAnimationSet=loadedobj["charAnimation"]
    def add_state(self,action_to_add,stateDict):

        teleX=self.boss_config["boss_teleport"]["heroX"]
        teleY=self.boss_config["boss_teleport"]["heroY"]
        teleZ=self.boss_config["boss_teleport"]["heroZ"]

        targetXScaled=(self.parseStateDictValue(stateDict,"targetedEntityX") - teleX)/10
        targetYScaled=(self.parseStateDictValue(stateDict,"targetedEntityY") - teleY)/10
        heroXScaled=(self.parseStateDictValue(stateDict,"heroX") - teleX)/10
        heroYScaled=(self.parseStateDictValue(stateDict,"heroY") - teleY)/10

        stateToAdd=np.zeros(num_state_scalars)
        if(self.isMultiDiscrete):
            stateToAdd[action_to_add[0]]=1
            stateToAdd[action_to_add[1]+5]=1
        else:
            stateToAdd[action_to_add]=1
        targetMaxHp=self.parseStateDictValue(stateDict,"TargetMaxHp")
        if targetMaxHp !=0:
            stateToAdd[12]=self.parseStateDictValue(stateDict,"targetedEntityHp")/targetMaxHp
        stateToAdd[13]=targetXScaled
        stateToAdd[14]=targetYScaled
        stateToAdd[15]=self.parseStateDictValue(stateDict,"targetedEntityZ")
        stateToAdd[16]=self.parseStateDictValue(stateDict,"targetMovement1")
        stateToAdd[17]=self.parseStateDictValue(stateDict,"targetMovement2")
        stateToAdd[18]=self.parseStateDictValue(stateDict,"targetComboAttack")
        heroMaxHp=self.parseStateDictValue(stateDict,"heroMaxHp")
        if heroMaxHp!=0:
            stateToAdd[19]=self.parseStateDictValue(stateDict,"heroHp")/heroMaxHp
        stateToAdd[20]=heroXScaled
        stateToAdd[21]=heroYScaled

        dist=self.calc_dist(stateDict)
        stateToAdd[22]=dist
        heroAngle=self.parseStateDictValue(stateDict,"heroAngle")
        stateToAdd[23]=heroAngle
        heroMaxSp=self.parseStateDictValue(stateDict,"heroMaxSp")
        if heroMaxSp!=0:
            stateToAdd[24]=self.parseStateDictValue(stateDict,"heroSp")/heroMaxSp
        stateToAdd[25]=stateDict["reward"]
        stateToAdd[26]=self.timesincecharacterattack
        stateToAdd[27]=self.timesincebossattack
        estus=self.parseStateDictValue(stateDict,"numEstus")
        stateToAdd[28]=estus
        if estus>0:
            stateToAdd[29]=1
        if self.within_reward_range:
            stateToAdd[30]=1
        if targetMaxHp !=0:
            stateToAdd[31]=self.bosshpdiff/targetMaxHp
        if heroMaxHp!=0:
            stateToAdd[32]=self.charhpdiff/heroMaxHp
        stateToAdd[33]=self.bossAnimationFrameCount
        stateToAdd[34]=self.charAnimationFrameCount
        stateToAdd[35]=self.timesinceherolosthp

        diffAngle = self.calc_diff_angle(stateDict)
        diffAngleScaled = diffAngle/180
        stateToAdd[36]=diffAngleScaled
        stateToAdd[37]=abs(diffAngleScaled)
        absDiff= abs(diffAngle)
        if absDiff>135:
            stateToAdd[38]=1
        elif absDiff<=135 and absDiff>=45:
            if diffAngle>0:
                stateToAdd[39]=1
            else:
                stateToAdd[40]=1
        else:
            stateToAdd[41]=1
        
        if(self.stateDict["didRead"]):
            stateToAdd[42]=1
        charAnimationStartIndex=43
        #Allow for 100 char animations and 100 boss animations
        charAnimationLength=100
        bossAnimationStartIndex= charAnimationStartIndex+charAnimationLength

        #One hot encode prev and current animations
        charAnimationIndex=charAnimationStartIndex+self.prev_char_animations[0]
        stateToAdd[charAnimationIndex]=1
        bossAnimationIndex=bossAnimationStartIndex+self.prev_boss_animations[0]
        stateToAdd[bossAnimationIndex]=1

        if self.fill_frame_buffer:
            for _ in range(num_history_states):
                self.prev_state.append(stateToAdd)
            self.fill_frame_buffer = False
        else:
            self.prev_state.append(stateToAdd)


def bin_array(num, m):
    """Convert a positive integer num into an m-bit bit vector"""
    return np.array(list(np.binary_repr(num).zfill(m))).astype(np.int8)