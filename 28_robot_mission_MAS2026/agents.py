"""Definition of robot agent classes with decision logic"""

from mesa import Agent
from abc import abstractmethod

from objects import Waste


class RobotAgent(Agent):
    """
    Abstract base class for all robot agents.

    Each concrete subclass must implement:
      percepts()         -> dict : observe the environment via self.model.grid
      deliberate(knowledge) -> action dict : decide next action from knowledge
      _do_transform()        : agent-specific waste fusion logic

    The agent loop is:
      percepts  ->  update knowledge  ->  deliberate  ->  execute
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

    # =================== Core agent loop ===================

    def step(self):
        percepts = self.percepts()
        self.knowledge["pos"] = self.pos
        self.knowledge["percepts"] = percepts
        action = self.deliberate(self.knowledge)
        self._execute(action)
        self.knowledge["percepts"] = self.percepts()

    # =================== Action execution ===================

    def _execute(self, action: dict):
        if action is None or action.get("type") == "wait":
            return
        action_type = action.get("type")
        if action_type == "move":
            self._do_move(action["direction"])
        elif action_type == "pick_up":
            self._do_pick_up(action["waste"])
        elif action_type == "transform":
            self._do_transform()
        elif action_type == "put_down":
            self._do_put_down(action["waste"])

    def _do_move(self, direction: str):
        x, y = self.pos
        moves = {
            "north": (x, y + 1),
            "south": (x, y - 1),
            "east":  (x + 1, y),
            "west":  (x - 1, y),
        }
        new_pos = moves.get(direction)
        if new_pos and self._is_move_feasible(new_pos):
            self.model.grid.move_agent(self, new_pos)

    def _do_pick_up(self, waste):
        cell_contents = self.model.grid.get_cell_list_contents([self.pos])
        if waste in cell_contents and isinstance(waste, Waste):
            self.model.grid.remove_agent(waste)
            self.knowledge["carried_waste"].append(waste)

    @abstractmethod
    def _do_transform(self):
        raise NotImplementedError

    def _do_put_down(self, waste):
        carried = self.knowledge["carried_waste"]
        if waste in carried:
            carried.remove(waste)
            if self.pos == self.model.waste_disposal_pos:
                waste.remove()
                self.model.waste_disposed_count += 1
            else:
                self.model.grid.place_agent(waste, self.pos)

    def _is_move_feasible(self, new_pos: tuple) -> bool:
        """Check grid bounds and zone access rights."""
        x, y = new_pos
        if x < 0 or x >= self.model.width or y < 0 or y >= self.model.height:
            return False
        if x < self.model.z1_max:
            zone = 1
        elif x < self.model.z2_max:
            zone = 2
        else:
            zone = 3
        return zone in self.allowed_zones

    @staticmethod
    def _direction_toward(from_pos, to_pos):
        """Return a cardinal direction string from from_pos toward to_pos."""
        dx = to_pos[0] - from_pos[0]
        dy = to_pos[1] - from_pos[1]
        if abs(dx) >= abs(dy):
            return "east" if dx > 0 else "west"
        return "north" if dy > 0 else "south"

    @abstractmethod
    def percepts(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def deliberate(self, knowledge: dict) -> dict:
        raise NotImplementedError


# --------------- Green Robot ----------------
class GreenAgent(RobotAgent):
    """
    Green robot, entirely restricted to zone z1.

    Behaviour:
      1. Wander z1 collecting green waste (picking up up to 2).
      2. Once carrying 2 green wastes -> transform into 1 yellow waste.
      3. Transport the yellow waste as far east as possible (z1 boundary),
         then put it down for a yellow robot to collect.
    """

    allowed_zones = (1,)

    def percepts(self) -> dict:
        neighborhood = self.model.grid.get_neighborhood(
            self.pos, moore=False, include_center=True
        )
        return {
            pos: self.model.grid.get_cell_list_contents([pos])
            for pos in neighborhood
        }

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
            x, y = pos
            if x < self.model.z1_max - 1:
                return {"type": "move", "direction": "east"}
            action = {"type": "put_down", "waste": yellow_carried[0]}
            self.model.broadcast_message(self, "yellow_waste_at", pos, YellowAgent)
            return action

        for obj in percepts.get(pos, []):
            if hasattr(obj, "waste_type") and obj.waste_type == "green":
                return {"type": "pick_up", "waste": obj}

        for cell_pos, contents in percepts.items():
            if cell_pos == pos:
                continue
            for obj in contents:
                if hasattr(obj, "waste_type") and obj.waste_type == "green":
                    return {"type": "move", "direction": self._direction_toward(pos, cell_pos)}

        return {"type": "move", "direction": self.random.choice(["north", "south", "east", "west"])}


# ------------------- Yellow Robot ----------------
class YellowAgent(RobotAgent):
    """
    Yellow robot, can move in zones z1 and z2.

    Behaviour:
      1. Collect up to 2 yellow wastes.
      2. Once carrying 2 yellow wastes -> transform into 1 red waste.
      3. Transport red waste east toward the z2 boundary.
      4. At the z2 boundary, put the red waste down for a red robot.
    """

    allowed_zones = (1, 2)

    def percepts(self) -> dict:
        neighborhood = self.model.grid.get_neighborhood(
            self.pos, moore=False, include_center=True
        )
        return {
            pos: self.model.grid.get_cell_list_contents([pos])
            for pos in neighborhood
        }

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
            x, y = pos
            if x < self.model.z2_max - 1:
                return {"type": "move", "direction": "east"}
            action = {"type": "put_down", "waste": red_carried[0]}
            self.model.broadcast_message(self, "red_waste_at", pos, RedAgent)
            return action

        for obj in percepts.get(pos, []):
            if hasattr(obj, "waste_type") and obj.waste_type == "yellow":
                return {"type": "pick_up", "waste": obj}

        for cell_pos, contents in percepts.items():
            if cell_pos == pos:
                continue
            for obj in contents:
                if hasattr(obj, "waste_type") and obj.waste_type == "yellow":
                    return {"type": "move", "direction": self._direction_toward(pos, cell_pos)}

        known_yellow = known_targets.get("yellow", [])
        if known_yellow:
            return {"type": "move", "direction": self._direction_toward(pos, known_yellow[0])}

        return {"type": "move", "direction": self.random.choice(["north", "south", "east", "west"])}


# -------------------- Red Robot ----------------
class RedAgent(RobotAgent):
    """
    Red robot – can move across all zones z1, z2, z3.

    Behaviour:
      1. Collect 1 red waste.
      2. Carry it east until the waste disposal zone is reached.
      3. Put it down on the waste disposal zone.
    """

    allowed_zones = (1, 2, 3)

    def percepts(self) -> dict:
        neighborhood = self.model.grid.get_neighborhood(
            self.pos, moore=False, include_center=True
        )
        return {
            pos: self.model.grid.get_cell_list_contents([pos])
            for pos in neighborhood
        }

    def _do_transform(self):
        pass

    def deliberate(self, knowledge: dict) -> dict:
        carried = knowledge.get("carried_waste", [])
        pos = knowledge.get("pos")
        percepts = knowledge.get("percepts", {})
        known_targets = knowledge.get("known_targets", {})

        red_carried = [w for w in carried if w.waste_type == "red"]

        if red_carried:
            disposal_pos = self.model.waste_disposal_pos
            if pos == disposal_pos:
                return {"type": "put_down", "waste": red_carried[0]}
            return {"type": "move", "direction": self._direction_toward(pos, disposal_pos)}

        for obj in percepts.get(pos, []):
            if hasattr(obj, "waste_type") and obj.waste_type == "red":
                self.model.broadcast_message(self, "claim_target", pos, RedAgent)
                return {"type": "pick_up", "waste": obj}

        for cell_pos, contents in percepts.items():
            if cell_pos == pos:
                continue
            for obj in contents:
                if hasattr(obj, "waste_type") and obj.waste_type == "red":
                    return {"type": "move", "direction": self._direction_toward(pos, cell_pos)}

        known_red = known_targets.get("red", [])
        if known_red:
            return {"type": "move", "direction": self._direction_toward(pos, known_red[0])}

        return {"type": "move", "direction": self.random.choice(["north", "south", "east", "west"])}
