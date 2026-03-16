# Group: robot_mission_MAS2026
# Date: 2026-03-16
# Members: Colin Friesh, Marie LUDUC , Hammale Mourad 

import random
import mesa
from objects import RadioactivityAgent, WasteDisposalZone, WasteAgent


# ---------------------------------------------------------------------------
# Action constants
# ---------------------------------------------------------------------------

MOVE       = "move"
PICK_UP    = "pick_up"
TRANSFORM  = "transform"
PUT_DOWN   = "put_down"
DEPOSIT    = "deposit"
WAIT       = "wait"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_zone_from_percepts(percepts: dict) -> int:
    """
    Read the radioactivity level of the current cell from percepts
    and return the zone number (1, 2 or 3).
    """
    current = percepts.get("current", {})
    for obj in current.get("contents", []):
        if isinstance(obj, RadioactivityAgent):
            r = obj.radioactivity
            if r < 0.33:
                return 1
            elif r < 0.66:
                return 2
            else:
                return 3
    return 1


def _find_waste_in_percepts(percepts: dict, color: str):
    """
    Return the position of the first waste of the given color found
    in adjacent cells, or None if none is visible.
    """
    for pos, cell_info in percepts.items():
        if pos == "current":
            continue
        for obj in cell_info.get("contents", []):
            if isinstance(obj, WasteAgent) and obj.color == color:
                return pos
    return None


def _find_disposal_in_percepts(percepts: dict):
    """Return the position of the WasteDisposalZone if visible."""
    for pos, cell_info in percepts.items():
        if pos == "current":
            continue
        for obj in cell_info.get("contents", []):
            if isinstance(obj, WasteDisposalZone):
                return pos
    return None


def _move_toward(current_pos, target_pos, percepts: dict, zone_limit: int):
    """
    Return a MOVE action toward target_pos, staying within zone_limit.
    Falls back to a random valid move if direct path is blocked.
    """
    cx, cy = current_pos
    tx, ty = target_pos
    dx = 0 if tx == cx else (1 if tx > cx else -1)
    dy = 0 if ty == cy else (1 if ty > cy else -1)

    candidates = []
    if dx != 0:
        candidates.append((cx + dx, cy))
    if dy != 0:
        candidates.append((cx, cy + dy))

    # filter by zone limit and walkable
    valid = []
    for pos in candidates:
        cell = percepts.get(pos, {})
        if cell.get("walkable", False):
            valid.append(pos)

    if valid:
        return {"type": MOVE, "target": valid[0]}

    # random fallback among all adjacent walkable cells
    all_adj = [
        pos for pos, info in percepts.items()
        if pos != "current" and info.get("walkable", False)
    ]
    if all_adj:
        return {"type": MOVE, "target": random.choice(all_adj)}

    return {"type": WAIT}


# ---------------------------------------------------------------------------
# Base robot class
# ---------------------------------------------------------------------------

class RobotAgent(mesa.Agent):
    """
    Abstract base for all robot types.
    Subclasses define their zone limit, carried waste logic, and strategy.
    """

    zone_limit: int = 3          # maximum zone the robot can enter
    robot_color: str = "base"

    def __init__(self, model):
        super().__init__(model)
        self.knowledge = {
            "pos": None,
            "zone": None,
            "carrying": [],          # list of WasteAgent objects currently held
            "known_wastes": {},      # pos -> color
            "known_disposal": None,
            "last_action": None,
            "percepts": {},
        }

    # ------------------------------------------------------------------
    # Percept integration
    # ------------------------------------------------------------------

    def _update_knowledge(self, percepts: dict):
        self.knowledge["percepts"] = percepts
        self.knowledge["pos"] = percepts.get("current", {}).get("pos")
        self.knowledge["zone"] = _get_zone_from_percepts(percepts)

        # update map of known waste locations
        for pos, cell_info in percepts.items():
            if pos == "current":
                continue
            waste_here = [
                obj for obj in cell_info.get("contents", [])
                if isinstance(obj, WasteAgent)
            ]
            if waste_here:
                self.knowledge["known_wastes"][pos] = waste_here[0].color
            else:
                self.knowledge["known_wastes"].pop(pos, None)

            # remember disposal zone
            for obj in cell_info.get("contents", []):
                if isinstance(obj, WasteDisposalZone):
                    self.knowledge["known_disposal"] = pos

    # ------------------------------------------------------------------
    # Deliberate (pure function — only uses self.knowledge)
    # ------------------------------------------------------------------

    def deliberate(self, knowledge: dict) -> dict:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------

    def step(self):
        percepts = self.model.get_percepts(self)
        self._update_knowledge(percepts)
        action = self.deliberate(self.knowledge)
        self.knowledge["last_action"] = action
        new_percepts = self.model.do(self, action)
        self._update_knowledge(new_percepts)


# ---------------------------------------------------------------------------
# Green Robot
# ---------------------------------------------------------------------------

class GreenAgent(RobotAgent):
    """
    Lives in z1 only.
    Picks up 2 green wastes, merges them into 1 yellow, then puts it down.
    """

    zone_limit = 1
    robot_color = "green"

    def deliberate(self, knowledge: dict) -> dict:
        carrying = knowledge["carrying"]
        pos = knowledge["pos"]
        percepts = knowledge["percepts"]

        # if holding 2 green -> transform
        green_held = [w for w in carrying if w.color == "green"]
        if len(green_held) >= 2:
            return {"type": TRANSFORM}

        # if holding 1 yellow -> put it down
        yellow_held = [w for w in carrying if w.color == "yellow"]
        if yellow_held:
            return {"type": PUT_DOWN, "waste": yellow_held[0]}

        # try to pick up a green waste on current cell
        current_wastes = [
            obj for obj in percepts.get("current", {}).get("contents", [])
            if isinstance(obj, WasteAgent) and obj.color == "green"
        ]
        if current_wastes and len(green_held) < 2:
            return {"type": PICK_UP, "waste": current_wastes[0]}

        # move toward a known green waste
        known = {p: c for p, c in knowledge["known_wastes"].items() if c == "green"}
        if known:
            target = min(known.keys(), key=lambda p: abs(p[0]-pos[0]) + abs(p[1]-pos[1]))
            return _move_toward(pos, target, percepts, self.zone_limit)

        # explore randomly
        adj = [
            p for p, info in percepts.items()
            if p != "current" and info.get("walkable", False)
        ]
        if adj:
            return {"type": MOVE, "target": random.choice(adj)}
        return {"type": WAIT}


# ---------------------------------------------------------------------------
# Yellow Robot
# ---------------------------------------------------------------------------

class YellowAgent(RobotAgent):
    """
    Lives in z1 and z2.
    Picks up 2 yellow wastes, merges them into 1 red, then puts it down.
    """

    zone_limit = 2
    robot_color = "yellow"

    def deliberate(self, knowledge: dict) -> dict:
        carrying = knowledge["carrying"]
        pos = knowledge["pos"]
        percepts = knowledge["percepts"]

        yellow_held = [w for w in carrying if w.color == "yellow"]
        red_held    = [w for w in carrying if w.color == "red"]

        if len(yellow_held) >= 2:
            return {"type": TRANSFORM}

        if red_held:
            return {"type": PUT_DOWN, "waste": red_held[0]}

        current_wastes = [
            obj for obj in percepts.get("current", {}).get("contents", [])
            if isinstance(obj, WasteAgent) and obj.color == "yellow"
        ]
        if current_wastes and len(yellow_held) < 2:
            return {"type": PICK_UP, "waste": current_wastes[0]}

        known = {p: c for p, c in knowledge["known_wastes"].items() if c == "yellow"}
        if known:
            target = min(known.keys(), key=lambda p: abs(p[0]-pos[0]) + abs(p[1]-pos[1]))
            return _move_toward(pos, target, percepts, self.zone_limit)

        adj = [
            p for p, info in percepts.items()
            if p != "current" and info.get("walkable", False)
        ]
        if adj:
            return {"type": MOVE, "target": random.choice(adj)}
        return {"type": WAIT}


# ---------------------------------------------------------------------------
# Red Robot
# ---------------------------------------------------------------------------

class RedAgent(RobotAgent):
    """
    Lives everywhere (z1, z2, z3).
    Picks up 1 red waste and carries it to the disposal zone in z3.
    """

    zone_limit = 3
    robot_color = "red"

    def deliberate(self, knowledge: dict) -> dict:
        carrying = knowledge["carrying"]
        pos = knowledge["pos"]
        percepts = knowledge["percepts"]

        red_held = [w for w in carrying if w.color == "red"]

        # carrying red waste -> head to disposal zone
        if red_held:
            disposal = knowledge.get("known_disposal")

            # check if standing on disposal zone
            current_contents = percepts.get("current", {}).get("contents", [])
            on_disposal = any(isinstance(o, WasteDisposalZone) for o in current_contents)
            if on_disposal:
                return {"type": DEPOSIT, "waste": red_held[0]}

            if disposal:
                return _move_toward(pos, disposal, percepts, self.zone_limit)

            # scan percepts for disposal
            disp_pos = _find_disposal_in_percepts(percepts)
            if disp_pos:
                return _move_toward(pos, disp_pos, percepts, self.zone_limit)

            # move east to find z3
            adj = [
                p for p, info in percepts.items()
                if p != "current" and info.get("walkable", False)
            ]
            east = [p for p in adj if p[0] > pos[0]]
            if east:
                return {"type": MOVE, "target": random.choice(east)}
            if adj:
                return {"type": MOVE, "target": random.choice(adj)}
            return {"type": WAIT}

        # not carrying -> find a red waste
        current_wastes = [
            obj for obj in percepts.get("current", {}).get("contents", [])
            if isinstance(obj, WasteAgent) and obj.color == "red"
        ]
        if current_wastes:
            return {"type": PICK_UP, "waste": current_wastes[0]}

        known = {p: c for p, c in knowledge["known_wastes"].items() if c == "red"}
        if known:
            target = min(known.keys(), key=lambda p: abs(p[0]-pos[0]) + abs(p[1]-pos[1]))
            return _move_toward(pos, target, percepts, self.zone_limit)

        adj = [
            p for p, info in percepts.items()
            if p != "current" and info.get("walkable", False)
        ]
        if adj:
            return {"type": MOVE, "target": random.choice(adj)}
        return {"type": WAIT}
