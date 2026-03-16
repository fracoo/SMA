#Groupe 15, François PETIT, Corentin RAFFRAY, 16 mars 2026

import mesa
from objects import Radioactivity, WasteAgent, WasteDisposalZone
import random

class RobotAgent(mesa.Agent):
    "An Agent with fixed initial color"

    def __init__(self, model: 'RobotModel', color="green"): #on pourrait aussi ajouter un id pour différencier les agents
        super().__init__(model)
        self.color = color
    
    def move(self):
        possible_steps = self.model.grid.get_neighborhood( # type: ignore
            self.pos,
            moore=False, # False car seulement les 4 cases orthogonales sont accessibles
            include_center=False
        )
        #check that neighborhood is not jumping over the grid limits
        allowed_steps = []
        for step in possible_steps:
            if not (self.pos[0] == 0 and step[0] == self.model.grid.width - 1) and not (self.pos[0] == self.model.grid.width - 1 and step[0] == 0) and not (self.pos[1] == 0 and step[1] == self.model.grid.height - 1) and not (self.pos[1] == self.model.grid.height - 1 and step[1] == 0): # type: ignore
                allowed_steps.append(step)
        
        new_position = self.random.choice(allowed_steps)
        self.model.grid.move_agent(self, new_position) # type: ignore

    def step(self):
        """One step of the agent."""
        self.move()




class RobotModel(mesa.Model):
    def __init__(self, n_green, n_yellow, n_red, height, width, seed=107):
        """
        Create a new RobotModel.
        
        Args:
            n_green: Number of green agents in the simulation
            n_yellow: Number of yellow agents in the simulation
            n_red: Number of red agents in the simulation
            height, width: Size of the grid
        """
        super().__init__(seed=seed)
        self.n_green = n_green
        self.n_yellow = n_yellow
        self.n_red = n_red
        self.grid: mesa.space.MultiGrid = mesa.space.MultiGrid(width, height, True)

        #Create Robot Agents
        agents = [RobotAgent(self, color="green") for _ in range(n_green)]
        agents += [RobotAgent(self, color="yellow") for _ in range(n_yellow)]
        agents += [RobotAgent(self, color="red") for _ in range(n_red)]

        # Create x and y positions for agents
        x = self.rng.integers(0, self.grid.width, size=(n_green + n_yellow + n_red,))
        y = self.rng.integers(0, self.grid.height, size=(n_green + n_yellow + n_red,))
        for a, i, j in zip(agents, x, y):
            # Add the agent to a random grid cell
            self.grid.place_agent(a, (i, j))

        #Create Radioactivity Agents (width is always divisible by 3, so we can easily split the grid into 3 zones)
        for i in range(self.grid.width): 
            for j in range(self.grid.height): 
                if i <= self.grid.width / 3: 
                    zone = "z1"
                elif i <= 2 * self.grid.width / 3: 
                    zone = "z2"
                else:
                    zone = "z3"
                radioactivity_agent = Radioactivity(self, zone)
                self.grid.place_agent(radioactivity_agent, (i, j))
        
        #Create Waste Disposal Zone Agents (one for the whole grid)
        waste_disposal_zone_agent = WasteDisposalZone(self)
        self.grid.place_agent(waste_disposal_zone_agent, waste_disposal_zone_agent.position)

        #Create wastes object
        num_cases = self.grid.width * self.grid.height
        num_wastes = random.randint(1, num_cases//10)
        for i in range (num_wastes):
            x = self.random.randrange(self.grid.width)
            y = self.random.randrange(self.grid.height)
            pos_waste = (x, y)
            contenu_case = self.grid.get_cell_list_contents([pos_waste])
            radioactivity_agent = None
            for agent in contenu_case:
                if isinstance(agent, Radioactivity):
                    radioactivity_agent = agent
                    break
            if radioactivity_agent.radioactivity_level < 0.34:
                waste_type = "green"
            elif radioactivity_agent.radioactivity_level < 0.68:
                waste_type = "yellow"
            else :
                waste_type = "red"
            waste_obj = WasteAgent(self, waste_type)
            self.grid.place_agent(waste_obj, pos_waste)

            


    
    def step(self):
        """Advance the model by one step."""
        self.agents.shuffle_do("step")



