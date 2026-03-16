# Group: robot_mission_MAS2026
# Date: 2026-03-16
# Members: (fill in your group members here)

import random
import mesa


class RadioactivityAgent(mesa.Agent):
    """
    Passive agent placed on every cell of the grid.
    Holds the radioactivity level of that cell so robots can
    determine which zone they are standing in.

    Radioactivity ranges:
        z1  ->  [0.00, 0.33)
        z2  ->  [0.33, 0.66)
        z3  ->  [0.66, 1.00]
    """

    def __init__(self, model, zone: int):
        super().__init__(model)
        self.zone = zone
        if zone == 1:
            self.radioactivity = random.uniform(0.0, 0.33)
        elif zone == 2:
            self.radioactivity = random.uniform(0.33, 0.66)
        else:
            self.radioactivity = random.uniform(0.66, 1.0)

    def step(self):
        pass


class WasteDisposalZone(mesa.Agent):
    """
    Passive marker agent placed on the easternmost column.
    Robots identify this cell as the drop-off point for red waste.
    """

    def __init__(self, model):
        super().__init__(model)

    def step(self):
        pass


class WasteAgent(mesa.Agent):
    """
    Passive agent representing a piece of waste.
    color: 'green' | 'yellow' | 'red'
    """

    def __init__(self, model, color: str):
        super().__init__(model)
        assert color in ("green", "yellow", "red"), f"Unknown waste color: {color}"
        self.color = color

    def step(self):
        pass
