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
        self.total_steps = 0
        self.useful_steps = 0
        self.target_cell: tuple | None = None
        self.idle_with_waste_steps: int = 0


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

    def _compute_view(self):
        x, y = self.pos  # type: ignore
        width = self.model.grid.width
        height = self.model.grid.height
        near_view = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)  # type: ignore
        near_view = [(nx, ny) for nx, ny in near_view if abs(nx - x) <= 1 and abs(ny - y) <= 1]
        far_view = [(x+2, y), (x-2, y), (x, y+2), (x, y-2)]
        far_view = [(nx, ny) for nx, ny in far_view if 0 <= nx < width and 0 <= ny < height]
        return list(set(near_view + far_view))

    def visualisation(self):
        view = self._compute_view()
        for cell in view:
            contenu_cell = self.model.grid.get_cell_list_contents([cell])
            has_own_waste = False
            for agent in contenu_cell:
                if isinstance(agent, WasteAgent) and agent.waste_type == self.color:
                    has_own_waste = True
                    self.map_knowledge[agent.pos] = agent
            if not has_own_waste and cell in self.map_knowledge:
                del self.map_knowledge[cell]

    def communicate(self):
        """Partage map_knowledge avec les robots voisins de même couleur. Actuellement inactive."""
        view = self._compute_view()
        for cell in view:
            contenu_cell = self.model.grid.get_cell_list_contents([cell])
            for agent in contenu_cell:
                if isinstance(agent, RobotAgent) and agent != self and agent.color == self.color:
                    neighbor_name = agent.get_name()
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
        new_messages = self.get_new_messages()
        for message in new_messages:
            if message.get_performative() == MessagePerformative.INFORM_REF:
                sender_map_knowledge = message.get_content()
                for cell, waste in sender_map_knowledge.items():
                    if cell not in view:
                        self.map_knowledge[cell] = waste

    def _step_toward(self, target_pos, allowed_steps):
        """Retourne le pas dans allowed_steps qui se rapproche le plus de target_pos."""
        x, y = self.pos  # type: ignore
        tx, ty = target_pos
        candidates = []
        if tx > x: candidates.append((x+1, y))
        elif tx < x: candidates.append((x-1, y))
        if ty > y: candidates.append((x, y+1))
        elif ty < y: candidates.append((x, y-1))
        for cand in candidates:
            if cand in allowed_steps:
                return cand
        return self._weighted_random_step(allowed_steps)

    def _move_toward_nearest_in_memory(self, allowed_steps):
        """Se dirige vers le déchet le plus proche connu en mémoire (distance Manhattan)."""
        if not self.map_knowledge:
            return self._weighted_random_step(allowed_steps)
        x, y = self.pos  # type: ignore
        nearest_pos = min(self.map_knowledge.keys(), key=lambda p: abs(p[0]-x) + abs(p[1]-y))
        return self._step_toward(nearest_pos, allowed_steps)

    def _pick_target_in_zone(self) -> tuple:
        """Choisit une case aléatoire dans la zone du robot, en excluant le bord est (green/yellow) et la WasteDisposalZone (red)."""
        width = self.model.grid.width  # type: ignore
        height = self.model.grid.height  # type: ignore
        if self.color == "green":
            x = self.random.randrange(0, width // 3 - 1)
            y = self.random.randrange(0, height)
            return (x, y)
        elif self.color == "yellow":
            x = self.random.randrange(width // 3, 2 * width // 3 - 1)
            y = self.random.randrange(0, height)
            return (x, y)
        else:  # red — exclude y=0 row entirely (disposal zone sits there, triggers disposal_nearby loop)
            x = self.random.randrange(2 * width // 3, width)
            y = self.random.randrange(1, height)
            return (x, y)
    
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


    def look_for_others(self, extended = False):
        near_view = self.model.grid.get_neighborhood(
            self.pos,
            moore = False if not extended else True,
            include_center=False
        )

        others = []
        for cell in near_view :
            cell_content = self.model.grid.get_cell_list_contents(cell)
            for agent in cell_content:
                if isinstance(agent,RobotAgent) and agent.color == self.color:
                    others.append(agent)
        if extended:
            #ajouter les voisins à 2 cases orthogonales de distance s'il y en a
            x, y = self.pos #type: ignore
            far_view = [(x+2, y), (x-2, y), (x, y+2), (x, y-2)]

            far_view = [
            (nx, ny)
            for nx, ny in far_view
            if 0 <= nx < self.model.grid.width and 0 <= ny < self.model.grid.height
            ]

            for cell in far_view:
                cell_content = self.model.grid.get_cell_list_contents(cell)
                for agent in cell_content:
                    if isinstance(agent,RobotAgent) and agent.color == self.color:
                        others.append(agent)

        return others

    def pick_waste(self, waste: "WasteAgent"):
        pos = waste.pos
        if self.slot1 is None:
            self.slot1 = waste
            self.model.grid.remove_agent(waste)
            if pos in self.map_knowledge:
                del self.map_knowledge[pos]
        elif self.slot2 is None:
            self.slot2 = waste
            self.model.grid.remove_agent(waste)
            if pos in self.map_knowledge:
                del self.map_knowledge[pos]
         
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

    def _weighted_random_step(self, candidates):
        if len(candidates) == 1:
            return candidates[0]
        counts = [self.model.visit_counts[y][x] for x, y in candidates]
        total = sum(counts)
        if total == 0:
            return self.random.choice(candidates)
        weights = [total - c for c in counts]
        if sum(weights) == 0:
            return self.random.choice(candidates)
        return self.random.choices(candidates, weights=weights, k=1)[0]

    def _partner_search_move(self, allowed_steps):
        """Move east preferentially, never west. Used when idle_with_waste_steps in [100, 200)."""
        x = self.pos[0]  # type: ignore
        non_west = [s for s in allowed_steps if s[0] >= x]
        if not non_west:
            return self.pos
        east = [s for s in non_west if s[0] > x]
        if east:
            return east[0]
        # At east border of zone: random up/down
        vertical = [s for s in non_west if s != self.pos]
        if vertical:
            return self._weighted_random_step(vertical)
        return self.pos

    def move(self):
        raise NotImplementedError

    def step(self):
        """
        Logique :
        1. Visualisation (mise à jour de la connaissance de la carte)
        2. Communication (partage de la connaissance de la carte avec les voisins).
        3.a. Si sur un slot de dépôt et possession d'un déchet, déposer le déchet.
        3.b. Sinon, si les deux slots sont pleins et contiennent des déchets du même type (hors rouge), les combiner
        3.c. Sinon, si un des deux slots est plein, et qu'il y a un robot voisin de la même couleur, essayer de donner le déchet
        3.d. Sinon, si il y a un déchet du même type dans la case, le ramasser
        3.e. Sinon, si un des slots est plein et qu'il y a un robot voisin de la même couleur à proximité (non directe), s'en rapprocher.
        3.f. Sinon, se déplacer aléatoirement parmi les cases accessibles
        """
        self.visualisation()
        self.communicate()

        self.total_steps += 1
        was_useful = False

        cell_contents = self.model.grid.get_cell_list_contents(self.pos)
        has_waste_disposal_zone = any(isinstance(agent, WasteDisposalZone) for agent in cell_contents)

        if has_waste_disposal_zone and (self.slot1 or self.slot2):
            self.discard_waste()
            was_useful = True
            if not (self.slot1 or self.slot2) and self.target_cell is None:
                self.target_cell = self._pick_target_in_zone()

        elif self.slot1 and self.slot2:
            if self.slot1.waste_type == self.slot2.waste_type and self.slot1.waste_type == self.color and self.color != "red":
                self.combine_waste()
                was_useful = True
            else:
                self.move()
        else:
            action = False
            if self.slot1 or self.slot2:
                others = self.look_for_others()
                if others:
                    for other in others:
                        if bool(other.slot1) ^ bool(other.slot2):
                            other_waste = other.slot1 or other.slot2
                            my_waste = self.slot1 or self.slot2
                            # Ne recevoir que si le type correspond
                            if my_waste and other_waste and my_waste.waste_type == other_waste.waste_type and my_waste.waste_type == self.color:
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
            
            elif (self.slot1 or self.slot2) and not action:
                others_extended = self.look_for_others(extended = True)
                if others_extended:
                    for other in others_extended:
                        if bool(other.slot1) ^ bool(other.slot2):
                            my_waste = self.slot1 or self.slot2
                            other_waste = other.slot1 or other.slot2
                            if my_waste and other_waste and my_waste.waste_type == other_waste.waste_type and my_waste.waste_type == self.color:
                                # S'approcher du robot voisin pour pouvoir lui donner le déchet au tour suivant
                                x, y = self.pos  # type: ignore
                                other_x, other_y = other.pos
                                dx = other_x - x
                                dy = other_y - y
                                if abs(dx) > abs(dy):
                                    step = (x + np.sign(dx), y)
                                else:
                                    step = (x, y + np.sign(dy))
                                if step in self.allowed_steps():
                                    self.model.grid.move_agent(self, step) # type: ignore
                                    action = True
                                    break
                
                if not action:
                    self.move()
            else:
                self.move()

            if action:
                was_useful = True

        if was_useful:
            self.useful_steps += 1


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
        if (self.slot1 and self.slot1.waste_type =="yellow") or (self.slot2 and self.slot2.waste_type =="yellow"):
            self.idle_with_waste_steps = 0
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
                if not (self.slot1 or self.slot2) and self.target_cell is None:
                    self.target_cell = self._pick_target_in_zone()
                new_position = self.pos

        elif any(w.waste_type == "green" for w in wastes_around):
            self.idle_with_waste_steps = 0
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
                new_position = self._weighted_random_step(allowed_steps)

        elif self.map_knowledge:
            self.idle_with_waste_steps = 0
            new_position = self._move_toward_nearest_in_memory(allowed_steps)

        elif radioactivity_east_cell != "z1" and not (self.slot1 or self.slot2):
            self.idle_with_waste_steps = 0
            # Libération de la case de dépôt : sur le bord est, slots vides, rien à faire -> reculer à l'ouest
            west_cell = (x - 1, y)
            if west_cell in allowed_steps:
                new_position = west_cell
            else:
                new_position = self._weighted_random_step(allowed_steps)

        elif self.target_cell:
            self.idle_with_waste_steps = 0
            if self.pos == self.target_cell:
                self.target_cell = None
                new_position = self._weighted_random_step(allowed_steps)
            else:
                new_position = self._step_toward(self.target_cell, allowed_steps)

        else:
            holding_one_waste = bool(self.slot1) ^ bool(self.slot2)
            others_extended = self.look_for_others(extended=True)
            partner_has_waste = any(o.slot1 is not None or o.slot2 is not None for o in others_extended)
            if partner_has_waste or not holding_one_waste:
                self.idle_with_waste_steps = 0
            else:
                self.idle_with_waste_steps += 1

            if 100 <= self.idle_with_waste_steps < 200:
                new_position = self._partner_search_move(allowed_steps)
            else:
                new_position = self._weighted_random_step(allowed_steps)

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
        if (self.slot1 and self.slot1.waste_type =="red") or (self.slot2 and self.slot2.waste_type =="red"):
            self.idle_with_waste_steps = 0
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
                if not (self.slot1 or self.slot2) and self.target_cell is None:
                    self.target_cell = self._pick_target_in_zone()
                new_position = self.pos

        elif any(w.waste_type == "yellow" for w in wastes_around):
            self.idle_with_waste_steps = 0
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
                new_position = self._weighted_random_step(allowed_steps)

        elif self.map_knowledge:
            self.idle_with_waste_steps = 0
            new_position = self._move_toward_nearest_in_memory(allowed_steps)

        elif radioactivity_east_cell not in ["z1", "z2"] and not (self.slot1 or self.slot2):
            self.idle_with_waste_steps = 0
            # Libération de la case de dépôt : slots vides, rien à faire -> reculer à l'ouest
            west_cell = (x - 1, y)
            if west_cell in allowed_steps:
                new_position = west_cell
            else:
                new_position = self._weighted_random_step(allowed_steps)

        elif self.target_cell:
            self.idle_with_waste_steps = 0
            if self.pos == self.target_cell:
                self.target_cell = None
                new_position = self._weighted_random_step(allowed_steps)
            else:
                new_position = self._step_toward(self.target_cell, allowed_steps)

        else:
            holding_one_waste = bool(self.slot1) ^ bool(self.slot2)
            others_extended = self.look_for_others(extended=True)
            partner_has_waste = any(o.slot1 is not None or o.slot2 is not None for o in others_extended)
            if partner_has_waste or not holding_one_waste:
                self.idle_with_waste_steps = 0
            else:
                self.idle_with_waste_steps += 1

            if 100 <= self.idle_with_waste_steps < 200:
                new_position = self._partner_search_move(allowed_steps)
            else:
                new_position = self._weighted_random_step(allowed_steps)

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
            # Si slot libre et déchet rouge visible directement, le ramassage est prioritaire sur le dépôt
            has_free_slot = not (self.slot1 and self.slot2)
            red_wastes_in_vision = [w for w in wastes_around if w.waste_type == "red"]
            if has_free_slot and red_wastes_in_vision:
                nearest = min(red_wastes_in_vision, key=lambda w: abs(w.pos[0]-x) + abs(w.pos[1]-y))
                new_position = self._step_toward(nearest.pos, allowed_steps)
            else:
                # Sinon, se diriger vers la zone de disposal (sud est)
                east_x = x + 1
                south_y = y - 1
                north_y = y + 1
                if y == 0 and east_x < self.model.grid.width:  # type: ignore
                    if north_y < self.model.grid.height:  # type: ignore
                        north_contents = self.model.grid.get_cell_list_contents((x, north_y))
                        has_robot_north = any(isinstance(a, RobotAgent) for a in north_contents)
                        new_position = self.pos if has_robot_north else (x, north_y)
                    else:
                        new_position = self.pos
                elif east_x < self.model.grid.width:  # type: ignore
                    east_contents = self.model.grid.get_cell_list_contents((east_x, y))
                    has_robot_east = any(isinstance(a, RobotAgent) for a in east_contents)
                    if not has_robot_east:
                        new_position = (east_x, y)
                    else:
                        if south_y > 0:
                            south_contents = self.model.grid.get_cell_list_contents((x, south_y))
                            has_robot_south = any(isinstance(a, RobotAgent) for a in south_contents)
                            new_position = self.pos if has_robot_south else (x, south_y)
                        else:
                            new_position = self.pos
                else:
                    if south_y >= 0:
                        south_contents = self.model.grid.get_cell_list_contents((x, south_y))
                        has_robot_south = any(isinstance(a, RobotAgent) for a in south_contents)
                        new_position = self.pos if has_robot_south else (x, south_y)
                    else:
                        new_position = self.pos

        elif not (self.slot1 or self.slot2):
            disposal_nearby = False
            for dx in range(3):
                cx = x + dx
                if 0 <= cx < self.model.grid.width:  # type: ignore
                    cell = self.model.grid.get_cell_list_contents((cx, y))
                    if any(isinstance(a, WasteDisposalZone) for a in cell):
                        disposal_nearby = True
                        break

            if any(w.waste_type == "red" for w in wastes_around):
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
                    new_position = self._move_toward_nearest_in_memory(allowed_steps)
            elif self.map_knowledge:
                new_position = self._move_toward_nearest_in_memory(allowed_steps)
            elif disposal_nearby:
                # Libération de la zone de dépôt : rien à faire, reculer à l'ouest pour libérer la zone
                west_cell = (x - 1, y)
                north_cell = (x, y + 1)
                if west_cell in allowed_steps:
                    new_position = west_cell
                elif north_cell in allowed_steps:
                    new_position = north_cell
                else:
                    new_position = self.pos
            elif self.target_cell:
                if self.pos == self.target_cell:
                    self.target_cell = None
                    new_position = self._weighted_random_step(allowed_steps)
                else:
                    tx, _ = self.target_cell
                    # At y=0 with an eastern target: go north first to stay off the disposal_nearby row
                    if y == 0 and tx > x:
                        north = (x, y + 1)
                        new_position = north if north in allowed_steps else self.pos
                    else:
                        new_position = self._step_toward(self.target_cell, allowed_steps)
            else:
                new_position = self._weighted_random_step(allowed_steps)

        elif any(w.waste_type == "red" for w in wastes_around):
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
                new_position = self._move_toward_nearest_in_memory(allowed_steps)

        elif self.map_knowledge:
            new_position = self._move_toward_nearest_in_memory(allowed_steps)

        else:
            new_position = self._weighted_random_step(allowed_steps)

        self.model.grid.move_agent(self, new_position) # type: ignore
