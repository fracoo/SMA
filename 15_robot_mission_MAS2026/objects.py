#Groupe 15, François PETIT, Corentin RAFFRAY, 16 mars 2026

import mesa
from model import RobotModel
import random

class Radioactivity(mesa.Agent):
    def __init__(self, model, zone):
        super().__init__(model)
        self.zone = zone
        
        if self.zone == "z1" or self.zone == "green":
            self.radioactivity_level = random.uniform(0, 0.33)
        elif self.zone == "z2" or self.zone == "yellow":
            self.radioactivity_level = random.uniform(0.34, 0.66)
        elif self.zone == "z3" or self.zone == "red":
            self.radioactivity_level = random.uniform(0.67, 1.0)
        else:
            self.radioactivity_level = 0

class WasteDisposalZone(mesa.Agent):
    def __init__(self, model):
        super()



