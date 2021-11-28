#!/usr/bin/env python
from gameState import dsgym

      
        
import math

def main():
    env=dsgym()
    animationsSet= set()
    animationList=['', 'FallStartFaceUp', 'GuardDamageMiddle', 'DamagePush', 'FallDeath', 'Idle', 'DamageSmall', 'GuardDamageSmall', 'RunStopRight', 'AttackRightLightDash', 'AttackRightLight2', 'DamageSmallBlow', '??', 'QuickTurnLeft180', 'HandChangeStart', 'RollingMedium', 'QuickTurnRight180', 'DamageMiddle', 'ThrowDef', 'AttackRightLightStep', 'EStepDown', 'Event60060', 'DamageExLarge', 'AddDamageStartFront', 'DeathStart', 'RunStopFront', 'AttackRightLight3', 'RunStopLeft', 'GuardStart', 'GuardEnd', 'FallDeathFaceUp', 'HandChangeEnd', 'BackStepNomal', 'RunStopBack', 'RollingMediumSelftra', 'AttackRightLightKick', 'GuardOn', 'DamageLarge', 'Event63000', 'ParryLeftStart', 'FallDeathLoop', 'ThrowAtk', 'FallLoop', 'AttackRightLight1', 'FallDeathLoopFaceUp', 'DamageUpper', 'FallStart', 'GuardBreak', 'Move', 'DeathIdle']
    while(True):
        state=env.readState()
        animationsSet.add(state["heroAnimationName"])
        #env.print_state_dict(state)
        #print("Animations:",animationsSet)
        #print("Animation index:",len(animationList))
        targetX=parseStateDictValue(state,"targetedEntityX")
        targetY=parseStateDictValue(state,"targetedEntityY")
        heroX=parseStateDictValue(state,"heroX")
        heroY=parseStateDictValue(state,"heroY")
        print("Dist:",calc_dist(targetX,targetY,heroX,heroY))

def calc_dist(targetx,targety,herox,heroy):
        return math.sqrt((targetx-herox)**2+(targety-heroy)**2)
def parseStateDictValue(stateDict,key):
        if (stateDict[key]=="??"):
            return 0
        else:
            return float(stateDict[key].replace(",","."))

if __name__ == '__main__':
    main()
