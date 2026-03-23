# Group: 28
# Date: 16/03/2026
# Members: FRISCH Colin, LEDUC Marie, HAMMALE Mourad

import random
from mesa import Agent


class Radioactivity(Agent):
    """
    Passive agent placed on every cell of the grid.
    Holds a radioactivity level sampled uniformly from the zone range:
      z1 -> [0.00, 0.33) low
      z2 -> [0.33, 0.66) medium
      z3 -> [0.66, 1.00] high
    Robot agents read this value to know which zone they are in.
    """

    def __init__(self, model, zone: int):
        super().__init__(model)
        self.zone = zone
        if zone == 1:
            self.radioactivity = random.uniform(0.00, 0.33)
        elif zone == 2:
            self.radioactivity = random.uniform(0.33, 0.66)
        else:
            self.radioactivity = random.uniform(0.66, 1.00)

    def step(self):
        pass


class WasteDisposalZone(Agent):
    """
    Passive agent marking the waste disposal cell.
    Placed on a randomly chosen cell in the easternmost column of the grid.
    Red robots deliver fully-transformed (red) waste here.
    """

    def __init__(self, model):
        super().__init__(model)

    def step(self):
        pass


class Waste(Agent):
    """
    Passive agent representing a waste object on the grid.
    Attribute waste_type: "green", "yellow", or "red".
    """

    def __init__(self, model, waste_type: str):
        super().__init__(model)
        assert waste_type in ("green", "yellow", "red"), f"Unknown waste type: {waste_type}"
        self.waste_type = waste_type
    def step(self):
        pass

