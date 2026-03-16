#Groupe 15, François PETIT, Corentin RAFFRAY, 16 mars 2026

import mesa

class RobotAgent(mesa.Agent):
    "An Agent with fixed initial color"

    def __init__(self, model: 'RobotModel', color="green"): #on pourrait aussi ajouter un id pour différencier les agents
        super().__init__(model)
        self.color = color
    
    def move(self):
        possible_steps = self.model.grid.get_neighborhood(
            self.pos,
            moore=False, # False car seulement les 4 cases orthogonales sont accessibles
            include_center=False
        )
        new_position = self.random.choice(possible_steps)
        self.model.grid.move_agent(self, new_position)

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

        #Create Agents
        agents = [RobotAgent(self, color="green") for _ in range(n_green)]
        agents += [RobotAgent(self, color="yellow") for _ in range(n_yellow)]
        agents += [RobotAgent(self, color="red") for _ in range(n_red)]

        # Create x and y positions for agents
        x = self.rng.integers(0, self.grid.width, size=(n_green + n_yellow + n_red,))
        y = self.rng.integers(0, self.grid.height, size=(n_green + n_yellow + n_red,))
        for a, i, j in zip(agents, x, y):
            # Add the agent to a random grid cell
            self.grid.place_agent(a, (i, j))
    
    def step(self):
        print("Step ")



