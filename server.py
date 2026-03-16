# Group: robot_mission_MAS2026
# Date: 2026-03-16
# Members: Colin Friesh, Marie LUDUC , Hammale Mourad

import solara
from mesa.visualization import SolaraViz, make_space_component, make_plot_component
from mesa.visualization.components import AgentPortrayalStyle

from model import RobotMission
from objects import RadioactivityAgent, WasteAgent, WasteDisposalZone
from agents import GreenAgent, YellowAgent, RedAgent


def agent_portrayal(agent):
    if isinstance(agent, RadioactivityAgent):
        color = {1: "#c8f5d0", 2: "#fff3cd", 3: "#f8d7da"}.get(agent.zone, "white")
        return AgentPortrayalStyle(color=color, size=800, marker="s", zorder=0)

    if isinstance(agent, WasteDisposalZone):
        return AgentPortrayalStyle(color="#6c757d", size=500, marker="s", zorder=1)

    if isinstance(agent, WasteAgent):
        colors = {"green": "#28a745", "yellow": "#ffc107", "red": "#dc3545"}
        return AgentPortrayalStyle(color=colors.get(agent.color, "gray"), size=80, marker="o", zorder=2)

    if isinstance(agent, GreenAgent):
        return AgentPortrayalStyle(color="#155724", size=200, marker="o", zorder=3)

    if isinstance(agent, YellowAgent):
        return AgentPortrayalStyle(color="#856404", size=200, marker="o", zorder=3)

    if isinstance(agent, RedAgent):
        return AgentPortrayalStyle(color="#721c24", size=200, marker="o", zorder=3)

    return None


model_params = {
    "width": {
        "type": "SliderInt",
        "value": 15,
        "label": "Grid width",
        "min": 9,
        "max": 30,
        "step": 3,
    },
    "height": {
        "type": "SliderInt",
        "value": 10,
        "label": "Grid height",
        "min": 5,
        "max": 20,
        "step": 1,
    },
    "n_green_robots": {
        "type": "SliderInt",
        "value": 3,
        "label": "Green robots",
        "min": 1,
        "max": 10,
        "step": 1,
    },
    "n_yellow_robots": {
        "type": "SliderInt",
        "value": 2,
        "label": "Yellow robots",
        "min": 1,
        "max": 10,
        "step": 1,
    },
    "n_red_robots": {
        "type": "SliderInt",
        "value": 2,
        "label": "Red robots",
        "min": 1,
        "max": 10,
        "step": 1,
    },
    "n_initial_waste": {
        "type": "SliderInt",
        "value": 10,
        "label": "Initial green waste",
        "min": 1,
        "max": 30,
        "step": 1,
    },
}

SpaceComponent = make_space_component(agent_portrayal)
WasteChart = make_plot_component(["Green waste", "Yellow waste", "Red waste"])
DepositChart = make_plot_component(["Deposited"])

model = RobotMission()


@solara.component
def Page():
    vitesse, set_vitesse = solara.use_state(300)

    solara.SliderInt(
        label="Vitesse (ms/étape)",
        value=vitesse,
        on_value=set_vitesse,
        min=50,
        max=1000,
        step=50,
    )
    SolaraViz(
        model,
        components=[SpaceComponent, WasteChart, DepositChart],
        model_params=model_params,
        name="Robot Mission MAS 2026",
        play_interval=vitesse,
    )


page = Page
