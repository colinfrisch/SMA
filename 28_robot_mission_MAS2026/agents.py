"""Definition of robot agent classes with decision logic"""

from mesa import Agent
from abc import abstractmethod


class RobotAgent(Agent):
    """
    Abstract base class for all robot agents.

    Each concrete subclass must implement:
      percepts()  -> dict  : observe the environment via self.model
      deliberate(knowledge) -> action dict : decide next action from knowledge

    The agent loop is:
      percepts  ->  update knowledge  ->  deliberate  ->  action   
    """

    # Subclasses override this to declare which zones they may enter (1-indexed).
    allowed_zones: tuple = (1, 2, 3)

    def __init__(self, model):
        super().__init__(model)
        # knowledge is the agent's private belief state
        self.knowledge: dict = {
            "pos": None,
            "carried_waste": [], # list of waste objects currently held
            "percepts": {}, # last percepts snapshot
            "known_targets": {"yellow": [], "red": []}, # positions of waste from messages
        }


    # ===================Core agent loop==================

    def step_agent(self):
        """
        Implements:
            update(self.knowledge, percepts)
            action = deliberate(self.knowledge)
            percepts = self.model.do(self, action)
        """
        percepts = self.percepts()
        self.knowledge["pos"] = self.pos
        self.knowledge["percepts"] = percepts
        action = self.deliberate(self.knowledge)
        new_percepts = self.model.do(self, action)
        if new_percepts:
            self.knowledge["percepts"] = new_percepts

    def step(self):
        self.step_agent()

    # Methods implemented in subclasses
    @staticmethod
    def _direction_toward(from_pos, to_pos):
        """Return a cardinal direction string from "from_pos" toward "to_pos" (e.g. "north", "south", "east", "west")"""
        dx = to_pos[0] - from_pos[0]
        dy = to_pos[1] - from_pos[1]
        if abs(dx) >= abs(dy):
            return "east" if dx > 0 else "west"
        return "north" if dy > 0 else "south"

    @abstractmethod
    def percepts(self) -> dict:
        """
        Observe adjacent tiles and their contents.
        Returns a dict {pos: [agent_descriptions, ...], ...}.
        Should NOT contain any decision logic.
        """
        raise NotImplementedError

    @abstractmethod
    def deliberate(self, knowledge: dict) -> dict:
        """
        Decide the next action based solely on `knowledge`.
        Should NOT access any variable outside its argument.

        Possible actions (dict with a "type" key):
          {"type": "move",      "direction": "north"|"south"|"east"|"west"}
          {"type": "pick_up",   "waste": <Waste object>}
          {"type": "transform"}
          {"type": "put_down",  "waste": <Waste object>}
          {"type": "wait"}
        """
        raise NotImplementedError


#---------------Green Robot----------------
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

    def __init__(self, model):
        super().__init__(model)

    def percepts(self) -> dict:
        """Read the contents of all adjacent cells (Von Neumann neighbourhood)."""
        neighborhood = self.model.grid.get_neighborhood(
            self.pos, moore=False, include_center=True
        )
        percepts = {}
        for pos in neighborhood:
            contents = self.model.grid.get_cell_list_contents([pos])
            percepts[pos] = contents
        return percepts

    def deliberate(self, knowledge: dict) -> dict:
        carried = knowledge.get("carried_waste", [])
        pos = knowledge.get("pos")
        percepts = knowledge.get("percepts", {})

        green_carried = [w for w in carried if w.waste_type == "green"]
        yellow_carried = [w for w in carried if w.waste_type == "yellow"]

        # Two greens: transform
        if len(green_carried) >= 2:
            return {"type": "transform"}

        # Carrying yellow (after transform): deliver east toward z1 border
        if yellow_carried:
            x, y = pos
            if x < self.model.z1_max - 1:
                return {"type": "move", "direction": "east"}
            # Broadcast message when dropping yellow waste
            action = {"type": "put_down", "waste": yellow_carried[0]}
            self.model.broadcast_message(self, "yellow_waste_at", pos, YellowAgent)
            return action

        # Try to pick up green waste on current cell
        for obj in percepts.get(pos, []):
            if hasattr(obj, "waste_type") and obj.waste_type == "green":
                return {"type": "pick_up", "waste": obj}

        # Move toward green waste visible on an adjacent cell
        for cell_pos, contents in percepts.items():
            if cell_pos == pos:
                continue
            for obj in contents:
                if hasattr(obj, "waste_type") and obj.waste_type == "green":
                    return {"type": "move", "direction": self._direction_toward(pos, cell_pos)}

        # Random walk
        return {"type": "move", "direction": self.random.choice(["north", "south", "east", "west"])}


# -------------------Yellow Robot----------------
class YellowAgent(RobotAgent):
    """
    Yellow robot, can move in zones z1 and z2.

    Behaviour:
      1. Collect up to 2 yellow wastes (may also pick up yellow waste left by
         green robots at the z1/z2 border).
      2. Once carrying 2 yellow wastes -> transform into 1 red waste.
      3. Transport red waste (or a single yellow waste) further east toward z3.
      4. At the z2 boundary, put the red waste down for a red robot.
    """

    allowed_zones = (1, 2)

    def __init__(self, model):
        super().__init__(model)

    def percepts(self) -> dict:
        neighborhood = self.model.grid.get_neighborhood(
            self.pos, moore=False, include_center=True
        )
        percepts = {}
        for pos in neighborhood:
            contents = self.model.grid.get_cell_list_contents([pos])
            percepts[pos] = contents
        return percepts

    def deliberate(self, knowledge: dict) -> dict:
        carried = knowledge.get("carried_waste", [])
        pos = knowledge.get("pos")
        percepts = knowledge.get("percepts", {})
        known_targets = knowledge.get("known_targets", {})

        yellow_carried = [w for w in carried if w.waste_type == "yellow"]
        red_carried = [w for w in carried if w.waste_type == "red"]

        # Two yellows: transform
        if len(yellow_carried) >= 2:
            return {"type": "transform"}

        # Carrying red (result of transform): deliver east toward z2 border
        if red_carried:
            x, y = pos
            if x < self.model.z2_max - 1:
                return {"type": "move", "direction": "east"}
            # Broadcast message when dropping red waste
            action = {"type": "put_down", "waste": red_carried[0]}
            self.model.broadcast_message(self, "red_waste_at", pos, RedAgent)
            return action

        # Try to pick up yellow waste on current cell
        for obj in percepts.get(pos, []):
            if hasattr(obj, "waste_type") and obj.waste_type == "yellow":
                return {"type": "pick_up", "waste": obj}

        # Move toward yellow waste visible on an adjacent cell
        for cell_pos, contents in percepts.items():
            if cell_pos == pos:
                continue
            for obj in contents:
                if hasattr(obj, "waste_type") and obj.waste_type == "yellow":
                    return {"type": "move", "direction": self._direction_toward(pos, cell_pos)}

        # Move toward known yellow waste from messages
        known_yellow = known_targets.get("yellow", [])
        if known_yellow:
            target = known_yellow[0]
            return {"type": "move", "direction": self._direction_toward(pos, target)}

        # Random walk
        return {"type": "move", "direction": self.random.choice(["north", "south", "east", "west"])}


# --------------------Red Robot----------------
class RedAgent(RobotAgent):
    """
    Red robot – can move across all zones z1, z2, z3.

    Behaviour:
      1. Collect 1 red waste.
      2. Carry it east until the waste disposal zone is reached.
      3. Put it down on the waste disposal zone (waste is "put away").
    """

    allowed_zones = (1, 2, 3)

    def __init__(self, model):
        super().__init__(model)

    def percepts(self) -> dict:
        neighborhood = self.model.grid.get_neighborhood(
            self.pos, moore=False, include_center=True
        )
        percepts = {}
        for pos in neighborhood:
            contents = self.model.grid.get_cell_list_contents([pos])
            percepts[pos] = contents
        return percepts

    def deliberate(self, knowledge: dict) -> dict:
        carried = knowledge.get("carried_waste", [])
        pos = knowledge.get("pos")
        percepts = knowledge.get("percepts", {})
        known_targets = knowledge.get("known_targets", {})

        red_carried = [w for w in carried if w.waste_type == "red"]

        # Carrying red waste: navigate to disposal and put down
        if red_carried:
            disposal_pos = self.model.waste_disposal_pos
            if pos == disposal_pos:
                return {"type": "put_down", "waste": red_carried[0]}
            return {"type": "move", "direction": self._direction_toward(pos, disposal_pos)}

        # Try to pick up red waste on current cell
        for obj in percepts.get(pos, []):
            if hasattr(obj, "waste_type") and obj.waste_type == "red":
                # Send REQUEST message to claim target
                self.model.broadcast_message(self, "claim_target", pos, RedAgent)
                return {"type": "pick_up", "waste": obj}

        # Move toward red waste visible on an adjacent cell
        for cell_pos, contents in percepts.items():
            if cell_pos == pos:
                continue
            for obj in contents:
                if hasattr(obj, "waste_type") and obj.waste_type == "red":
                    return {"type": "move", "direction": self._direction_toward(pos, cell_pos)}

        # Move toward known red waste from messages
        known_red = known_targets.get("red", [])
        if known_red:
            target = known_red[0]
            return {"type": "move", "direction": self._direction_toward(pos, target)}

        # Random walk
        return {"type": "move", "direction": self.random.choice(["north", "south", "east", "west"])}
