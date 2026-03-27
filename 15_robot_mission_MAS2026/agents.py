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
        self.slot1 : WasteAgent | None = slot1
        self.slot2 : WasteAgent | None = slot2
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
                cell = self.model.grid.get_cell_list_contents(step)  # type: ignore
                if not any(isinstance(a, RobotAgent) for a in cell):
                    allowed_steps.append(step)
        return allowed_steps

    def visualisation(self):
         # On regarde les cases accessibles pour voir si on des déchets y sont présents
        x, y = self.pos  # type: ignore
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
    
    def look_for_waste(self):
        cell_contents = self.model.grid.get_cell_list_contents(self.pos)
        wastes = []
        for agent in cell_contents:
            if isinstance(agent, WasteAgent):
                wastes.append(agent)
        return wastes

    def pick_waste(self):
        cell_contents = self.model.grid.get_cell_list_contents(self.pos)
        for agent in cell_contents:
            if isinstance(agent, WasteAgent):
                if self.slot1 is None:
                    self.slot1 = agent
                    self.model.grid.remove_agent(agent) 
                    break
                elif self.slot2 is None:
                    self.slot2 = agent
                    self.model.grid.remove_agent(agent) 
                    break
                else:
                    break
         
    
    def combine_waste(self):
        if self.slot1 and self.slot2:
            if self.slot1.waste_type == self.slot2.waste_type:
                if self.slot1.waste_type == "green":
                    self.slot1 = WasteAgent(self.model, "yellow")
                elif self.slot1.waste_type == "yellow":
                    self.slot1 = WasteAgent(self.model, "red")
                elif self.slot1.waste_type == "red":
                    pass
            self.slot2 = None

    def put_waste(self):
        cell_contents = self.model.grid.get_cell_list_contents(self.pos)
        has_waste_disposal_zone = any(isinstance(agent, WasteDisposalZone) for agent in cell_contents)
        if has_waste_disposal_zone:
            if self.slot1 and self.slot1.waste_type == "red":
                self.slot1 = None
        else:
            if self.slot1:
                self.model.grid.place_agent(self.slot1, self.pos)
                self.slot1 = None



class GreenAgent(RobotAgent):
    """Robot de la zone verte (z1). Collecte les déchets verts."""

    def __init__(self, model):
        super().__init__(model, color="green", slot1=None, slot2=None, map_knowledge={})
    
    def move(self):
        """
        Logique :
        1. Trouver les cases légales
        2. Se déplacer
        En fonction de l'état des slots, le déplacement n'est pas le même.
        """
        allowed_steps = self.allowed_steps()
        for step in allowed_steps:
            cell_contents = self.model.grid.get_cell_list_contents(step)
            for agent in cell_contents:
                if isinstance(agent, Radioactivity) and agent.zone != "z1":
                    allowed_steps.remove(step)
                    break
        
        if self.slot1 and self.slot1.waste_type =="yellow":
            # Si possession d'un déchet jaune, on se dirige vers la zone de dépôt (à l'est) pour les déposer
            east_cell = (self.pos[0] + 1, self.pos[1]) # type: ignore
            radioactivity_east_cell : str | None = None
            cell_contents = self.model.grid.get_cell_list_contents(east_cell)
            for agent in cell_contents:
                if isinstance(agent, Radioactivity):
                    radioactivity_east_cell = agent.zone
                    break
            if radioactivity_east_cell and radioactivity_east_cell == "z1":
                new_position = east_cell
            else:
                self.put_waste()
                new_position = self.pos
        else:
            new_position = self.random.choice(allowed_steps)
        
        self.model.grid.move_agent(self, new_position) # type: ignore

    def step(self):
        """
        Logique du tour :
        1. Visualisation de la carte pour mettre à jour les connaissances
        2.a. Si possible, Combinaison de deux déchets du même type pour en obtenir un de niveau supérieur
        2.b. Si possible, Ramassage d'un déchet s'il y en a un sur la case
        2.c. Sinon, déplacement vers une case accessible
        """
        self.visualisation()
        
        # Action
        if self.slot1 and self.slot2:
            if self.slot1.waste_type == self.slot2.waste_type:
                self.combine_waste()
            else:
                self.move()
        else:
            wastes_in_cell = self.look_for_waste()
            if wastes_in_cell != []:
                action = False
                for waste in wastes_in_cell:
                    if waste.waste_type == "green":
                        self.pick_waste()
                        action = True
                        break
                if not action:
                    self.move()
            else:
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
                if isinstance(agent, Radioactivity) and agent.zone == "z3":
                    allowed_steps.remove(step)
                    break

        new_position = self.random.choice(allowed_steps)
        self.model.grid.move_agent(self, new_position) # type: ignore
    
    def step(self):
        self.visualisation()
        self.move()


class RedAgent(RobotAgent):
    """Robot de la zone rouge (z3). Collecte les déchets rouges."""

    def __init__(self, model):
        super().__init__(model, color="red", slot1=None, slot2=None, map_knowledge={})
    
    def move(self):
        allowed_steps = self.allowed_steps()
        new_position = self.random.choice(allowed_steps)
        self.model.grid.move_agent(self, new_position) # type: ignore
    
    def step(self):
        self.visualisation()
        self.move()
