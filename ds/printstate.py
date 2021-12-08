#!/usr/bin/env python
from gameState import dsgym

      
        
import yaml

def main():
    with open("bossconfigs/Iudex.yaml", "r") as ymlfile:
            boss_config = yaml.safe_load(ymlfile)
            print(boss_config["location"]["boss_area"])    

if __name__ == '__main__':
    main()
