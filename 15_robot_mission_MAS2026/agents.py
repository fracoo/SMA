#Groupe 15, François PETIT, Corentin RAFFRAY, 16 mars 2026

import mesa


class RobotAgent(mesa.Agent):
    """Classe de base pour tous les robots. Regroupe les comportements partagés."""

    def __init__(self, model, color):
        super().__init__(model)
        self.color = color

    def move(self):
        possible_steps = self.model.grid.get_neighborhood( # type: ignore
            self.pos,
            moore=False,  # False car seulement les 4 cases orthogonales sont accessibles
            include_center=False
        )
        # Evite les téléportations dues aux bords
        allowed_steps = []
        for step in possible_steps:
            if (
                not (self.pos[0] == 0 and step[0] == self.model.grid.width - 1)  # type: ignore
                and not (self.pos[0] == self.model.grid.width - 1 and step[0] == 0)  # type: ignore
                and not (self.pos[1] == 0 and step[1] == self.model.grid.height - 1)  # type: ignore
                and not (self.pos[1] == self.model.grid.height - 1 and step[1] == 0)  # type: ignore
            ):
                allowed_steps.append(step)

        new_position = self.random.choice(allowed_steps)
        self.model.grid.move_agent(self, new_position) # type: ignore

    def step(self):
        """Un pas de l'agent."""
        self.move()


class GreenAgent(RobotAgent):
    """Robot de la zone verte (z1). Collecte les déchets verts."""

    def __init__(self, model):
        super().__init__(model, color="green")

    def step(self):
        self.move()


class YellowAgent(RobotAgent):
    """Robot de la zone jaune (z2). Collecte les déchets jaunes."""

    def __init__(self, model):
        super().__init__(model, color="yellow")

    def step(self):
        self.move()


class RedAgent(RobotAgent):
    """Robot de la zone rouge (z3). Collecte les déchets rouges."""

    def __init__(self, model):
        super().__init__(model, color="red")

    def step(self):
        self.move()
