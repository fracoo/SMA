#Groupe 15, François PETIT, Corentin RAFFRAY, 16 mars 2026

from operator import ne

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
    
    def look_for_waste_in_current_cell(self):
        cell_contents = self.model.grid.get_cell_list_contents(self.pos)
        wastes = []
        for agent in cell_contents:
            if isinstance(agent, WasteAgent):
                wastes.append(agent)
        return wastes
    
    def look_for_waste_around(self):
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
        wastes = []
        for cell in view:
            cell_contents = self.model.grid.get_cell_list_contents(cell)
            for agent in cell_contents:
                if isinstance(agent, WasteAgent):
                    wastes.append(agent)
        return wastes


    def look_for_others(self):
        near_view = self.model.grid.get_neighborhood(
            self.pos,
            moore = False,
            include_center=False
        )
        others = []
        for cell in near_view :
            cell_content = self.model.grid.get_cell_list_contents(cell)
            for agent in cell_content:
                if isinstance(agent,RobotAgent) and agent.color == self.color:
                    others.append(agent)
        return others

    def pick_waste(self, waste: "WasteAgent"):
        if self.slot1 is None:
            self.slot1 = waste
            self.model.grid.remove_agent(waste)
        elif self.slot2 is None:
            self.slot2 = waste
            self.model.grid.remove_agent(waste)
         
    def combine_waste(self):
        if self.slot1 and self.slot2:
            if self.slot1.waste_type == self.slot2.waste_type:
                combined_count = self.slot1.original_count + self.slot2.original_count
                if self.slot1.waste_type == "green":
                    self.slot1 = WasteAgent(self.model, "yellow", original_count=combined_count)
                elif self.slot1.waste_type == "yellow":
                    self.slot1 = WasteAgent(self.model, "red", original_count=combined_count)
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

    def receive_waste_from_other(self, other: "RobotAgent"):
        """This function assume that self and other have exaclty one waste in their slots, and that the waste are of the same type."""
        self_empty_slot = "slot2" if self.slot1 else "slot1"
        other_waste_slot = "slot1" if other.slot1 else "slot2"

        #swap the waste between the two robots, situation 1/1 à 2/0
        setattr(self, self_empty_slot, getattr(other, other_waste_slot))
        setattr(other, other_waste_slot, None)

    def discard_waste(self):
        cell_contents = self.model.grid.get_cell_list_contents(self.pos)
        has_waste_disposal_zone = any(isinstance(agent, WasteDisposalZone) for agent in cell_contents)
        if has_waste_disposal_zone:
            if self.slot1:
                self.model.waste_disposed += self.slot1.original_count
                self.slot1 = None
            elif self.slot2:
                self.model.waste_disposed += self.slot2.original_count
                self.slot2 = None

    def move(self):
        raise NotImplementedError

    def step(self):
        """
        Logique :
        1. Visualisation (mise à jour de la connaissance de la carte)
            La visualisation n'est pas utile pour la v0 des robots qui ont un déplacement aléatoire.
        2.a. Si sur un slot de dépôt et possession d'un déchet, déposer le déchet.
        2.b. Sinon, si les deux slots sont pleins et contiennent des déchets du même type (hors rouge), les combiner
        2.c. Sinon, si un des deux slots est plein, et qu'il y a un robot voisin de la même couleur, essayer de donner le déchet
        2.d. Sinon, si il y a un déchet du même type dans la case, le ramasser
        2.e. Sinon, se déplacer
        """
        # self.visualisation()

        cell_contents = self.model.grid.get_cell_list_contents(self.pos)
        has_waste_disposal_zone = any(isinstance(agent, WasteDisposalZone) for agent in cell_contents)

        if has_waste_disposal_zone and (self.slot1 or self.slot2):
            self.discard_waste()

        elif self.slot1 and self.slot2:
            if self.slot1.waste_type == self.slot2.waste_type and self.slot1.waste_type != "red":
                self.combine_waste()
            else:
                self.move()
        else:
            action = False
            if self.slot1 or self.slot2:
                others = self.look_for_others()
                if others:
                    for other in others:
                        if bool(other.slot1) ^ bool(other.slot2):
                            self.receive_waste_from_other(other)
                            action = True
                            break

            wastes_in_cell = self.look_for_waste_in_current_cell()
            if wastes_in_cell != [] and not action:
                for waste in wastes_in_cell:
                    if waste.waste_type == self.color:
                        self.pick_waste(waste)
                        action = True
                        break
                if not action:
                    self.move()
            else:
                self.move()


class GreenAgent(RobotAgent):
    """Robot de la zone verte (z1). Collecte les déchets verts."""

    def __init__(self, model):
        super().__init__(model, color="green", slot1=None, slot2=None, map_knowledge={})

    def move(self):
        """
        Logique :
        1. Trouver les cases légales
        2. Se déplacer en fonction de la vision alentour du robot
        En fonction de l'état des slots, le déplacement n'est pas le même.
        """
        #trouver les cases légales
        allowed_steps = self.allowed_steps()
        for step in allowed_steps:
            cell_contents = self.model.grid.get_cell_list_contents(step)
            for agent in cell_contents:
                if isinstance(agent, Radioactivity) and agent.zone != "z1":
                    allowed_steps.remove(step)
                    break
        allowed_steps.append(self.pos) # on ajoute la possibilité de rester sur place, pour qu'il y ait toujours une action possible même si les cases autour sont inaccessibles

        wastes_around = self.look_for_waste_around()
        x, y = self.pos  # type: ignore

        # Pré-calcul de la case est et de sa zone (utilisé pour dépôt et libération)
        east_cell = (x + 1, y)
        east_contents = self.model.grid.get_cell_list_contents(east_cell)
        radioactivity_east_cell : str | None = None
        for agent in east_contents:
            if isinstance(agent, Radioactivity):
                radioactivity_east_cell = agent.zone
                break

        # deplacement
        if self.slot1 and self.slot1.waste_type =="yellow" or self.slot2 and self.slot2.waste_type =="yellow":
            # Si possession d'un déchet jaune, on se dirige vers la zone de dépôt (à l'est)
            if radioactivity_east_cell and radioactivity_east_cell == "z1":
                # La case est est encore en z1 : essayer de s'y déplacer
                has_robot_east = any(isinstance(a, RobotAgent) for a in east_contents)
                if not has_robot_east:
                    new_position = east_cell
                else:
                    # Case est occupée : essayer haut puis bas
                    new_position = self.pos
                    for cand in [(x, y + 1), (x, y - 1)]:
                        if 0 <= cand[1] < self.model.grid.height:  # type: ignore
                            cand_contents = self.model.grid.get_cell_list_contents(cand)
                            if not any(isinstance(a, RobotAgent) for a in cand_contents):
                                if any(isinstance(a, Radioactivity) and a.zone == "z1" for a in cand_contents):
                                    new_position = cand
                                    break
            else:
                # On est sur la case bord extrême Est de z1 : déposer le déchet
                # Garantit que le déchet jaune est en slot1 avant le dépôt
                # (peut être en slot2 si reçu via receive_waste_from_other)
                if self.slot2 and self.slot2.waste_type == "yellow":
                    self.slot1, self.slot2 = self.slot2, self.slot1
                self.put_waste()
                new_position = self.pos

        elif radioactivity_east_cell != "z1":
            # Libération de la case de dépôt : sur le bord est sans déchet jaune -> reculer à l'ouest pour libérer la placede dépôt
            west_cell = (x - 1, y)
            if west_cell in allowed_steps:
                new_position = west_cell
            else:
                new_position = self.random.choice(allowed_steps)

        elif wastes_around :
            new_position = None
            for waste in wastes_around:
                if waste.waste_type == "green":
                    if waste.pos in allowed_steps:
                        new_position = waste.pos
                        break
                    else:
                        x_waste, y_waste = waste.pos
                        candidates = []
                        # y en premier pour éviter de longer le bord est et déclencher la libération
                        if y_waste < y:
                            candidates.append((x, y-1))
                        elif y_waste > y:
                            candidates.append((x, y+1))

                        if x_waste < x:
                            candidates.append((x-1, y))
                        elif x_waste > x:
                            candidates.append((x+1, y))

                        for cand in candidates:
                            if cand in allowed_steps:
                                new_position = cand
                                break

                        if new_position is not None:
                            break

            if new_position is None:
                new_position = self.random.choice(allowed_steps)

        else:
            new_position = self.random.choice(allowed_steps)

        self.model.grid.move_agent(self, new_position) # type: ignore



class YellowAgent(RobotAgent):
    """Robot de la zone jaune (z2). Collecte les déchets jaunes."""

    def __init__(self, model):
        super().__init__(model, color="yellow", slot1=None, slot2=None, map_knowledge={})

    def move(self):
        """
        Logique :
        1. Trouver les cases légales
        2. Se déplacer en fonction de la vision alentour du robot
        En fonction de l'état des slots, le déplacement n'est pas le même.
        """
        #trouver les cases légales
        allowed_steps = self.allowed_steps()
        for step in allowed_steps:
            cell_contents = self.model.grid.get_cell_list_contents(step)
            for agent in cell_contents:
                if isinstance(agent, Radioactivity):
                    if agent.zone == "z3":
                        allowed_steps.remove(step)
                        break
                    elif agent.zone == "z1":
                        #remove only if there is no yellow waste in the cell
                        has_yellow_waste = any(isinstance(a, WasteAgent) and a.waste_type == "yellow" for a in cell_contents)
                        if not has_yellow_waste:
                            allowed_steps.remove(step)
                            break
        allowed_steps.append(self.pos) # on ajoute la possibilité de rester sur place, pour qu'il y ait toujours une action possible même si les cases autour sont inaccessibles

        wastes_around = self.look_for_waste_around()
        x, y = self.pos  # type: ignore

        # Pré-calcul de la case est et de sa zone (utilisé pour dépôt et libération)
        east_cell = (x + 1, y)
        east_contents = self.model.grid.get_cell_list_contents(east_cell)
        radioactivity_east_cell : str | None = None
        for agent in east_contents:
            if isinstance(agent, Radioactivity):
                radioactivity_east_cell = agent.zone
                break

        #deplacement
        if self.slot1 and self.slot1.waste_type =="red" or self.slot2 and self.slot2.waste_type =="red":
            # Si possession d'un déchet rouge, on se dirige vers la zone de dépôt (à l'est)
            if radioactivity_east_cell and radioactivity_east_cell in ["z1", "z2"]:
                # La case est est encore en z1/z2 : essayer de s'y déplacer
                has_robot_east = any(isinstance(a, RobotAgent) for a in east_contents)
                if not has_robot_east:
                    new_position = east_cell
                else:
                    # Case est occupée : essayer haut puis bas
                    new_position = self.pos
                    for cand in [(x, y + 1), (x, y - 1)]:
                        if 0 <= cand[1] < self.model.grid.height:  # type: ignore
                            cand_contents = self.model.grid.get_cell_list_contents(cand)
                            if not any(isinstance(a, RobotAgent) for a in cand_contents):
                                if any(isinstance(a, Radioactivity) and a.zone in ["z1", "z2"] for a in cand_contents):
                                    new_position = cand
                                    break
            else:
                # On est sur la case bord est de z2 : déposer le déchet
                # Garantit que le déchet rouge est en slot1 avant le dépôt
                # (peut être en slot2 si reçu via receive_waste_from_other)
                if self.slot2 and self.slot2.waste_type == "red":
                    self.slot1, self.slot2 = self.slot2, self.slot1
                self.put_waste()
                new_position = self.pos

        elif radioactivity_east_cell not in ["z1", "z2"]:
            # Libération de la case de dépôt : sur le bord est sans déchet rouge -> reculer à l'ouest pour libérer la place de dépôt
            west_cell = (x - 1, y)
            if west_cell in allowed_steps:
                new_position = west_cell
            else:
                new_position = self.random.choice(allowed_steps)

        elif wastes_around :
            new_position = None
            for waste in wastes_around:
                if waste.waste_type == "yellow":
                    if waste.pos in allowed_steps:
                        new_position = waste.pos
                        break
                    else:
                        x_waste, y_waste = waste.pos
                        candidates = []
                        # y en premier pour éviter de longer le bord est et déclencher la libération
                        if y_waste < y:
                            candidates.append((x, y-1))
                        elif y_waste > y:
                            candidates.append((x, y+1))

                        if x_waste < x:
                            candidates.append((x-1, y))
                        elif x_waste > x:
                            candidates.append((x+1, y))

                        for cand in candidates:
                            if cand in allowed_steps:
                                new_position = cand
                                break

                        if new_position is not None:
                            break

            if new_position is None:
                new_position = self.random.choice(allowed_steps)

        else:
            new_position = self.random.choice(allowed_steps)

        self.model.grid.move_agent(self, new_position) # type: ignore


class RedAgent(RobotAgent):
    """Robot de la zone rouge (z3). Collecte les déchets rouges."""

    def __init__(self, model):
        super().__init__(model, color="red", slot1=None, slot2=None, map_knowledge={})

    def move(self):
        """
        Logique :
        1. Trouver les cases légales
        2. Se déplacer en fonction de la vision alentour du robot
        En fonction de l'état des slots, le déplacement n'est pas le même.
        """
        #trouver les cases légales
        allowed_steps = self.allowed_steps()
        for step in allowed_steps:
            cell_contents = self.model.grid.get_cell_list_contents(step)
            for agent in cell_contents:
                if isinstance(agent, Radioactivity) and agent.zone != "z3":
                    # remove only if there is no red waste in the cell
                    has_red_waste = any(isinstance(a, WasteAgent) and a.waste_type == "red" for a in cell_contents)
                    if not has_red_waste:
                        allowed_steps.remove(step)
                        break
        allowed_steps.append(self.pos) # on ajoute la possibilité de rester sur place, pour qu'il y ait toujours une action possible même si les cases autour sont inaccessibles

        wastes_around = self.look_for_waste_around()
        x, y = self.pos  # type: ignore

        #deplacement
        if (self.slot1 and self.slot1.waste_type =="red") or (self.slot2 and self.slot2.waste_type =="red"):
            # Si possession d'un déchet rouge, on se dirige vers la zone de disposal (sud est)
            east_x = x + 1
            south_y = y - 1
            north_y = y + 1
            if y == 0 and east_x < self.model.grid.width:  # type: ignore
                # Sur la ligne la plus au sud hors disposal : remonter d'abord vers le nord
                if north_y < self.model.grid.height:  # type: ignore
                    north_contents = self.model.grid.get_cell_list_contents((x, north_y))
                    has_robot_north = any(isinstance(a, RobotAgent) for a in north_contents)
                    new_position = self.pos if has_robot_north else (x, north_y)
                else:
                    new_position = self.pos
            elif east_x < self.model.grid.width:  # type: ignore
                # Essayer d'aller à l'est
                east_contents = self.model.grid.get_cell_list_contents((east_x, y))
                has_robot_east = any(isinstance(a, RobotAgent) for a in east_contents)
                if not has_robot_east:
                    new_position = (east_x, y)
                else:
                    # Case est occupée : essayer le sud (jamais la ligne la plus au sud hors disposal,
                    # pour éviter de bloquer le couloir d'accès à la zone de dépôt)
                    if south_y > 0:
                        south_contents = self.model.grid.get_cell_list_contents((x, south_y))
                        has_robot_south = any(isinstance(a, RobotAgent) for a in south_contents)
                        new_position = self.pos if has_robot_south else (x, south_y)
                    else:
                        new_position = self.pos
            else:
                # À l'extrême est : essayer le sud
                if south_y >= 0:
                    south_contents = self.model.grid.get_cell_list_contents((x, south_y))
                    has_robot_south = any(isinstance(a, RobotAgent) for a in south_contents)
                    new_position = self.pos if has_robot_south else (x, south_y)
                else:
                    # Déjà sur la waste disposal zone, ne pas bouger
                    new_position = self.pos

        elif not (self.slot1 or self.slot2):
            # Libération de la zone de dépôt : si le dépôt est sur la case courante, à l'est ou deux cases à l'est -> reculer à l'ouest pour libérer la zone de dépot
            disposal_nearby = False
            for dx in range(3):
                cx = x + dx
                if 0 <= cx < self.model.grid.width:  # type: ignore
                    cell = self.model.grid.get_cell_list_contents((cx, y))
                    if any(isinstance(a, WasteDisposalZone) for a in cell):
                        disposal_nearby = True
                        break

            if disposal_nearby:
                west_cell = (x - 1, y)
                if west_cell in allowed_steps:
                    new_position = west_cell
                else:
                    new_position = self.pos
            elif wastes_around:
                new_position = None
                for waste in wastes_around:
                    if waste.waste_type == "red":
                        if waste.pos in allowed_steps:
                            new_position = waste.pos
                            break
                        else:
                            x_waste, y_waste = waste.pos
                            candidates = []
                            if x_waste < x:
                                candidates.append((x-1, y))
                            elif x_waste > x:
                                candidates.append((x+1, y))

                            if y_waste < y:
                                candidates.append((x, y-1))
                            elif y_waste > y:
                                candidates.append((x, y+1))

                            for cand in candidates:
                                if cand in allowed_steps:
                                    new_position = cand
                                    break

                            if new_position is not None:
                                break

                if new_position is None:
                    new_position = self.random.choice(allowed_steps)
            else:
                new_position = self.random.choice(allowed_steps)

        elif wastes_around :
            new_position = None
            for waste in wastes_around:
                if waste.waste_type == "red":
                    if waste.pos in allowed_steps:
                        new_position = waste.pos
                        break
                    else:
                        x_waste, y_waste = waste.pos
                        candidates = []
                        if x_waste < x:
                            candidates.append((x-1, y))
                        elif x_waste > x:
                            candidates.append((x+1, y))

                        if y_waste < y:
                            candidates.append((x, y-1))
                        elif y_waste > y:
                            candidates.append((x, y+1))

                        for cand in candidates:
                            if cand in allowed_steps:
                                new_position = cand
                                break

                        if new_position is not None:
                            break

            if new_position is None:
                new_position = self.random.choice(allowed_steps)

        else:
            new_position = self.random.choice(allowed_steps)

        self.model.grid.move_agent(self, new_position) # type: ignore
