import math
import time
from collections import deque

prev_char_animations = deque([],maxlen=1)
prev_char_animations.append(1)
prev_char_animations.append(2)
prev_char_animations.append(3)
print("Dist:",prev_char_animations[-1])