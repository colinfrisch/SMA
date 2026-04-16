# Group 28 - Robot Mission MAS 2026
# Created: 2026-04-13
# Members: Colin Frisch
"""Definition of robot agent classes with decision logic"""

from mesa import Agent
from abc import abstractmethod

from objects import Waste


def _direction_toward(from_pos, to_pos):
    """Return a cardinal direction string from from_pos toward to_pos."""
    dx = to_pos[0] - from_pos[0]
    dy = to_pos[1] - from_pos[1]
    if abs(dx) >= abs(dy):
        return "east" if dx > 0 else "west"
    return "north" if dy > 0 else "south"


class RobotAgent(Agent):
    """
    Abstract base class for all robot agents.

    The agent loop follows the PDF specification:
      1. percepts  ->  update knowledge
      2. deliberate(knowledge)  ->  action
      3. model.do(agent, action)  ->  new percepts
    """

    allowed_zones: tuple = (1, 2, 3)

    def __init__(self, model):
        super().__init__(model)
        self.knowledge: dict = {
            "pos": None,
            "carried_waste": [],
            "percepts": {},
            "known_targets": {"yellow": [], "red": []},
        }

    def step(self):
        # 1. Observe environment (percepts)
        neighborhood = self.model.grid.get_neighborhood(
            self.pos, moore=False, include_center=True
        )
        percepts = {
            pos: self.model.grid.get_cell_list_contents([pos])
            for pos in neighborhood
        }
        # 2. Update knowledge
        self.knowledge["pos"] = self.pos
        self.knowledge["percepts"] = percepts
        self.knowledge["z1_max"] = self.model.z1_max
        self.knowledge["z2_max"] = self.model.z2_max
        self.knowledge["waste_disposal_pos"] = self.model.waste_disposal_pos
        self.knowledge["random_dir"] = self.random.choice(
            ["north", "south", "east", "west"]
        )
        # 3. Deliberate -> action
        action = self.deliberate(self.knowledge)
        # 4. Model executes action and returns new percepts
        new_percepts = self.model.do(self, action)
        self.knowledge["percepts"] = new_percepts

    @abstractmethod
    def _do_transform(self):
        raise NotImplementedError

    @abstractmethod
    def deliberate(self, knowledge: dict) -> dict:
        raise NotImplementedError


# --------------- Green Robot ----------------
class GreenAgent(RobotAgent):
    """
    Green robot, restricted to zone z1.
    Collects 2 green wastes -> transforms into 1 yellow -> transports east.
    """

    allowed_zones = (1,)

    def _do_transform(self):
        carried = self.knowledge["carried_waste"]
        greens = [w for w in carried if w.waste_type == "green"]
        if len(greens) >= 2:
            for w in greens[:2]:
                carried.remove(w)
                w.remove()
            carried.append(Waste(self.model, "yellow"))

    def deliberate(self, knowledge: dict) -> dict:
        carried = knowledge.get("carried_waste", [])
        pos = knowledge.get("pos")
        percepts = knowledge.get("percepts", {})

        green_carried = [w for w in carried if w.waste_type == "green"]
        yellow_carried = [w for w in carried if w.waste_type == "yellow"]

        if len(green_carried) >= 2:
            return {"type": "transform"}

        if yellow_carried:
            x, _ = pos
            if x < knowledge["z1_max"] - 1:
                return {"type": "move", "direction": "east"}
            return {
                "type": "put_down",
                "waste": yellow_carried[0],
                "message": {"msg_type": "yellow_waste_at", "recipient": "yellow"},
            }

        for obj in percepts.get(pos, []):
            if hasattr(obj, "waste_type") and obj.waste_type == "green":
                return {"type": "pick_up", "waste": obj}

        for cell_pos, contents in percepts.items():
            if cell_pos == pos:
                continue
            for obj in contents:
                if hasattr(obj, "waste_type") and obj.waste_type == "green":
                    return {"type": "move", "direction": _direction_toward(pos, cell_pos)}

        return {"type": "move", "direction": knowledge["random_dir"]}


# ------------------- Yellow Robot ----------------
class YellowAgent(RobotAgent):
    """
    Yellow robot, can move in zones z1 and z2.
    Collects 2 yellow wastes -> transforms into 1 red -> transports east.
    """

    allowed_zones = (1, 2)

    def _do_transform(self):
        carried = self.knowledge["carried_waste"]
        yellows = [w for w in carried if w.waste_type == "yellow"]
        if len(yellows) >= 2:
            for w in yellows[:2]:
                carried.remove(w)
                w.remove()
            carried.append(Waste(self.model, "red"))

    def deliberate(self, knowledge: dict) -> dict:
        carried = knowledge.get("carried_waste", [])
        pos = knowledge.get("pos")
        percepts = knowledge.get("percepts", {})
        known_targets = knowledge.get("known_targets", {})

        yellow_carried = [w for w in carried if w.waste_type == "yellow"]
        red_carried = [w for w in carried if w.waste_type == "red"]

        if len(yellow_carried) >= 2:
            return {"type": "transform"}

        if red_carried:
            x, _ = pos
            if x < knowledge["z2_max"] - 1:
                return {"type": "move", "direction": "east"}
            return {
                "type": "put_down",
                "waste": red_carried[0],
                "message": {"msg_type": "red_waste_at", "recipient": "red"},
            }

        for obj in percepts.get(pos, []):
            if hasattr(obj, "waste_type") and obj.waste_type == "yellow":
                return {"type": "pick_up", "waste": obj}

        for cell_pos, contents in percepts.items():
            if cell_pos == pos:
                continue
            for obj in contents:
                if hasattr(obj, "waste_type") and obj.waste_type == "yellow":
                    return {"type": "move", "direction": _direction_toward(pos, cell_pos)}

        known_yellow = known_targets.get("yellow", [])
        if known_yellow:
            return {"type": "move", "direction": _direction_toward(pos, known_yellow[0])}

        return {"type": "move", "direction": knowledge["random_dir"]}


# -------------------- Red Robot ----------------
class RedAgent(RobotAgent):
    """
    Red robot, can move across all zones z1, z2, z3.
    Collects 1 red waste -> transports to waste disposal zone.
    """

    allowed_zones = (1, 2, 3)

    def _do_transform(self):
        pass

    def deliberate(self, knowledge: dict) -> dict:
        carried = knowledge.get("carried_waste", [])
        pos = knowledge.get("pos")
        percepts = knowledge.get("percepts", {})
        known_targets = knowledge.get("known_targets", {})

        red_carried = [w for w in carried if w.waste_type == "red"]

        if red_carried:
            disposal_pos = knowledge["waste_disposal_pos"]
            if pos == disposal_pos:
                return {"type": "put_down", "waste": red_carried[0]}
            return {"type": "move", "direction": _direction_toward(pos, disposal_pos)}

        for obj in percepts.get(pos, []):
            if hasattr(obj, "waste_type") and obj.waste_type == "red":
                return {
                    "type": "pick_up",
                    "waste": obj,
                    "message": {"msg_type": "claim_target", "recipient": "red"},
                }

        for cell_pos, contents in percepts.items():
            if cell_pos == pos:
                continue
            for obj in contents:
                if hasattr(obj, "waste_type") and obj.waste_type == "red":
                    return {"type": "move", "direction": _direction_toward(pos, cell_pos)}

        known_red = known_targets.get("red", [])
        if known_red:
            return {"type": "move", "direction": _direction_toward(pos, known_red[0])}

        return {"type": "move", "direction": knowledge["random_dir"]}
