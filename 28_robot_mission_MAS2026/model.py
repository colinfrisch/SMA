# Group: 28
# Date: 16/03/2026
# Members: FRISCH Colin, LEDUC Marie, HAMMALE Mourad

from mesa import Model
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector

from agents import GreenAgent, YellowAgent, RedAgent
from objects import Radioactivity, Waste, WasteDisposalZone


class RobotMission(Model):
    """
    RobotMission model

    The grid is divided west-to-east into three zones of equal width:
      z1  [0, z1_max) : low radioactivity, contains initial green waste
      z2  [z1_max, z2_max): medium radioactivity
      z3  [z2_max, width) : high radioactivity, waste disposal zone located here

    Parameters
    ----------
    n_green : number of green robots
    n_yellow : number of yellow robots
    n_red : number of red robots
    n_green_waste : number of green waste items placed at initialisation
    width, height : grid dimensions
    """

    def __init__(
        self,
        n_green: int = 3,
        n_yellow: int = 3,
        n_red: int = 3,
        n_green_waste: int = 10,
        width: int = 30,
        height: int = 10,
        seed=None,
    ):
        super().__init__(seed=seed)
        self.n_green = n_green
        self.n_yellow = n_yellow
        self.n_red = n_red
        self.width = width
        self.height = height

        self.grid = MultiGrid(width, height, torus=False)
        self.running = True

        # Zone boundaries (column indices, exclusive upper bound)
        self.z1_max = width // 3
        self.z2_max = 2 * (width // 3)

        self._setup_radioactivity()
        self._setup_waste_disposal_zone()
        self._setup_initial_waste(n_green_waste)
        self._setup_robots()

        self.datacollector = DataCollector(
            model_reporters={
                "Green Waste": lambda m: m._count_waste("green"),
                "Yellow Waste": lambda m: m._count_waste("yellow"),
                "Red Waste": lambda m: m._count_waste("red"),
            }
        )

    # _-------------------Helpers for model setup-------------------
    def _setup_radioactivity(self):
        """Place one Radioactivity agent on every cell."""
        for x in range(self.width):
            for y in range(self.height):
                if x < self.z1_max:
                    zone = 1
                elif x < self.z2_max:
                    zone = 2
                else:
                    zone = 3
                radio = Radioactivity(self, zone)
                self.grid.place_agent(radio, (x, y))

    def _setup_waste_disposal_zone(self):
        """Place the WasteDisposalZone on a random cell of the easternmost column."""
        x = self.width - 1
        y = self.random.randrange(self.height)
        wdz = WasteDisposalZone(self)
        self.grid.place_agent(wdz, (x, y))
        self.waste_disposal_pos = (x, y)

    def _setup_initial_waste(self, n_green_waste: int):
        """Scatter green waste randomly across zone z1."""
        for _ in range(n_green_waste):
            x = self.random.randrange(self.z1_max)
            y = self.random.randrange(self.height)
            waste = Waste(self, "green")
            self.grid.place_agent(waste, (x, y))

    def _setup_robots(self):
        """Place robots in their accessible zone(s)."""
        for _ in range(self.n_green):
            x = self.random.randrange(self.z1_max)
            y = self.random.randrange(self.height)
            agent = GreenAgent(self)
            self.grid.place_agent(agent, (x, y))

        for _ in range(self.n_yellow):
            x = self.random.randrange(self.z2_max)
            y = self.random.randrange(self.height)
            agent = YellowAgent(self)
            self.grid.place_agent(agent, (x, y))

        for _ in range(self.n_red):
            x = self.random.randrange(self.width)
            y = self.random.randrange(self.height)
            agent = RedAgent(self)
            self.grid.place_agent(agent, (x, y))

    # -------------------Action Execution-------------------
    def do(self, agent, action: dict) -> dict:
        """
        Execute the action chosen by `agent` and return updated percepts.

        The method checks feasibility before applying any change.
        If the action is not feasible the agent simply receives fresh percepts
        with no state change.

        Supported action types
        ----------------------
        move      : {"type": "move", "direction": "north"|"south"|"east"|"west"}
        pick_up   : {"type": "pick_up", "waste": <Waste>}
        transform : {"type": "transform"}
        put_down  : {"type": "put_down", "waste": <Waste>}
        wait      : {"type": "wait"}
        """
        if action is None or action.get("type") == "wait":
            return self._get_percepts(agent)

        action_type = action.get("type")

        # Move
        if action_type == "move":
            direction = action.get("direction")
            new_pos = self._get_new_pos(agent.pos, direction)
            if new_pos and self._is_move_feasible(agent, new_pos):
                self.grid.move_agent(agent, new_pos)

        # Pick up
        elif action_type == "pick_up":
            waste = action.get("waste")
            cell_contents = self.grid.get_cell_list_contents([agent.pos])
            if waste in cell_contents and isinstance(waste, Waste):
                self.grid.remove_agent(waste)
                agent.knowledge["carried_waste"].append(waste)

        # Transform
        elif action_type == "transform":
            carried = agent.knowledge.get("carried_waste", [])

            if isinstance(agent, GreenAgent):
                greens = [w for w in carried if w.waste_type == "green"]
                if len(greens) >= 2:
                    for w in greens[:2]:
                        carried.remove(w)
                        w.remove()
                    new_waste = Waste(self, "yellow")
                    carried.append(new_waste)

            elif isinstance(agent, YellowAgent):
                yellows = [w for w in carried if w.waste_type == "yellow"]
                if len(yellows) >= 2:
                    for w in yellows[:2]:
                        carried.remove(w)
                        w.remove()
                    new_waste = Waste(self, "red")
                    carried.append(new_waste)

        # Put down
        elif action_type == "put_down":
            waste = action.get("waste")
            carried = agent.knowledge.get("carried_waste", [])
            if waste in carried:
                carried.remove(waste)
                if agent.pos == self.waste_disposal_pos:
                    waste.remove()
                else:
                    self.grid.place_agent(waste, agent.pos)

        return self._get_percepts(agent)

    # --------------------Helpers for agent decision-making-------------------
    def _get_new_pos(self, pos: tuple, direction: str):
        """Return the grid position one step in `direction` from `pos`."""
        x, y = pos
        moves = {"north": (x, y + 1), "south": (x, y - 1),
                 "east":  (x + 1, y), "west":  (x - 1, y)}
        return moves.get(direction)

    def _is_move_feasible(self, agent, new_pos: tuple) -> bool:
        """Check grid bounds and zone access rights."""
        x, y = new_pos
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        if x < self.z1_max:
            zone = 1
        elif x < self.z2_max:
            zone = 2
        else:
            zone = 3
        return zone in agent.allowed_zones

    def _get_percepts(self, agent) -> dict:
        """
        Return a dict mapping each adjacent position (Von Neumann and centre)
        to the list of agent objects present there.
        """
        neighborhood = self.grid.get_neighborhood(
            agent.pos, moore=False, include_center=True
        )
        return {
            pos: self.grid.get_cell_list_contents([pos])
            for pos in neighborhood
        }

    def _count_waste(self, waste_type: str) -> int:
        """Count waste of `waste_type` that is on the grid (not carried, not alone) """
        return sum(
            1 for a in self.agents
            if isinstance(a, Waste) and a.waste_type == waste_type and a.pos is not None
        )

    # ---------------------Scheduler step-------------------
    def step(self):
        self.datacollector.collect(self)
        # Only robot agents need to act, passive objects (Radioactivity, Waste, WasteDisposalZone) have no behaviour
        for robot_type in (GreenAgent, YellowAgent, RedAgent):
            self.agents_by_type[robot_type].shuffle_do("step")
