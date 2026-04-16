# Group 28 - Robot Mission MAS 2026
# Created: 2026-04-13
# Members: Colin Frisch
"""Definition of the RobotMission model and its core logic"""

import threading

from mesa import Model
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector

from agents import GreenAgent, YellowAgent, RedAgent
from objects import Radioactivity, WasteDisposalZone, Waste


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
    n_yellow_waste : number of yellow waste items placed at initialisation
    n_red_waste : number of red waste items placed at initialisation
    width, height : grid dimensions
    """

    def __init__(
        self,
        n_green: int = 3,
        n_yellow: int = 3,
        n_red: int = 3,
        n_green_waste: int = 10,
        n_yellow_waste: int = 0,
        n_red_waste: int = 0,
        width: int = 30,
        height: int = 10,
        communication_range: int = 10,
        seed=None,
    ):
        super().__init__(seed=seed)
        self.n_green = n_green
        self.n_yellow = n_yellow
        self.n_red = n_red
        self.width = width
        self.height = height
        self.communication_range = communication_range

        self.grid = MultiGrid(width, height, torus=False)
        self.running = True

        # Messaging and metrics
        self.total_messages_sent = 0
        self.waste_disposed_count = 0

        # Zone boundaries (column indices, exclusive upper bound)
        self.z1_max = width // 3
        self.z2_max = 2 * (width // 3)

        self._setup_radioactivity()
        self._setup_waste_disposal_zone()
        self._setup_initial_waste(n_green_waste)
        self._setup_initial_yellow_waste(n_yellow_waste)
        self._setup_initial_red_waste(n_red_waste)
        self._setup_robots()

        self._collect_lock = threading.Lock()
        self.datacollector = DataCollector(
            model_reporters={
                "Green Waste": lambda m: m._count_waste("green"),
                "Yellow Waste": lambda m: m._count_waste("yellow"),
                "Red Waste": lambda m: m._count_waste("red"),
                "Total Messages": lambda m: m.total_messages_sent,
            }
        )

        # Make collect() and get_model_vars_dataframe() thread-safe so that
        # Solara's render thread cannot read a partially-appended model_vars dict.
        _lock = self._collect_lock
        _original_collect = self.datacollector.collect
        _original_get_df = self.datacollector.get_model_vars_dataframe

        def _safe_collect(model):
            with _lock:
                _original_collect(model)

        def _safe_get_df():
            with _lock:
                return _original_get_df()

        self.datacollector.collect = _safe_collect
        self.datacollector.get_model_vars_dataframe = _safe_get_df

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

    def _setup_initial_yellow_waste(self, n_yellow_waste: int):
        """Scatter yellow waste randomly across zones z1 and z2."""
        for _ in range(n_yellow_waste):
            x = self.random.randrange(self.z2_max)
            y = self.random.randrange(self.height)
            waste = Waste(self, "yellow")
            self.grid.place_agent(waste, (x, y))

    def _setup_initial_red_waste(self, n_red_waste: int):
        """Scatter red waste randomly across zones z1, z2, and z3."""
        for _ in range(n_red_waste):
            x = self.random.randrange(self.width)
            y = self.random.randrange(self.height)
            waste = Waste(self, "red")
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

    # -------------------Action execution (do)-------------------
    def do(self, agent, action):
        """
        Execute an agent's action after checking feasibility, then return percepts.

        Parameters
        ----------
        agent : RobotAgent
        action : dict with at least a "type" key

        Returns
        -------
        dict : percepts mapping neighbouring positions to their cell contents
        """
        if action is not None and action.get("type") != "wait":
            action_type = action.get("type")

            if action_type == "move":
                new_pos = self._compute_new_pos(agent.pos, action["direction"])
                if new_pos and self._is_move_feasible(agent, new_pos):
                    self.grid.move_agent(agent, new_pos)

            elif action_type == "pick_up":
                waste = action["waste"]
                cell_contents = self.grid.get_cell_list_contents([agent.pos])
                if waste in cell_contents and isinstance(waste, Waste):
                    self.grid.remove_agent(waste)
                    agent.knowledge["carried_waste"].append(waste)

            elif action_type == "transform":
                agent._do_transform()

            elif action_type == "put_down":
                waste = action["waste"]
                carried = agent.knowledge["carried_waste"]
                if waste in carried:
                    carried.remove(waste)
                    if agent.pos == self.waste_disposal_pos:
                        waste.remove()
                        self.waste_disposed_count += 1
                    else:
                        self.grid.place_agent(waste, agent.pos)

            # Handle messaging if included in the action
            if "message" in action:
                msg = action["message"]
                recipient_map = {"yellow": YellowAgent, "red": RedAgent}
                recipient_type = recipient_map.get(msg["recipient"])
                if recipient_type:
                    self.broadcast_message(
                        agent, msg["msg_type"], agent.pos, recipient_type
                    )

        # Return percepts: adjacent tiles and their contents
        neighborhood = self.grid.get_neighborhood(
            agent.pos, moore=False, include_center=True
        )
        return {
            pos: self.grid.get_cell_list_contents([pos])
            for pos in neighborhood
        }

    @staticmethod
    def _compute_new_pos(pos, direction):
        x, y = pos
        moves = {
            "north": (x, y + 1),
            "south": (x, y - 1),
            "east": (x + 1, y),
            "west": (x - 1, y),
        }
        return moves.get(direction)

    def _is_move_feasible(self, agent, new_pos):
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

    # -------------------Messaging system-------------------
    def broadcast_message(self, sender, msg_type: str, pos: tuple, recipient_type):
        """
        Send a message from sender to all recipients of a given type within communication range.

        Parameters
        ----------
        sender : Agent
        msg_type : str
        pos : tuple
        recipient_type : class
        """
        recipients = self._get_agents_in_range(pos, recipient_type, self.communication_range)
        message_count = 0
        for recipient in recipients:
            if recipient != sender:
                waste_type = "yellow" if msg_type == "yellow_waste_at" else "red"
                if pos not in recipient.knowledge.get("known_targets", {}).get(waste_type, []):
                    if waste_type not in recipient.knowledge["known_targets"]:
                        recipient.knowledge["known_targets"][waste_type] = []
                    recipient.knowledge["known_targets"][waste_type].append(pos)
                    message_count += 1
        self.total_messages_sent += message_count
        return message_count

    def _get_agents_in_range(self, pos: tuple, agent_type, range_dist: int):
        """
        Get all agents of a given type within distance range_dist from pos.

        Parameters
        ----------
        pos : tuple
        agent_type : class
        range_dist : int

        Returns
        -------
        list : Agents of agent_type within range_dist of pos
        """
        result = []
        x0, y0 = pos
        for agent in self.agents:
            if isinstance(agent, agent_type) and agent.pos is not None:
                x1, y1 = agent.pos
                dist = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
                if dist <= range_dist:
                    result.append(agent)
        return result

    def _count_waste(self, waste_type: str) -> int:
        """Count waste of `waste_type` that is on the grid (not carried, not alone) """
        return sum(
            1 for a in self.agents
            if isinstance(a, Waste) and a.waste_type == waste_type and a.pos is not None
        )

    # ---------------------Scheduler step-------------------
    def step(self):
        # Clear known targets each step (messages persist for one step only)
        for agent in self.agents:
            if hasattr(agent, 'knowledge') and 'known_targets' in agent.knowledge:
                agent.knowledge['known_targets'] = {"yellow": [], "red": []}
        
        # Only robot agents need to act, passive objects (Radioactivity, Waste, WasteDisposalZone) have no behaviour
        for robot_type in (GreenAgent, YellowAgent, RedAgent):
            self.agents_by_type[robot_type].shuffle_do("step")
        self.datacollector.collect(self)
