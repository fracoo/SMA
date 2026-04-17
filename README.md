# Simulation Multi-Agents — Nettoyage de déchets radioactifs

Un groupe de robots coopère pour nettoyer des déchets radioactifs répartis sur une grille divisée en trois zones de radioactivité croissante. Le projet explore comment la mémoire individuelle et la communication entre agents améliorent l'efficacité collective.


## Contexte et objectif

Trois types de robots (vert, jaune, rouge) doivent nettoyer des déchets radioactifs dans un environnement en grille. Chaque type de robot est assigné à une zone et traite les déchets correspondants :

| Robot | Zone | Rôle |
|-------|------|------|
| **Vert** | z1 (faible radioactivité) | Collecte 2 déchets verts → fabrique 1 déchet jaune → le dépose à la frontière z1/z2 (en z1) |
| **Jaune** | z2 (radioactivité moyenne) | Collecte 2 déchets jaunes → fabrique 1 déchet rouge → le dépose à la frontière z2/z3 (en z2) |
| **Rouge** | z3 (forte radioactivité) | Collecte les déchets rouges → les dépose dans la zone de destruction (volontairement figée tout en bas à droite) |

La quantité initiale de déchets respecte le règle suivante : `4·n` verts, `2·n` jaunes, `1·n` rouge. La simulation s'arrête soit quand tous les déchets sont éliminés, soit après 5 000 pas (selon le paramètre dans simulate.py).


## Structure du projet

```
SMA/
├── 15_robot_mission_MAS2026/        # Code de simulation principal
│   ├── agents.py                    # Logique de chaque type de robot
│   ├── model.py                     # Modèle Mesa (grille, initialisation)
│   ├── objects.py                   # Déchets, radioactivité, zone de dépôt
│   ├── run.py                       # Lancement de la visualisation interactive
│   ├── server.py                    # Interface web Solara
│   └── communication/               # Système de messagerie inter-agents
│       ├── agent/CommunicatingAgent.py
│       ├── mailbox/Mailbox.py
│       └── message/
│           ├── Message.py
│           ├── MessagePerformative.py
│           └── MessageService.py
├── simulate.py                      # Runner de simulations en batch + génération des résultats
├── requirements.txt
└── results/                         # Résultats générés automatiquement
    ├── v0_1_<timestamp>/
    ├── v0_2_<timestamp>/
    ├── v1_1_<timestamp>/
    ├── v1_2_<timestamp>/
    └── v2_2_<timestamp>/
```


## Environnement de simulation

**Grille** : hauteur × largeur, divisée en 3 zones verticales égales.

```
 z1 (vert)  |  z2 (jaune)  |  z3 (rouge)  | [D]
  robots      robots           robots       dépôt
  verts       jaunes           rouges
```


- `[D]` = zone de destruction en haut à droite `(width-1, 0)`
- Chaque robot a **2 emplacements** dans son inventaire
- Perception : cellule courante + 8 voisins + 2 pas orthogonaux supplémentaires (en croix)

<p align="center">
<img src="images/interface.png" alt="Interface" width="500"/>
</p>

Cette interface, issue de solara, permet de rendre compte la position des robots sur la map, ainsi que s'ils portent des déchets ou non grâce aux ronds en bas de chaque point représentant les robots (rond noir => slot vide / rond blanc => slot occupé)

## Évolution des versions

### `v0_1` — Mouvement aléatoire (baseline)

Robots se déplacent aléatoirement. Aucune logique de transfert entre robots. Sert de référence pour mesurer l'apport des versions suivantes.

### `v0_2` — Transfert de déchets entre robots adjacents

Les robots du même type peuvent s'échanger des déchets lorsqu'ils sont sur des cellules voisines, permettant de former plus rapidement des paires pour créer le déchet de niveau supérieur, et éviter des lockdown en fin de run avec des robots de même couleur qui portent chacun 1 déchet et ne peuvent rien en faire puisqu'il n'est plus possible de ramasser un nouveau déchet sur la carte, déjà entièrement vidée.

### `v1_1` — Perception étendue (croix orthogonale)

Les robots perçoivent les déchets non seulement dans leur cellule mais aussi dans les 4 cellules orthogonales adjacentes (haut, bas, gauche, droite) à une distance de 2 pas en ligne droite. Ils se dirigent activement vers les déchets visibles.

### `v1_2` — Perception diagonale + orthogonale étendue

Extension de la perception aux 8 voisins immédiats (diagonales incluses) et aux cellules situées à 2 pas orthogonaux. Améliore la densité effective de collecte.

### `v1_3` — Prévention de collisions + comportements améliorés

- Les robots ne peuvent plus occuper la même cellule
- Les robots portant des déchets ne foncent plus en ligne droite vers la zone de dépôt (comportement plus réaliste)
- La zone de dépôt est libérée après chaque dépôt, évitant les embouteillages

### `v1_4` — Transfert actif vers robots proches

Un robot portant un déchet cherche activement un autre robot du même type avec un emplacement libre dans son champ de vision, et se dirige vers lui pour accélérer la combinaison des paires.

### `v2_1` — Mémoire individuelle (`map_knowledge`)

Chaque robot maintient une carte mentale des déchets de sa couleur observés précédemment. Lorsqu'aucun déchet n'est visible, le robot se dirige vers la position mémorisée la plus proche. La mémoire est mise à jour à chaque pas de visualisation.

### `v2_2` — Communication inter-agents (version actuelle)

Les robots du même type partagent leur `map_knowledge` avec les robots voisins (portée = 1 cellule + 2 pas orthogonaux). Communication par messages `INFORM_REF` contenant les positions de déchets connues. Cela permet à un robot d'apprendre l'existence de déchets qu'il n'a jamais vus directement.

**Logique décisionnelle (v2_2)** à chaque pas :
1. Visualisation → mise à jour de `map_knowledge`
2. Communication → envoi/réception de `map_knowledge` aux voisins du même type
3. Action (par ordre de priorité) :
   - Si à la zone de dépôt avec des déchets → déposer
   - Si les 2 emplacements sont pleins du même type → combiner
   - Si un déchet est présent dans la cellule courante → ramasser
   - Si un robot proche a besoin d'un transfert → transférer
   - Sinon → se déplacer (vers déchets mémorisés, ou aléatoire)


## Installation

```bash
# Cloner / naviguer dans le projet
cd SMA

# Créer un environnement virtuel (recommandé)
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# Installer les dépendances
pip install -r requirements.txt
```

**Dépendances principales** :
- `mesa==3.3.0` — framework multi-agents
- `matplotlib`, `seaborn` — visualisation des résultats
- `solara` — interface web interactive
- `numpy`, `networkx`, `altair`


## Exécution

### Simulations en batch (génération des résultats)

```bash
python simulate.py
```

Lance **20 simulations indépendantes** pour chacune des 15 configurations paramétriques (graines aléatoires différentes). Les résultats sont sauvegardés dans `results/v2_2_<timestamp>/`.

Les configurations testées font varier :
- Le nombre de robots par couleur : 1, 3, 10, 14
- La largeur de la grille : 9, 15, 21, 30 (hauteur fixée à 15)
- La hauteur de la grille : 6, 15, 24, 36 (largeur fixée à 15)
- La densité de déchets (`n_waste`) : 1, 2, 4, 10

Pour changer la version simulée, modifier la variable `VERSION` en haut de `simulate.py`.

### Visualisation interactive

```bash
python 15_robot_mission_MAS2026/run.py
```

Ouvre un serveur Solara (généralement sur `http://localhost:8765`). Permet d'observer pas à pas le comportement des robots sur la grille, de régler les paramètres et de lancer/mettre en pause la simulation.


## Résultats

### Dossiers de résultats

Chaque exécution de `simulate.py` crée un dossier `results/<version>_<timestamp>/` contenant :

```
results/v2_2_20260417_134519/
├── summary.csv
├── runs.csv
└── plots/
    ├── fraction_disposed_over_time.png
    ├── cleanup_rate_comparison.png
    └── visit_heatmaps.png
```

### `summary.csv` — Vue d'ensemble par simulation

Une ligne par simulation individuelle :

| Colonne | Description |
|---------|-------------|
| `config` | Nom de la configuration (ex : `n_robots=3`) |
| `run` | Numéro de la simulation (0 à 19) |
| `cleaned` | `True` si tous les déchets ont été éliminés avant la limite |
| `steps_to_clean` | Nombre de pas pour tout nettoyer (`NaN` si non terminé) |
| `n_green/yellow/red` | Nombre de robots par couleur |
| `n_waste` | Paramètre de densité de déchets |
| `height`, `width` | Dimensions de la grille |

### `runs.csv` — Séries temporelles détaillées

Une ligne par pas de simulation :

| Colonne | Description |
|---------|-------------|
| `step` | Numéro du pas |
| `fraction_disposed` | Fraction des déchets éliminés (0 → 1) |
| `waste_disposed` | Nombre cumulé de déchets éliminés |
| `waste_on_grid` | Déchets encore présents sur la grille |
| `waste_held` | Déchets portés par les robots |
| `throughput` | Déchets éliminés au cours de ce pas |
| `avg_utilization` | Fraction des robots ayant effectué une action utile |
| `config`, `run` | Identifiants de la simulation |

### Graphiques générés

**`fraction_disposed_over_time.png`**
Grille de sous-graphiques (un par configuration). Chaque graphique montre la fraction de déchets éliminés au fil du temps, avec la moyenne en trait plein et ±1 écart-type en zone ombrée. Permet de comparer la vitesse de convergence entre configurations.

**`cleanup_rate_comparison.png`**
Graphiques en barres comparant, pour chaque groupe de configurations :
- Le nombre moyen de pas pour nettoyer complètement
- Le nombre minimum de pas (meilleure simulation)
Les barres grises indiquent les configurations où certaines simulations n'ont pas terminé avant la limite de 5 000 pas.

**`visit_heatmaps.png`**
Carte de chaleur de la fréquence de visite moyenne de chaque cellule de la grille, agrégée sur les 20 runs. Révèle les zones sur-explorées ou sous-explorées et les goulots d'étranglement de circulation.

### Comment interpréter les résultats

- Un `fraction_disposed_over_time` qui atteint 1.0 rapidement → bonne coordination
- Un `avg_utilization` élevé → les robots sont actifs (peu d'errance)
- Des `visit_heatmaps` uniformes → exploration équilibrée de la grille
- Comparer les versions entre elles en chargeant les `summary.csv` de chaque dossier de résultats

```python
import pandas as pd
import glob

# Charger tous les résumés disponibles
dfs = []
for path in glob.glob("results/*/summary.csv"):
    df = pd.read_csv(path)
    df["version"] = path.split("/")[1].split("_")[0] + "_" + path.split("/")[1].split("_")[1]
    dfs.append(df)

summary = pd.concat(dfs)
print(summary.groupby(["version", "config"])["steps_to_clean"].mean())
```
