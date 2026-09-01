from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from geodisk_paper.data.regions import RegionReference
from geodisk_paper.geometry.mappings import GeometryResult, harmonic_seed_positions
from geodisk_paper.geometry.power import balanced_power_cells, circular_domain, warp_geometry
from geodisk_paper.metrics.geometry import display_adjacency, geometry_validity
from geodisk_paper.metrics.spatial import evaluate_spatial
from geodisk_paper.topology.embedding import TopologyEmbedding, topology_seed_positions


@dataclass
class Candidate:
    label: str
    points: np.ndarray
    cells: list
    weights: np.ndarray
    score: float
    metrics: dict[str, float]
    area_cv: float


def _geographic_positions(reference: RegionReference, view: str, inner: float, outer: float) -> np.ndarray:
    theta = reference.cells.theta.to_numpy(float)
    rho = reference.cells.rho.to_numpy(float)
    radius = rho if view == "disk" else inner + rho * (outer - inner)
    radius = np.clip(radius, .025 if view == "disk" else inner + .015, outer - .015)
    return np.column_stack([radius * np.cos(theta), radius * np.sin(theta)])


def _project(points: np.ndarray, view: str, inner: float, outer: float) -> np.ndarray:
    result = np.asarray(points, float).copy()
    radius = np.hypot(result[:, 0], result[:, 1])
    zero = radius < 1e-10
    if np.any(zero):
        angles = np.linspace(0, 2 * math.pi, len(result), endpoint=False)
        result[zero] = np.column_stack([.03 * np.cos(angles[zero]), .03 * np.sin(angles[zero])])
        radius = np.hypot(result[:, 0], result[:, 1])
    minimum = .025 if view == "disk" else inner + .015
    target = np.clip(radius, minimum, outer - .015)
    result *= (target / np.maximum(radius, 1e-12))[:, None]
    return result


def _score_candidate(
    reference: RegionReference, ids: list[str], points: np.ndarray, view: str, inner: float, outer: float,
    power_iterations: int, objective_weights: dict[str, float], label: str, contact_tolerance: float,
) -> Candidate:
    domain = circular_domain(view, inner, outer)
    points = _project(points, view, inner, outer)
    cells, weights, _ = balanced_power_cells(points, domain, iterations=power_iterations, balance=True)
    edges = display_adjacency(ids, cells, tolerance=contact_tolerance)
    source = {str(row.cell_id): (float(row.longitude), float(row.latitude)) for row in reference.cells.itertuples()}
    target = {cell_id: (float(cell.centroid.x), float(cell.centroid.y)) for cell_id, cell in zip(ids, cells)}
    theta = {str(row.cell_id): float(row.theta) for row in reference.cells.itertuples()}
    rho = {str(row.cell_id): float(row.rho) for row in reference.cells.itertuples()}
    metrics = evaluate_spatial(ids, reference.edges, edges, source, target, theta, rho, reference.anchor[1])
    validity = geometry_validity(cells, domain)
    radial = metrics["radial_spearman"] if np.isfinite(metrics["radial_spearman"]) else -1.0
    score = (
        objective_weights.get("adjacency", 1.0) * metrics["adj_f1"]
        + objective_weights.get("neighborhood", .18) * metrics["np2"]
        - objective_weights.get("local_direction", .06) * metrics["local_direction_error_deg"] / 180.0
        - objective_weights.get("angular", .04) * metrics["angular_error_deg"] / 180.0
        - objective_weights.get("radial", .04) * (1.0 - radial) / 2.0
        - objective_weights.get("area_cv", .035) * min(validity["area_cv"], 2.0)
    )
    return Candidate(label, points, cells, weights, float(score), metrics, float(validity["area_cv"]))


def _topology_forces(candidate: Candidate, reference: RegionReference, ids: list[str],
                     contact_tolerance: float) -> np.ndarray:
    index = {cell_id: position for position, cell_id in enumerate(ids)}
    display = display_adjacency(ids, candidate.cells, tolerance=contact_tolerance)
    lost = reference.edges - display
    new = display - reference.edges
    points = candidate.points
    forces = np.zeros_like(points)
    nearest = []
    for i, point in enumerate(points):
        distances = np.linalg.norm(points - point, axis=1)
        distances[i] = np.inf
        nearest.append(float(np.min(distances)))
    scale = max(float(np.median(nearest)), .015)
    # Set iteration follows Python's randomized hash order.  Sorting is
    # essential here because floating-point force accumulation can otherwise
    # select a different later candidate under the same declared RNG seed.
    for left, right in sorted(lost):
        a, b = index[left], index[right]
        vector = points[b] - points[a]
        distance = max(float(np.linalg.norm(vector)), 1e-12)
        unit = vector / distance
        magnitude = min(distance / scale, 2.5)
        forces[a] += magnitude * unit; forces[b] -= magnitude * unit
    for left, right in sorted(new):
        a, b = index[left], index[right]
        vector = points[b] - points[a]
        distance = max(float(np.linalg.norm(vector)), 1e-12)
        unit = vector / distance
        magnitude = min(scale / distance, 2.0)
        forces[a] -= .42 * magnitude * unit; forces[b] += .42 * magnitude * unit
    norms = np.linalg.norm(forces, axis=1)
    active = norms > 1e-12
    forces[active] /= np.maximum(norms[active, None], 1.0)
    return forces


def refine_final_power_adjacency(
    reference: RegionReference, embedding: TopologyEmbedding, view: str, *, inner: float = .48,
    outer: float = 1.0, power_iterations: int = 4, force_iterations: int = 5,
    objective_weights: dict[str, float] | None = None,
    candidate_schedule: list[str] | None = None, contact_tolerance: float = 2e-5,
) -> GeometryResult:
    """Multi-start refinement scored only on the final balanced Power cells.

    Unlike the slot objective, every accepted candidate is reconstructed as a
    complete Power partition and its adjacency is recomputed from the final
    polygons.  The candidate schedule is deterministic and outcome-independent.
    """
    objective_weights = objective_weights or {}
    ids = embedding.cell_ids
    topology = topology_seed_positions(embedding, reference, view, inner, outer)
    harmonic = harmonic_seed_positions(reference, view, inner, outer)
    geographic = _geographic_positions(reference, view, inner, outer)
    candidates = {
        "topology": topology,
        "harmonic": harmonic,
        "geographic": geographic,
        "topology_harmonic_50": .5 * topology + .5 * harmonic,
        "topology_geographic_50": .5 * topology + .5 * geographic,
    }
    schedule = candidate_schedule or list(candidates)
    unknown = [label for label in schedule if label not in candidates]
    if unknown:
        raise ValueError(f"Unknown final-Power candidate labels: {unknown}")
    if "topology" not in schedule:
        raise ValueError("candidate_schedule must include the topology start")
    starts = [(label, candidates[label]) for label in schedule]
    evaluated = [
        _score_candidate(reference, ids, points, view, inner, outer, power_iterations, objective_weights,
                         label, contact_tolerance)
        for label, points in starts
    ]
    best = max(evaluated, key=lambda candidate: candidate.score)
    initial = next(candidate for candidate in evaluated if candidate.label == "topology")
    anchor = best.points.copy()
    for iteration in range(force_iterations):
        step = .035 * (1.0 - .72 * iteration / max(force_iterations - 1, 1))
        forces = _topology_forces(best, reference, ids, contact_tolerance)
        trial_points = best.points + step * forces + .06 * (anchor - best.points)
        trial = _score_candidate(reference, ids, trial_points, view, inner, outer, power_iterations,
                                 objective_weights, f"force_{iteration + 1}", contact_tolerance)
        evaluated.append(trial)
        if trial.score > best.score + 1e-10:
            best = trial
        else:
            anchor = .85 * anchor + .15 * best.points
    method = "GeoDisk-Final" if view == "disk" else "GeoAnnulus-Final"
    return GeometryResult(method, view, ids, best.cells, circular_domain(view, inner, outer), {
        "optimization_target": "final_balanced_power_polygon_adjacency",
        "contact_tolerance": contact_tolerance,
        "objective_weights": dict(objective_weights),
        "power_iterations": power_iterations,
        "force_iterations": force_iterations,
        "candidate_schedule": [candidate.label for candidate in evaluated],
        "selected_candidate": best.label,
        "initial_final_power_objective": initial.score,
        "optimized_final_power_objective": best.score,
        "initial_final_power_adj_f1": initial.metrics["adj_f1"],
        "optimized_final_power_adj_f1": best.metrics["adj_f1"],
        "optimized_final_power_np2": best.metrics["np2"],
        "area_cv": best.area_cv,
        "weight_range": [float(best.weights.min()), float(best.weights.max())],
        "candidate_history": [
            {"candidate": candidate.label, "objective": candidate.score, "adj_f1": candidate.metrics["adj_f1"],
             "np2": candidate.metrics["np2"], "area_cv": candidate.area_cv}
            for candidate in evaluated
        ],
    })
