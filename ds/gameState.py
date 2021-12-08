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
NO_ACTION=[0,0]

HERO_BASE_HP=454
HEALTH_REWARD_MULTIPLIER=2.5
REWARD_DISTANCE=5
ESTUS_NEGATIVE_REWARD=0.3
PARRY_REWARD=0.1
TIMESTEPS_DEFENSIVE_BEHAVIOR=200
DEFENSIVE_BEHAVIOR_NEGATIVE_REWARD =0.002

start_time=-1
not_responding_lock=threading.Lock()

areaKey="locationArea"
charHpKey="heroHp"
charSpKey="heroSp"
bossHpKey="targetedEntityHp"

num_state_scalars=74
num_history_states=5
num_prev_animations=2

parryAnimationName='DamageParryEnemy1' 

# Cheat engine socket info
HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 31000        # The port used by the server     

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
    #1) WASD Keys:  Discrete 5  - NOOP[0], W[1], A[2], S[3], D[4]  - params: min: 0, max: 4
    #2) Action:     Discrete 6  - NOOP[0], Jump[1], Parry[2], Block[3], Attack[4], estus[5] - params: min: 0, max: 5
    action_space=spaces.MultiDiscrete([5,6])
    metadata=None
    def __init__(self):
        with open("bossconfigs/Vordt.yaml", "r") as ymlfile:
            self.boss_config = yaml.safe_load(ymlfile)
        self.bossAnimationSet = []
        self.charAnimationSet = []
        self.best_so_far=-100
        self.set_initial_state()      
        self.spawnCheckRespondingThread()
        self.logfile = open("gameInfo.txt", "r", encoding="utf-8")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((HOST, PORT))
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        self.paused=False

    def set_initial_state(self):
        self.prev_input_actions = NO_ACTION
        self.prev_char_animations = deque([],maxlen=num_prev_animations)
        self.prev_boss_animations = deque([],maxlen=num_prev_animations)
        self.prev_state = deque([], maxlen=num_history_states)
        self.fill_frame_buffer=True
        self.episode_rew=0
        self.episode_len=0
        self.bossHpLastFrame=self.boss_config["base_hp"]
        self.bossAnimationLastFrame='??'
        self.bossAnimationFrameCount=0
        self.charHpLastFrame=HERO_BASE_HP
        self.charAnimationLastFrame='??'
        self.charAnimationFrameCount=0
        self.timesincecharacterattack=0
        self.timesincebossattack=0
        self.timesincebosslosthp=0
        self.timesinceherolosthp=0
        self.timesinceheroparry=0
        self.numEstusLastFrame=0
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
            if(self.notresponding("DarkSoulsIII.exe") or self.window_exists("Error") or self.notresponding("cheatengine-x86_64.exe") or self.window_exists("Lua Engine")):
                with not_responding_lock:
                    self.releaseAll()
                    print("Game not responding, waiting 5 seconds until restart")
                    PressAndRelease(U)
                    time.sleep(5)
                    if (self.notresponding("DarkSoulsIII.exe")or self.window_exists("Error") or self.notresponding("cheatengine-x86_64.exe") or self.window_exists("Lua Engine")):
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
        time.sleep(5)
        for i in range(50):
            self.waitForUnpause()
            self.check_responding_lock()
            self.setCeState(self.boss_config["fog_gate_teleport"])
            time.sleep(1)
            PressAndRelease(U)#Normal speed
            PressAndRelease(E)
            PressAndRelease(E)#Twice, bloodstain can be at entrance
            time.sleep(2)
            #Check whether we have entered boss area
            stateDict=self.readState()
            if(stateDict[areaKey]==self.boss_config["boss_area"]):
                self.setCeState(self.boss_config["boss_teleport"])
                time.sleep(1)
                PressAndRelease(Q)
                PressAndFastRelease(T)
                break
            elif i%20:
                print("Tried 20 times, killing self and resetting boss")
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
        PressAndRelease(F3)

    def setCeState(self,dict):
        str_to_send = ""
        hasSent=False
        for key,value in dict.items():
            str_to_send+=str(key)+"="+str(value)+" "
        str_to_send+="\n"
        while (hasSent==False):
            try:
                print("Trying to send: ",str_to_send)
                self.socket.send(bytes(str_to_send,"utf-8"))
            except BaseException as err:
                print("Couldn't send to socket, will retry connecting , err: ",err)
                try:
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.connect((HOST, PORT))
                    self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
                except:
                    print("Couldn't reconnect")
                continue
            hasSent=True


    def readState(self):
        hasRead=False
        start_read=time.time()

        while (hasRead==False):
            try:
                self.socket.send(b'getState \n')
                data = self.socket.recv(1024)
                #print('Received', repr(data))
                loglines=data.decode("utf-8")
            except:
                print("Couldn't read from socket, will retry connecting")
                try:
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.connect((HOST, PORT))
                    self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
                except:
                    print("Couldn't reconnect")
                continue
            if not loglines or len(loglines.split(";;"))<22:
                continue
            stateDict= {}
            for line in loglines.split(";;"):
                try:
                    (key,val) = line.split("::")
                    stateDict[key]=val
                except:
                    print("Had issues reading state, will try again")
                    break
            else:
                hasRead = True
        return stateDict
    def reset(self):
        self.setDsInFocus()
        self.releaseAll()
        self.waitForUnpause()
        self.teleToBoss()
        self.setDsInFocus()
        self.set_initial_state()
        return self.step(NO_ACTION)[0]
    
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
        stateDict = self.readState()
        #Check if we died
        if(stateDict[charHpKey]=="0" or stateDict[areaKey]==self.boss_config["bonfire_area"] or stateDict[areaKey]=="??"):
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
            print("Lost target, retargeting until i die")
            while stateDict["targetLock"]=="0" and stateDict[charHpKey]!="0":
                self.releaseAll()
                PressAndFastRelease(Q)
                stateDict=self.readState()      
        #Input action
        self.handleAction(input_actions)      
        
        if stateDict[bossHpKey]!="??" and self.bossHpLastFrame>int(stateDict[bossHpKey]):
            hpdiff=self.bossHpLastFrame-int(stateDict[bossHpKey])
            reward+=(hpdiff/self.boss_config["base_hp"])*HEALTH_REWARD_MULTIPLIER
            self.timesincebosslosthp=0
        else:
            self.timesincebosslosthp = self.timesincebosslosthp+1
            if self.timesincebosslosthp > TIMESTEPS_DEFENSIVE_BEHAVIOR:
                print("Agent is playing too defensively, negative reward")
                reward -=DEFENSIVE_BEHAVIOR_NEGATIVE_REWARD

        #If our hp is different from last frame, can result in reward if char got healed
        if stateDict[charHpKey]!="??" and int(stateDict[charHpKey])!=int(self.charHpLastFrame):
            hpdiff=int(self.charHpLastFrame)-int(stateDict[charHpKey])
            reward-=hpdiff/HERO_BASE_HP
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
            reward+=0.001
        else:
            reward-=0.001

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
            PressKey(NUM4)
        if input_actions[1] == 5:
            if self.numEstusLastFrame == 0:
                pass
            else:
                PressKey(R)
        self.prev_input_actions=input_actions

    def releasePreviousActions(self, prevaction, curaction):
        keys = []
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
        global start_time
         # Sleep to ensure consistency in frames
        if start_time != -1:
            elapsed = time.time() - start_time
            timeToSleep = FRAME_DIFF - elapsed
            if timeToSleep > 0:
                time.sleep(timeToSleep)
                #print("New elapsed ",time.time()-start_time)
            else:
                print("Didn't sleep")
        start_time = time.time()

    def parseStateDictValue(self,stateDict,key):
        if (stateDict[key]=="??" or stateDict[key]==""):
            return 0
        else:
            try:
                return float(stateDict[key].replace(",","."))
            except:
                print("Couldn't transform value to float for key: ",key, "using 0 instead")
                return 0
    def calc_dist(self,stateDict):
        targetx=self.parseStateDictValue(stateDict,"targetedEntityX")
        targety=self.parseStateDictValue(stateDict,"targetedEntityY")
        herox=self.parseStateDictValue(stateDict,"heroX")
        heroy=self.parseStateDictValue(stateDict,"heroY")
        return math.sqrt((targetx-herox)**2+(targety-heroy)**2)

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
        targetX=self.parseStateDictValue(stateDict,"targetedEntityX")
        targetY=self.parseStateDictValue(stateDict,"targetedEntityY")
        heroX=self.parseStateDictValue(stateDict,"heroX")
        heroY=self.parseStateDictValue(stateDict,"heroY")

        stateToAdd=np.zeros(num_state_scalars)
        stateToAdd[action_to_add[0]]=1
        stateToAdd[action_to_add[1]+5]=1
        stateToAdd[12]=self.parseStateDictValue(stateDict,"targetedEntityHp")
        stateToAdd[13]=targetX
        stateToAdd[14]=targetY
        stateToAdd[15]=self.parseStateDictValue(stateDict,"targetedEntityZ")
        targetAngle=self.parseStateDictValue(stateDict,"targetedEntityAngle")
        stateToAdd[16]=targetAngle
        stateToAdd[17]=self.parseStateDictValue(stateDict,"targetAttack1")
        stateToAdd[18]=float(self.parseStateDictValue(stateDict,"targetAttack2"))
        stateToAdd[19]=self.parseStateDictValue(stateDict,"targetMovement1")
        stateToAdd[20]=self.parseStateDictValue(stateDict,"targetMovement2")
        stateToAdd[21]=self.parseStateDictValue(stateDict,"targetComboAttack")
        stateToAdd[22]=self.parseStateDictValue(stateDict,"heroHp")
        stateToAdd[23]=heroX
        stateToAdd[24]=heroY

        dist=self.calc_dist(stateDict)
        stateToAdd[25]=dist
        heroAngle=self.parseStateDictValue(stateDict,"heroAngle")
        stateToAdd[26]=heroAngle
        stateToAdd[27]=self.parseStateDictValue(stateDict,"heroSp")
        stateToAdd[28]=stateDict["reward"]
        stateToAdd[29]=stateDict["HeroAnimationCounter"]
        stateToAdd[30]=self.timesincecharacterattack
        stateToAdd[31]=self.timesincebossattack
        stateToAdd[32]=stateDict["BossAnimationCounter"]
        estus=self.parseStateDictValue(stateDict,"numEstus")
        stateToAdd[33]=estus
        if estus>0:
            stateToAdd[34]=1
        stateToAdd[35]=math.sin(heroAngle)
        stateToAdd[36]=math.cos(heroAngle)
        stateToAdd[37]=math.sin(targetAngle)
        stateToAdd[38]=math.cos(targetAngle)
        stateToAdd[39]=heroX-targetX
        stateToAdd[39]=heroY-targetY
        stateToAdd[40]=self.timesincebosslosthp
        stateToAdd[41]=stateDict["BossAnimationCounter"]
        stateToAdd[42]=stateDict["HeroAnimationCounter"]
        stateToAdd[43]=self.timesinceherolosthp
        stateToAdd[44]=self.timesinceheroparry
        charAnimationStartIndex=45
        
        #binary encode current and prev animations
        for j in range(num_prev_animations):
            bossAnimationAsBinary = bin_array(self.prev_boss_animations[j],7)
            charAnimationAsBinary = bin_array(self.prev_char_animations[j],7)
            for i in range(7):
                stateToAdd[charAnimationStartIndex+i+(14*j)]=bossAnimationAsBinary[i]
            for i in range(7):
                stateToAdd[charAnimationStartIndex+7+i+(14*j)]=charAnimationAsBinary[i]          

        if self.fill_frame_buffer:
            for _ in range(num_history_states):
                self.prev_state.append(stateToAdd)
            self.fill_frame_buffer = False
        else:
            self.prev_state.append(stateToAdd)


def bin_array(num, m):
    """Convert a positive integer num into an m-bit bit vector"""
    return np.array(list(np.binary_repr(num).zfill(m))).astype(np.int8)