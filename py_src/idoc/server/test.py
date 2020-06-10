class Car:
    def __init__(self, speed=5):
        self._speed = speed
        self.velocity = speed

    @property
    def speed(self):
        return self._speed

import ipdb; ipdb.set_trace()
