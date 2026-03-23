#Groupe 15, François PETIT, Corentin RAFFRAY, 16 mars 2026

import mesa
import numpy as np
from objects import Radioactivity, WasteDisposalZone, WasteAgent

from communication.agent.CommunicatingAgent import CommunicatingAgent
from communication.mailbox.Mailbox import Mailbox
from communication.message.Message import Message
from communication.message.MessagePerformative import MessagePerformative
from communication.message.MessageService import MessageService



class RobotAgent(CommunicatingAgent):
    """Classe de base pour tous les robots. Regroupe les comportements partagés."""

    def __init__(self, model, color, slot1, slot2, map_knowledge):
        if not hasattr(model, "_robot_sid_counter"):
            model._robot_sid_counter = 0
        id = f"Robot_{color}_{model._robot_sid_counter}"
        model._robot_sid_counter += 1

        super().__init__(model, name=id)
        self.color = color
        self.slot1 = slot1
        self.slot2 = slot2
        self.map_knowledge = map_knowledge
        self.sent_to: dict[str, set] = {}  # neighbor_name -> set of cells already sent


    def allowed_steps(self):
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

        return allowed_steps

    def visualisation(self):
         # On regarde les cases accessibles pour voir si on des déchets y sont présents
        x, y = self.pos
        width = self.model.grid.width
        height = self.model.grid.height

        near_view = self.model.grid.get_neighborhood(
            self.pos,
            moore = True,
            include_center=False
        )

        near_view = [
            (nx, ny)
            for nx, ny in near_view
            if abs(nx - x) <= 1 and abs(ny - y) <= 1
        ]

        far_view =[(x+2, y), (x-2, y), (x, y+2), (x, y-2)]
        
        far_view = [
            (nx, ny)
            for nx, ny in far_view
            if 0 <= nx < width and 0 <= ny < height
        ]

        view = list(set(near_view + far_view))

        for cell in view : 
            contenu_cell = self.model.grid.get_cell_list_contents([cell])
            has_waste_in_cell = False
            neighbor_robot: RobotAgent | None = None
            for agent in contenu_cell:
                if isinstance(agent, WasteAgent):
                    has_waste_in_cell = True
                    self.map_knowledge[agent.pos] = agent
                elif isinstance(agent, RobotAgent) and agent != self:
                    neighbor_robot = agent
            if not has_waste_in_cell and cell in self.map_knowledge:
                del self.map_knowledge[cell]
            
            # envoyer uniquement les nouvelles cellules au voisin (évite les messages redondants)
            if neighbor_robot:
                neighbor_name = neighbor_robot.get_name()
                already_sent = self.sent_to.get(neighbor_name, set())
                new_cells = {k: v for k, v in self.map_knowledge.items() if k not in already_sent}
                if new_cells:
                    message = Message(
                        from_agent=self.get_name(),
                        to_agent=neighbor_name,
                        message_performative=MessagePerformative.INFORM_REF,
                        content=new_cells
                    )
                    self.send_message(message)
                    self.sent_to[neighbor_name] = already_sent | set(new_cells.keys())

        # recevoir la connaissance de la carte des robots voisins, pour mettre à jour la connaissance de la carte sauf pour les cellules que le robot courant peut voir
        new_messages = self.get_new_messages()
        for message in new_messages:
            if message.get_performative() == MessagePerformative.INFORM_REF:
                sender_map_knowledge = message.get_content()
                for cell, waste in sender_map_knowledge.items():
                    if cell not in view:  # Ne pas mettre à jour la connaissance pour les cellules que le robot peut voir
                        self.map_knowledge[cell] = waste


class GreenAgent(RobotAgent):
    """Robot de la zone verte (z1). Collecte les déchets verts."""

    def __init__(self, model):
        super().__init__(model, color="green", slot1=None, slot2=None, map_knowledge={})
    
    def move(self):
        allowed_steps = self.allowed_steps()
        for step in allowed_steps:
            cell_contents = self.model.grid.get_cell_list_contents(step)
            for agent in cell_contents:
                if (isinstance(agent, Radioactivity) and agent.zone != "z1") or isinstance(agent, WasteAgent):
                    allowed_steps.remove(step)
                    break
                
        new_position = self.random.choice(allowed_steps)
        self.model.grid.move_agent(self, new_position) # type: ignore

    def step(self):
        self.move()


class YellowAgent(RobotAgent):
    """Robot de la zone jaune (z2). Collecte les déchets jaunes."""

    def __init__(self, model):
        super().__init__(model, color="yellow", slot1=None, slot2=None, map_knowledge={})
    
    def move(self):
        allowed_steps = self.allowed_steps()
        for step in allowed_steps:
            cell_contents = self.model.grid.get_cell_list_contents(step)
            for agent in cell_contents:
                if (isinstance(agent, Radioactivity) and agent.zone == "z3") or isinstance(agent, WasteAgent):
                    allowed_steps.remove(step)
                    break
                
        new_position = self.random.choice(allowed_steps)
        self.model.grid.move_agent(self, new_position) # type: ignore
    
    def step(self):
        self.move()


class RedAgent(RobotAgent):
    """Robot de la zone rouge (z3). Collecte les déchets rouges."""

    def __init__(self, model):
        super().__init__(model, color="red", slot1=None, slot2=None, map_knowledge={})
    
    def move(self): 
        allowed_steps = self.allowed_steps()
        for step in allowed_steps:
            cell_contents = self.model.grid.get_cell_list_contents(step)
            for agent in cell_contents:
                if isinstance(agent, WasteAgent):
                    allowed_steps.remove(step)
                    break
                
        new_position = self.random.choice(allowed_steps)
        self.model.grid.move_agent(self, new_position) # type: ignore
    
    def step(self):
        self.move()
