"""Main script to run the RobotMission model and visualize results using SolaraViz"""

import matplotlib.patches as mpatches

from mesa.visualization import SolaraViz, make_space_component, make_plot_component
from mesa.visualization.components import AgentPortrayalStyle

from model import RobotMission
from agents import GreenAgent, YellowAgent, RedAgent
from objects import Radioactivity, Waste, WasteDisposalZone

# ---------------------Grid dimensions---------------------
WIDTH = 30
HEIGHT = 10

# ---------------------Portrayal function for agents---------------------
def agent_portrayal(agent):
    # Radioactivity agents are invisible and zones are drawn by post_process.
    if isinstance(agent, Radioactivity):
        return AgentPortrayalStyle(
            color="white", size=0, alpha=0, zorder=1
        )

    if isinstance(agent, WasteDisposalZone):
        return AgentPortrayalStyle(
            color="#222222",
            marker="s",
            size=250,
            zorder=1,
            alpha=0.9,
        )

    if isinstance(agent, Waste):
        color_map = {"green": "#1a7a1a", "yellow": "#e6c800", "red": "#cc0000"}
        return AgentPortrayalStyle(
            color=color_map.get(agent.waste_type, "grey"),
            marker="s",
            size=80,
            zorder=1,
            alpha=0.9,
        )

    if isinstance(agent, GreenAgent):
        return AgentPortrayalStyle(
            color="#00cc44",
            marker="o",
            size=150,
            zorder=1,
            edgecolors="black",
            linewidths=1.2,
        )

    if isinstance(agent, YellowAgent):
        return AgentPortrayalStyle(
            color="#ffdd00",
            marker="o",
            size=150,
            zorder=1,
            edgecolors="black",
            linewidths=1.2,
        )

    if isinstance(agent, RedAgent):
        return AgentPortrayalStyle(
            color="#ff3300",
            marker="o",
            size=150,
            zorder=1,
            edgecolors="black",
            linewidths=1.2,
        )

    # Fallback: invisible
    return AgentPortrayalStyle(color="white", size=0, alpha=0, zorder=1)


# ---------------------Post-processing function to draw zone backgrounds-------------------
def draw_zone_backgrounds(ax):
    z1_max = WIDTH // 3
    z2_max = 2 * (WIDTH // 3)

    ax.axvspan(-0.5, z1_max - 0.5,         alpha=0.12, color="green",  zorder=0)
    ax.axvspan(z1_max - 0.5, z2_max - 0.5, alpha=0.12, color="yellow", zorder=0)
    ax.axvspan(z2_max - 0.5, WIDTH - 0.5,  alpha=0.12, color="red",    zorder=0)

    legend_patches = [
        mpatches.Patch(color="green",  alpha=0.4, label="z1 – low radioactivity"),
        mpatches.Patch(color="yellow", alpha=0.4, label="z2 – medium radioactivity"),
        mpatches.Patch(color="red",    alpha=0.4, label="z3 – high radioactivity"),
    ]
    ax.legend(handles=legend_patches, loc="upper left", fontsize=7)


# ----------------------Space and plot components---------------------
space_component = make_space_component(
    agent_portrayal,
    post_process=draw_zone_backgrounds,
)

plot_component = make_plot_component(
    {"Green Waste": "#00cc44", "Yellow Waste": "#ffdd00", "Red Waste": "#ff3300"},
)

# -----------------------Interactive model parameters---------------------
model_params = {
    "n_green": {
        "type": "SliderInt",
        "value": 3,
        "label": "Green Robots",
        "min": 1,
        "max": 10,
        "step": 1,
    },
    "n_yellow": {
        "type": "SliderInt",
        "value": 3,
        "label": "Yellow Robots",
        "min": 1,
        "max": 10,
        "step": 1,
    },
    "n_red": {
        "type": "SliderInt",
        "value": 3,
        "label": "Red Robots",
        "min": 1,
        "max": 10,
        "step": 1,
    },
    "n_green_waste": {
        "type": "SliderInt",
        "value": 10,
        "label": "Initial Green Waste",
        "min": 0,
        "max": 30,
        "step": 1,
    },
    "n_yellow_waste": {
        "type": "SliderInt",
        "value": 0,
        "label": "Initial Yellow Waste",
        "min": 0,
        "max": 30,
        "step": 1,
    },
    "n_red_waste": {
        "type": "SliderInt",
        "value": 0,
        "label": "Initial Red Waste",
        "min": 0,
        "max": 30,
        "step": 1,
    },
    "communication_range": {
        "type": "SliderInt",
        "value": 10,
        "label": "Communication Range",
        "min": 0,
        "max": 20,
        "step": 1,
    },
    "width":  WIDTH,
    "height": HEIGHT,
}

# ------------------------Server run---------------------
# run with solara run server.py
model = RobotMission()

page = SolaraViz(
    model,
    components=[space_component, plot_component],
    model_params=model_params,
    name="Waste disposal – Group 28",
)
