#Groupe 15, François PETIT, Corentin RAFFRAY, 16 mars 2026

import mesa
import solara
from matplotlib.figure import Figure
from mesa.visualization import SolaraViz, make_plot_component, make_space_component
from mesa.visualization.utils import update_counter
from model import RobotModel

#from model import


def agent_portrayal(agent):
    size = 10
    if agent.color == "green":
        color = "tab:green"
    elif agent.color == "yellow":
        color = "tab:yellow"
    else:
        color = "tab:red"
    return {"size": size, "color": color}

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
    "n": {
        "type": "SliderInt",
        "value": 50,
        "label": "Number of green robots :",
        "min": 1,
        "max": 100,
        "step": 1,
    },
    # "n_yellow": {
    #     "type": "SliderInt",
    #     "value": 50,
    #     "label": "Number of yellow robots :",
    #     "min": 1,
    #     "max": 100,
    #     "step": 1,
    # },
    # "n_red": {
    #     "type": "SliderInt",
    #     "value": 50,
    #     "label": "Number of red robots :",
    #     "min": 1,
    #     "max": 100,
    #     "step": 1,
    # },
    "width": {
        "type": "SliderInt",
        "value": 30,
        "label": "Width of the grid :",
        "min": 10,
        "max": 100,
        "step": 5,
    },
    "height": {
        "type": "SliderInt",
        "value": 10,
        "label": "Height of the grid :",
        "min": 10,
        "max": 100,
        "step": 5,
    },
}

# Create initial model instance
model1 = RobotModel(1, 10, 30)

SpaceGraph = make_space_component(agent_portrayal)

#Create the Dashboard
page = SolaraViz(
    model1,
    components=[SpaceGraph],
    model_params=model_params,
    name="Radioactive Map",
)
# This is required to render the visualization in the Jupyter notebook
page
# to start : "solara run server.py"