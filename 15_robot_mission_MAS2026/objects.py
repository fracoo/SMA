#Groupe 15, François PETIT, Corentin RAFFRAY, 16 mars 2026

from re import M

import mesa
import random

class Radioactivity(mesa.Agent):
    def __init__(self, model, zone):
        super().__init__(model)
        self.zone = zone
        
        if self.zone == "z1":
            self.radioactivity_level = random.uniform(0, 0.33)
        elif self.zone == "z2" :
            self.radioactivity_level = random.uniform(0.34, 0.66)
        elif self.zone == "z3" :
            self.radioactivity_level = random.uniform(0.67, 1.0)
        else:
            self.radioactivity_level = 0

class WasteDisposalZone(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        height = model.grid.height
        pos_waste_disposal = random.randint(0, height-1)
        self.position = (model.grid.width-1, pos_waste_disposal)

class WasteAgent(mesa.Agent):
    def __init__(self, model, waste_type):
        super().__init__(model)
        self.waste_type = waste_type
        position = (random.randint(0, model.grid.width-1), random.randint(0, model.grid.height-1))
        # tant qu'il n'y a pas deja un déchet à cet emplacement, on en génère un nouveau
        while WasteAgent in model.grid.get_cell_list_contents(position):
            position = (random.randint(0, model.grid.width-1), random.randint(0, model.grid.height-1))
        self.position = position

