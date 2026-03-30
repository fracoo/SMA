#Groupe 15, François PETIT, Corentin RAFFRAY, 16 mars 2026

import mesa
import solara
import numpy as np
from matplotlib.figure import Figure
from matplotlib.colors import to_rgba
from matplotlib import patches
from mesa.visualization import SolaraViz, make_space_component
from mesa.visualization.utils import update_counter
from model import RobotModel
from agents import RobotAgent, GreenAgent, YellowAgent, RedAgent
from objects import WasteDisposalZone, WasteAgent

#from model import

_COLOR_MAP = {
    "green": to_rgba("tab:green"),
    "yellow": to_rgba("#ffe600"),
    "red": to_rgba("tab:red"),
}

def agent_portrayal(agent):
    if isinstance(agent, RobotAgent):
        color = _COLOR_MAP.get(agent.color, to_rgba("tab:blue"))
        return {"size": 10, "color": color}
    elif isinstance(agent, WasteDisposalZone):
        return {"size": 10, "color": to_rgba("tab:blue"), "marker": "D"}
    elif isinstance(agent, WasteAgent):
        if agent.waste_type == "green":
            return {"size": 5, "color": to_rgba("#1A6D01"), "marker": "s"}
        elif agent.waste_type == "yellow":
            return {"size": 5, "color": to_rgba("#af6f01"), "marker": "s"}
        elif agent.waste_type == "red":
            return {"size": 5, "color": to_rgba("#9e0000"), "marker": "s"}
    else:
        return {"size": 0, "color": (0, 0, 0, 0)}

def draw_zones(ax):
    # This function draws uniform continuous background zones over the grid
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()
    width = x_max - x_min
    z = width / 3
    
    # Add colored rectangle patches with lower zorder so they sit behind agents
    rect_green = patches.Rectangle((x_min, y_min), z, y_max - y_min, facecolor='green', alpha=0.2, zorder=0)
    rect_yellow = patches.Rectangle((x_min + z, y_min), z, y_max - y_min, facecolor='yellow', alpha=0.2, zorder=0)
    rect_red = patches.Rectangle((x_min + 2 * z, y_min), z, y_max - y_min, facecolor='red', alpha=0.2, zorder=0)
    
    ax.add_patch(rect_green)
    ax.add_patch(rect_yellow)
    ax.add_patch(rect_red)
    
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    
    ax.set_aspect('equal')
    # ax.figure.set_size_inches(20, 20)
    ax.set_title("Robot Waste Cleanup", fontsize=14, pad=10)

# @solara.component
# def Histogram(model):
#     update_counter.get() # This is required to update the counter
#     # Note: you must initialize a figure using this method instead of
#     # plt.figure(), for thread safety purpose
#     fig = Figure()
#     ax = fig.subplots()
#     wealth_vals = [agent.wealth for agent in model.agents]
#     # Note: you have to use Matplotlib's OOP API instead of plt.hist
#     # because plt.hist is not thread-safe.
#     ax.hist(wealth_vals, bins=10)
#     solara.FigureMatplotlib(fig)

model_params = {
    "n_green": {
        "type": "SliderInt",
        "value": 8,
        "label": "Number of green robots :",
        "min": 1,
        "max": 10,
        "step": 1,
    },
    "n_yellow": {
        "type": "SliderInt",
        "value": 8,
        "label": "Number of yellow robots :",
        "min": 1,
        "max": 10,
        "step": 1,
    },
    "n_red": {
        "type": "SliderInt",
        "value": 8,
        "label": "Number of red robots :",
        "min": 1,
        "max": 10,
        "step": 1,
    },
        "n_waste": {
        "type": "SliderInt",
        "value": 30,
        "label": "Number of waste objects :",
        "min": 1,
        "max": 30,
        "step": 1,
    },
    "width": {
        "type": "SliderInt",
        "value": 30,
        "label": "Width of the grid :",
        "min": 6,
        "max": 99,
        "step": 3,
    },
    "height": {
        "type": "SliderInt",
        "value": 15,
        "label": "Height of the grid :",
        "min": 5,
        "max": 50,
        "step": 5,
    },
}

# Create initial model instance
model1 = RobotModel(n_green=8, n_yellow=8, n_red=8, n_waste=30, height=15, width=30) # type: ignore

@solara.component # type: ignore
def KnowledgeMap(model):
    """Heatmap showing which cells are known by each robot color."""
    update_counter.get()
    m = model
    width = m.grid.width
    height = m.grid.height

    # One grid per robot color
    grids = {
        "green":  np.zeros((height, width)),
        "yellow": np.zeros((height, width)),
        "red":    np.zeros((height, width)),
    }
    for agent in m.agents:
        if isinstance(agent, RobotAgent) and agent.color in grids:
            for (cx, cy) in agent.map_knowledge:
                if 0 <= cx < width and 0 <= cy < height:
                    grids[agent.color][cy][cx] = 1

    fig = Figure(figsize=(12, 3))
    axes = fig.subplots(1, 3)
    colors_info = [
        ("green",  "Greens",  "Green robots"),
        ("yellow", "YlOrBr",  "Yellow robots"),
        ("red",    "Reds",    "Red robots"),
    ]
    for ax, (color, cmap, title) in zip(axes, colors_info):
        ax.imshow(grids[color], origin="lower", cmap=cmap, vmin=0, vmax=1, aspect="auto")
        ax.set_title(title, fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle("Connaissance de la carte par couleur de robot", fontsize=12)
    fig.tight_layout()
    solara.FigureMatplotlib(fig)


SpaceGraph = make_space_component(agent_portrayal, post_process=draw_zones)

#Create the Dashboard
page = SolaraViz(
    model1,
    components=[SpaceGraph, KnowledgeMap], # type: ignore
    model_params=model_params,
    name="Radioactive Map",
)
# This is required to render the visualization in the Jupyter notebook
page # type: ignore
# to start : "solara run server.py"