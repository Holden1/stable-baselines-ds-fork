import math
import time
from gameState import dsgym

env= dsgym()
while(True):
    time.sleep(0.1)
    env.print_state_dict(env.readState())
    print("Dist:",env.calc_dist(env.readState()))