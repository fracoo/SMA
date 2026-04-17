#Groupe 15, François PETIT, Corentin RAFFRAY, 16 mars 2026

import mesa
import random
import numpy as np
from objects import Radioactivity, WasteDisposalZone, WasteAgent
from agents import RobotAgent, GreenAgent, YellowAgent, RedAgent
from communication.message.MessageService import MessageService


class RobotModel(mesa.Model):
    def __init__(self, n_green, n_yellow, n_red, n_waste, height, width, seed=107):
        """
        Create a new RobotModel.

        Args:
            n_green: Number of green agents in the simulation
            n_yellow: Number of yellow agents in the simulation
            n_red: Number of red agents in the simulation
            n_waste: Number of waste agents in the simulation
            height, width: Size of the grid
        """
        super().__init__(rng=int(seed))
        self.n_green = n_green
        self.n_yellow = n_yellow
        self.n_red = n_red
        self.n_waste = n_waste
        # n_waste is the number of red waste units; proportions are 4:2:1 (green:yellow:red)
        # weighted units: green=1, yellow=2, red=4
        # total = 4*n_waste*1 + 2*n_waste*2 + 1*n_waste*4 = 12*n_waste
        self.total_initial_waste = 12 * n_waste
        self.waste_disposed = 0
        self._prev_waste_disposed = 0
        self._throughput = 0
        self.visit_counts = np.zeros((height, width))
        self.grid: mesa.space.MultiGrid = mesa.space.MultiGrid(width, height, True)
        self.message_log: list[str] = []

        # Reset and initialize the MessageService singleton before creating agents
        MessageService._MessageService__instance = None # type: ignore
        self.message_service = MessageService(self, instant_delivery=True)

        #Create Robot Agents

        #Green
        green_agents = [GreenAgent(self) for _ in range(n_green)]
        # Add the agent to a random (distinct on y) grid cell
        y = self.rng.choice(self.grid.height, size=n_green, replace=False).tolist() # type: ignore
        for a, j in zip(green_agents, y):
            self.grid.place_agent(a, (0, j))
    
        #Yellow
        yellow_agents = [YellowAgent(self) for _ in range(n_yellow)]
        # Add the agent to a random (distinct on y) grid cell
        y = self.rng.choice(self.grid.height, size=n_yellow, replace=False).tolist() # type: ignore
        for a, j in zip(yellow_agents, y):
            self.grid.place_agent(a, (self.grid.width//3, j))

        #Red
        red_agents = [RedAgent(self) for _ in range(n_red)]
        # Add the agent to a random (distinct on y) grid cell
        y = self.rng.choice(self.grid.height, size=n_red, replace=False).tolist() # type: ignore
        for a, j in zip(red_agents, y):
            self.grid.place_agent(a, (2*self.grid.width//3, j))


        #Create Radioactivity Agents (width is always divisible by 3, so we can easily split the grid into 3 zones)
        for i in range(self.grid.width): 
            for j in range(self.grid.height): 
                if i <= self.grid.width // 3 - 1: 
                    zone = "z1"
                elif i <= 2 * self.grid.width // 3 - 1: 
                    zone = "z2"
                else:
                    zone = "z3"
                radioactivity_agent = Radioactivity(self, zone)
                self.grid.place_agent(radioactivity_agent, (i, j))
        
        #Create Waste Disposal Zone Agents (one for the whole grid)
        waste_disposal_zone_agent = WasteDisposalZone(self)
        self.grid.place_agent(waste_disposal_zone_agent, waste_disposal_zone_agent.position)

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "fraction_disposed": lambda m: m.waste_disposed / m.total_initial_waste if m.total_initial_waste > 0 else 0,
                "waste_disposed": lambda m: m.waste_disposed,
                "waste_on_grid": lambda m: sum(1 for a in m.agents if isinstance(a, WasteAgent) and a.pos is not None),
                "waste_held": lambda m: sum(
                    (a.slot1.original_count if a.slot1 else 0) + (a.slot2.original_count if a.slot2 else 0)
                    for a in m.agents if hasattr(a, "slot1")
                ),
                "throughput": lambda m: m._throughput,
                "avg_utilization": lambda m: (
                    sum(a.useful_steps / a.total_steps for a in m.agents if isinstance(a, RobotAgent) and a.total_steps > 0)
                    / max(1, sum(1 for a in m.agents if isinstance(a, RobotAgent) and a.total_steps > 0))
                ),
            }
        )

        # Create waste objects: 4*n_waste green (z1), 2*n_waste yellow (z2), n_waste red (z3)
        # Proportions 4:2:1 guarantee full cleanup: 4 green -> 2 yellow -> 1 red -> disposed
        z1_x = range(0, self.grid.width // 3)
        z2_x = range(self.grid.width // 3, 2 * self.grid.width // 3)
        z3_x = range(2 * self.grid.width // 3, self.grid.width)

        for waste_type, zone_x, count in [
            ("green",  z1_x, 4 * n_waste),
            ("yellow", z2_x, 2 * n_waste),
            ("red",    z3_x, 1 * n_waste),
        ]:
            placed = 0
            while placed < count:
                x = self.random.choice(list(zone_x))
                y = self.random.randrange(self.grid.height)
                pos_waste = (x, y)
                if not any(isinstance(a, (WasteAgent, GreenAgent, YellowAgent, RedAgent)) for a in self.grid.get_cell_list_contents([pos_waste])):
                    waste_obj = WasteAgent(self, waste_type)
                    self.grid.place_agent(waste_obj, pos_waste)
                    placed += 1

            


    
    def step(self):
        """Advance the model by one step."""
        self.agents.shuffle_do("step")
        self._throughput = self.waste_disposed - self._prev_waste_disposed
        self._prev_waste_disposed = self.waste_disposed
        for a in self.agents:
            if isinstance(a, RobotAgent) and a.pos is not None:
                x, y = a.pos
                self.visit_counts[y][x] += 1
        self.datacollector.collect(self)



