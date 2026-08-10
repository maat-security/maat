"""Pure-Python force-directed graph layout.

No numpy/scipy dependency — deliberately. networkx's own layout
functions (spring_layout, kamada_kawai_layout, ...) require numpy,
which isn't in requirements.txt today, and graph.py's own docstring
caps the realistic scale at "tens to low hundreds of nodes" — well
within what a plain Fruchterman-Reingold simulation handles in pure
Python without a vectorized backend.

compute_layout() takes an explicit graph argument, same testability
principle as metrics.py/remediation.py — it works on any nx.DiGraph,
independent of graph.py's module-level singleton.
"""

import math
import random

DEFAULT_ITERATIONS = 200
DEFAULT_WIDTH = 800.0
DEFAULT_HEIGHT = 600.0
REPULSION_CONSTANT = 8000.0
ATTRACTION_CONSTANT = 0.02
MIN_DISTANCE = 1.0


def compute_layout(g, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, iterations=DEFAULT_ITERATIONS, seed=42):
    """Return {node_id: (x, y)} positions within a width x height box.

    Deterministic for a given graph + seed — the same node/edge set
    always produces the same layout, which matters both for a stable
    visual across re-renders (nothing worse than a graph that jumps
    around every time you open it) and for testing.
    """
    nodes = list(g.nodes)
    if not nodes:
        return {}
    if len(nodes) == 1:
        return {nodes[0]: (width / 2, height / 2)}

    rng = random.Random(seed)
    positions = {n: [rng.uniform(0, width), rng.uniform(0, height)] for n in nodes}

    # Direction doesn't matter for layout purposes — two nodes with an
    # edge between them should be pulled together regardless of which
    # way it points.
    undirected_edges = {tuple(sorted((u, v))) for u, v in g.to_undirected().edges()}
    max_displacement = max(width, height) / 10.0

    for iteration in range(iterations):
        forces = {n: [0.0, 0.0] for n in nodes}

        for i, u in enumerate(nodes):
            for v in nodes[i + 1:]:
                dx = positions[u][0] - positions[v][0]
                dy = positions[u][1] - positions[v][1]
                distance = max(math.hypot(dx, dy), MIN_DISTANCE)
                force = REPULSION_CONSTANT / (distance * distance)
                fx, fy = (dx / distance) * force, (dy / distance) * force
                forces[u][0] += fx
                forces[u][1] += fy
                forces[v][0] -= fx
                forces[v][1] -= fy

        for u, v in undirected_edges:
            dx = positions[u][0] - positions[v][0]
            dy = positions[u][1] - positions[v][1]
            distance = max(math.hypot(dx, dy), MIN_DISTANCE)
            force = ATTRACTION_CONSTANT * distance
            fx, fy = (dx / distance) * force, (dy / distance) * force
            forces[u][0] -= fx
            forces[u][1] -= fy
            forces[v][0] += fx
            forces[v][1] += fy

        temperature = max_displacement * (1 - iteration / iterations)
        for n in nodes:
            fx, fy = forces[n]
            magnitude = max(math.hypot(fx, fy), MIN_DISTANCE)
            displacement = min(magnitude, temperature)
            positions[n][0] += (fx / magnitude) * displacement
            positions[n][1] += (fy / magnitude) * displacement
            positions[n][0] = min(max(positions[n][0], 0.0), width)
            positions[n][1] = min(max(positions[n][1], 0.0), height)

    return {n: (positions[n][0], positions[n][1]) for n in nodes}
