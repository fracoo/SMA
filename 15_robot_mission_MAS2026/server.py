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
        "value": 5,
        "label": "Number of green robots :",
        "min": 1,
        "max": 10,
        "step": 1,
    },
    "n_yellow": {
        "type": "SliderInt",
        "value": 5,
        "label": "Number of yellow robots :",
        "min": 1,
        "max": 10,
        "step": 1,
    },
    "n_red": {
        "type": "SliderInt",
        "value": 5,
        "label": "Number of red robots :",
        "min": 1,
        "max": 10,
        "step": 1,
    },
    "n_waste": {
        "type": "SliderInt",
        "value": 2,
        "label": "Number of waste objects :",
        "min": 1,
        "max": 10,
        "step": 1,
    },
    "width": {
        "type": "SliderInt",
        "value": 15,
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
        "step": 1,
    },
    "seed": {
        "type": "InputText",
        "value": "107",
        "label": "Random seed :",
    },
}

# Create initial model instance
model1 = RobotModel(n_green=5, n_yellow=5, n_red=5, n_waste=2, height=15, width=15, seed=107) # type: ignore

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

@solara.component  # type: ignore
def RobotSlotsView(model):
    update_counter.get()
    m = model
    width = m.grid.width
    height = m.grid.height

    fig = Figure(figsize=(12, 6))
    ax = fig.subplots()

    ax.set_xlim(-0.5, width - 0.5)
    ax.set_ylim(-0.5, height - 0.5)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Robots et slots", fontsize=14, pad=10)

    draw_zones(ax)

    for a in m.agents:
        if isinstance(a, WasteDisposalZone) and a.pos is not None:
            x, y = a.pos
            zone = patches.RegularPolygon(
                (x, y), numVertices=4, radius=0.28,
                orientation=np.pi / 4,
                facecolor=to_rgba("tab:blue"),
                edgecolor="black",
                linewidth=1.0,
                zorder=2
            )
            ax.add_patch(zone)

        elif isinstance(a, WasteAgent) and a.pos is not None:
            x, y = a.pos
            if a.waste_type == "green":
                c = to_rgba("#1A6D01")
            elif a.waste_type == "yellow":
                c = to_rgba("#af6f01")
            else:
                c = to_rgba("#9e0000")
            waste = patches.Rectangle(
                (x - 0.12, y - 0.12), 0.24, 0.24,
                facecolor=c, edgecolor="black",
                linewidth=0.8, zorder=2
            )
            ax.add_patch(waste)

    # Robots: grand rond + 2 petits ronds (slots)
    for a in m.agents:
        if isinstance(a, RobotAgent) and a.pos is not None:
            x, y = a.pos
            body_color = _COLOR_MAP.get(a.color, to_rgba("tab:blue"))

            body = patches.Circle(
                (x, y), radius=0.32,
                facecolor=body_color, edgecolor="black",
                linewidth=1.2, zorder=3
            )
            ax.add_patch(body)

            slot1_color = "white" if a.slot1 is not None else "black"
            slot2_color = "white" if a.slot2 is not None else "black"

            slot_left = patches.Circle(
                (x - 0.16, y - 0.27), radius=0.09,
                facecolor=slot1_color, edgecolor="black",
                linewidth=1.0, zorder=4
            )
            slot_right = patches.Circle(
                (x + 0.16, y - 0.27), radius=0.09,
                facecolor=slot2_color, edgecolor="black",
                linewidth=1.0, zorder=4
            )
            ax.add_patch(slot_left)
            ax.add_patch(slot_right)

    fig.tight_layout()
    solara.FigureMatplotlib(fig)


@solara.component  # type: ignore
def RobotDebugTable(model):
    """Table de debug: liste tous les robots avec position et contenu des slots."""
    update_counter.get()
    rows = []
    for a in sorted(model.agents, key=lambda a: getattr(a, 'name', str(a))):
        if isinstance(a, RobotAgent):
            s1 = a.slot1.waste_type if a.slot1 else "—"
            s2 = a.slot2.waste_type if a.slot2 else "—"
            rows.append(f"{a.get_name():<30}  pos={str(a.pos):<12}  slot1={s1:<8}  slot2={s2}")
    step = model.steps if hasattr(model, 'steps') else "?"
    text = f"**Step {step}**\n```\n" + "\n".join(rows) + "\n```"
    solara.Markdown(text)


@solara.component  # type: ignore
def WasteTimeSeries(model):
    """Courbe waste_on_grid + waste_held + waste_disposed sur le même graphe."""
    update_counter.get()
    df = model.datacollector.get_model_vars_dataframe()
    if df.empty:
        return
    fig = Figure(figsize=(10, 3))
    ax = fig.subplots()
    ax.plot(df.index, df["waste_on_grid"],  label="On grid",  color="saddlebrown")
    ax.plot(df.index, df["waste_held"],     label="Held",     color="orange")
    ax.plot(df.index, df["waste_disposed"], label="Disposed", color="forestgreen")
    ax.set_xlabel("Step")
    ax.set_ylabel("Waste units")
    ax.set_title("Pipeline des déchets")
    ax.legend()
    fig.tight_layout()
    solara.FigureMatplotlib(fig)


@solara.component  # type: ignore
def ThroughputChart(model):
    """Courbe du throughput (déchets éliminés par step) avec moyenne glissante."""
    update_counter.get()
    df = model.datacollector.get_model_vars_dataframe()
    if df.empty or "throughput" not in df.columns:
        return
    fig = Figure(figsize=(10, 3))
    ax = fig.subplots()
    raw = df["throughput"]
    ax.plot(df.index, raw, alpha=0.35, color="steelblue", label="Raw")
    rolling = raw.rolling(window=10, min_periods=1).mean()
    ax.plot(df.index, rolling, color="steelblue", linewidth=2, label="Moy. glissante (10 steps)")
    if "avg_utilization" in df.columns:
        ax2 = ax.twinx()
        ax2.plot(df.index, df["avg_utilization"], color="darkorange", linewidth=1.5,
                 linestyle="--", label="Taux utilisation")
        ax2.set_ylabel("Taux d'utilisation", color="darkorange")
        ax2.set_ylim(0, 1)
        ax2.tick_params(axis="y", labelcolor="darkorange")
        ax2.legend(loc="upper right")
    ax.set_xlabel("Step")
    ax.set_ylabel("Déchets / step")
    ax.set_title("Throughput & taux d'utilisation des robots")
    ax.legend(loc="upper left")
    fig.tight_layout()
    solara.FigureMatplotlib(fig)


@solara.component  # type: ignore
def VisitHeatmap(model):
    """Heatmap de fréquentation : combien de fois chaque cellule a été visitée."""
    update_counter.get()
    counts = model.visit_counts
    if counts.max() == 0:
        return
    fig = Figure(figsize=(8, 4))
    ax = fig.subplots()
    im = ax.imshow(counts, origin="lower", cmap="hot", aspect="auto")
    fig.colorbar(im, ax=ax, label="Visites")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Fréquentation des cellules")
    fig.tight_layout()
    solara.FigureMatplotlib(fig)


SpaceGraph = make_space_component(agent_portrayal, post_process=draw_zones)

#Create the Dashboard
page = SolaraViz(
    model1,
    components=[RobotSlotsView, WasteTimeSeries, ThroughputChart, VisitHeatmap, KnowledgeMap, RobotDebugTable],  # type: ignore
    model_params=model_params,
    name="Radioactive Map",
)
# This is required to render the visualization in the Jupyter notebook
page # type: ignore
# to start : "solara run server.py"




