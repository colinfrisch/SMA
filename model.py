# Group: robot_mission_MAS2026
# Date: 2026-03-16
# Members: Colin Friesh, Marie LUDUC , Hammale Mourad

import random
import threading
import mesa

from objects import RadioactivityAgent, WasteAgent, WasteDisposalZone
from agents import (
    GreenAgent, YellowAgent, RedAgent,
    MOVE, PICK_UP, TRANSFORM, PUT_DOWN, DEPOSIT, WAIT,
)


class RobotMission(mesa.Model):
    """
    Main simulation model.

    Parameters
    ----------
    width, height       : grid dimensions
    n_green_robots      : number of green robots
    n_yellow_robots     : number of yellow robots
    n_red_robots        : number of red robots
    n_initial_waste     : initial green waste count in z1
    """

    def __init__(
        self,
        width: int = 15,
        height: int = 10,
        n_green_robots: int = 3,
        n_yellow_robots: int = 2,
        n_red_robots: int = 2,
        n_initial_waste: int = 10,
        seed=None,
    ):
        super().__init__(rng=seed)

        self.width = width
        self.height = height
        self.grid = mesa.space.MultiGrid(width, height, torus=False)

        # zone boundaries (columns, 0-indexed)
        self.z1_cols = range(0, width // 3)
        self.z2_cols = range(width // 3, 2 * width // 3)
        self.z3_cols = range(2 * width // 3, width)

        self._place_radioactivity()
        self._place_disposal_zone()
        self._place_initial_waste(n_initial_waste)
        self._place_robots(n_green_robots, n_yellow_robots, n_red_robots)

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Green waste":  lambda m: m.count_waste("green"),
                "Yellow waste": lambda m: m.count_waste("yellow"),
                "Red waste":    lambda m: m.count_waste("red"),
                "Deposited":    lambda m: m.deposited,
            }
        )
        self.deposited = 0
        self.running = True

        # Thread-safe wrappers: Mesa 3.5 steps the model in a background thread
        # while the chart renders in another, causing intermittent length mismatches.
        self._dc_lock = threading.Lock()
        _orig_collect = self.datacollector.collect
        _orig_get_df = self.datacollector.get_model_vars_dataframe

        def _safe_collect(model):
            with self._dc_lock:
                _orig_collect(model)

        def _safe_get_df():
            with self._dc_lock:
                return _orig_get_df()

        self.datacollector.collect = _safe_collect
        self.datacollector.get_model_vars_dataframe = _safe_get_df

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _zone_for_col(self, col: int) -> int:
        if col in self.z1_cols:
            return 1
        if col in self.z2_cols:
            return 2
        return 3

    def _place_radioactivity(self):
        for col in range(self.width):
            zone = self._zone_for_col(col)
            for row in range(self.height):
                agent = RadioactivityAgent(self, zone)
                self.grid.place_agent(agent, (col, row))

    def _place_disposal_zone(self):
        col = self.width - 1
        row = random.randrange(self.height)
        self.disposal_pos = (col, row)
        agent = WasteDisposalZone(self)
        self.grid.place_agent(agent, self.disposal_pos)

    def _place_initial_waste(self, n: int):
        z1_cells = [(c, r) for c in self.z1_cols for r in range(self.height)]
        chosen = random.sample(z1_cells, min(n, len(z1_cells)))
        for pos in chosen:
            waste = WasteAgent(self, "green")
            self.grid.place_agent(waste, pos)

    def _place_robots(self, ng: int, ny: int, nr: int):
        z1_cells = [(c, r) for c in self.z1_cols for r in range(self.height)]
        z2_cells = [(c, r) for c in self.z2_cols for r in range(self.height)]
        all_cells = [(c, r) for c in range(self.width) for r in range(self.height)]

        for _ in range(ng):
            pos = random.choice(z1_cells)
            a = GreenAgent(self)
            self.grid.place_agent(a, pos)

        for _ in range(ny):
            pos = random.choice(z1_cells + z2_cells)
            a = YellowAgent(self)
            self.grid.place_agent(a, pos)

        for _ in range(nr):
            pos = random.choice(all_cells)
            a = RedAgent(self)
            self.grid.place_agent(a, pos)

    # ------------------------------------------------------------------
    # Percepts
    # ------------------------------------------------------------------

    def get_percepts(self, agent) -> dict:
        """
        Return a dictionary describing the current cell and all
        Moore-neighborhood cells visible to the agent.
        """
        pos = agent.pos
        percepts = {
            "current": {
                "pos": pos,
                "contents": list(self.grid.get_cell_list_contents([pos])),
            }
        }
        for neighbor in self.grid.get_neighborhood(pos, moore=True, include_center=False):
            col = neighbor[0]
            zone = self._zone_for_col(col)
            walkable = zone <= agent.zone_limit
            percepts[neighbor] = {
                "contents": list(self.grid.get_cell_list_contents([neighbor])),
                "walkable": walkable,
            }
        return percepts

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------

    def do(self, agent, action: dict) -> dict:
        action_type = action.get("type", WAIT)

        if action_type == MOVE:
            self._do_move(agent, action)

        elif action_type == PICK_UP:
            self._do_pick_up(agent, action)

        elif action_type == TRANSFORM:
            self._do_transform(agent)

        elif action_type == PUT_DOWN:
            self._do_put_down(agent, action)

        elif action_type == DEPOSIT:
            self._do_deposit(agent, action)

        # always return fresh percepts after the action
        return self.get_percepts(agent)

    def _do_move(self, agent, action: dict):
        target = action.get("target")
        if target is None:
            return
        col = target[0]
        zone = self._zone_for_col(col)
        if zone > agent.zone_limit:
            return
        if not self.grid.is_cell_empty(target):
            # cell occupied — still allowed (MultiGrid), just move
            pass
        self.grid.move_agent(agent, target)

    def _do_pick_up(self, agent, action: dict):
        waste = action.get("waste")
        if waste is None:
            return
        # check the waste is actually on the same cell
        cell_contents = self.grid.get_cell_list_contents([agent.pos])
        if waste not in cell_contents:
            return
        self.grid.remove_agent(waste)
        agent.knowledge["carrying"].append(waste)

    def _do_transform(self, agent):
        carrying = agent.knowledge["carrying"]

        green_held = [w for w in carrying if w.color == "green"]
        yellow_held = [w for w in carrying if w.color == "yellow"]

        if len(green_held) >= 2:
            carrying.remove(green_held[0])
            carrying.remove(green_held[1])
            new_waste = WasteAgent(self, "yellow")
            carrying.append(new_waste)

        elif len(yellow_held) >= 2:
            carrying.remove(yellow_held[0])
            carrying.remove(yellow_held[1])
            new_waste = WasteAgent(self, "red")
            carrying.append(new_waste)

    def _do_put_down(self, agent, action: dict):
        waste = action.get("waste")
        if waste is None or waste not in agent.knowledge["carrying"]:
            return
        agent.knowledge["carrying"].remove(waste)
        self.grid.place_agent(waste, agent.pos)

    def _do_deposit(self, agent, action: dict):
        waste = action.get("waste")
        if waste is None or waste not in agent.knowledge["carrying"]:
            return
        col = agent.pos[0]
        zone = self._zone_for_col(col)
        if zone != 3:
            return
        agent.knowledge["carrying"].remove(waste)
        self.deposited += 1

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def count_waste(self, color: str) -> int:
        count = 0
        for cell_content, _ in self.grid.coord_iter():
            for obj in cell_content:
                if isinstance(obj, WasteAgent) and obj.color == color:
                    count += 1
        # also count waste being carried
        for agent in self.agents:
            if hasattr(agent, "knowledge"):
                for w in agent.knowledge.get("carrying", []):
                    if isinstance(w, WasteAgent) and w.color == color:
                        count += 1
        return count

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------

    def step(self):
        self.agents.shuffle_do("step")

        total_waste = (
            self.count_waste("green")
            + self.count_waste("yellow")
            + self.count_waste("red")
        )
        if total_waste == 0:
            self.running = False

        self.datacollector.collect(self)
