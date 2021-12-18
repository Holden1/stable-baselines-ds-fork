#!/usr/bin/env python
from gameState import dsgym
import time
import math
      
        
import yaml

def main():
    mygym=dsgym()
    
    while 1:
        state=mygym.readState()
        targetAngle=mygym.parseStateDictValue(state,"targetedEntityAngle")
        heroAngle=mygym.parseStateDictValue(state,"heroAngle")
        heroX=mygym.parseStateDictValue(state,"heroX")
        heroY=mygym.parseStateDictValue(state,"heroY")
        targetedEntityX=mygym.parseStateDictValue(state,"targetedEntityX")
        targetedEntityY=mygym.parseStateDictValue(state,"targetedEntityY")
        time.sleep(1)
        
        angleBetween=(math.atan2(targetedEntityX-heroX,targetedEntityY-heroY)+math.pi)*57.29
        if angleBetween >180:
            angleBetween= 360-angleBetween
        targetAngle=targetAngle*90
        #print("Angle char position: ",angleBetween)
        #print("Target angle position: ",targetAngle)
        #print("deg between: ",targetAngle-angleBetween)

        diffAngle = targetAngle-angleBetween
        absDiff= abs(diffAngle)
        if absDiff>135:
            print("behind")
        elif absDiff<=135 and absDiff>=45:
            if diffAngle>0:
                print("right Side")
            else:
                print("left side")
        else:
            print("front")

if __name__ == '__main__':
    main()
