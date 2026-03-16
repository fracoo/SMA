#Groupe 15, François PETIT, Corentin RAFFRAY, 16 mars 2026

import mesa
import solara
from matplotlib.figure import Figure
from matplotlib.colors import to_rgba
from mesa.visualization import SolaraViz, make_space_component
from model import RobotModel, RobotAgent
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
        return {"size": 10, "color": to_rgba("tab:blue")}
    elif isinstance(agent, WasteAgent):
        return {"size": 10, "color": to_rgba("tab:gray")}
    else:
        return {"size": 0, "color": (0, 0, 0, 0)}


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
        "value": 50,
        "label": "Number of green robots :",
        "min": 1,
        "max": 100,
        "step": 1,
    },
    "n_yellow": {
        "type": "SliderInt",
        "value": 50,
        "label": "Number of yellow robots :",
        "min": 1,
        "max": 100,
        "step": 1,
    },
    "n_red": {
        "type": "SliderInt",
        "value": 50,
        "label": "Number of red robots :",
        "min": 1,
        "max": 100,
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
        "value": 10,
        "label": "Height of the grid :",
        "min": 5,
        "max": 50,
        "step": 5,
    },
}

# Create initial model instance
model1 = RobotModel(n_green=1, n_yellow=1, n_red=1, height=10, width=30)

SpaceGraph = make_space_component(agent_portrayal)

#Create the Dashboard
page = SolaraViz(
    model1,
    components=[SpaceGraph],
    model_params=model_params,
    name="Radioactive Map",
)
# This is required to render the visualization in the Jupyter notebook
page # type: ignore
# to start : "solara run server.py"