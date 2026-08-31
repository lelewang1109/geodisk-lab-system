from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np
from shapely.geometry import Polygon

from geodisk_paper.data.regions import RegionReference
from geodisk_paper.metrics.spatial import evaluate_spatial

TAU = 2 * math.pi


@dataclass(frozen=True)
class Slot:
    index: int
    layer: int
    position: int
    theta_center: float
    theta_left: float
    theta_right: float
    r_inner: float
    r_outer: float


@dataclass
class TopologyEmbedding:
    cell_ids: list[str]
    slots: list[Slot]
    slot_edges: set[tuple[int, int]]
    initial_assignment: np.ndarray
    assignment: np.ndarray
    initial_objective: float
    final_objective: float
    layer_count: int


def _seam(theta: np.ndarray) -> float:
    values = np.sort(np.mod(theta, TAU))
    gaps = np.diff(np.r_[values, values[0] + TAU])
    index = int(np.argmax(gaps))
    return float((values[index] + gaps[index] / 2) % TAU)


def _slot_edges(slots: list[Slot]) -> set[tuple[int, int]]:
    by_layer: dict[int, list[Slot]] = {}
    for slot in slots:
        by_layer.setdefault(slot.layer, []).append(slot)
    edges = set()
    for same_layer in by_layer.values():
        same_layer.sort(key=lambda item: item.position)
        if len(same_layer) > 1:
            for index, slot in enumerate(same_layer):
                other = same_layer[(index + 1) % len(same_layer)]
                edges.add(tuple(sorted((slot.index, other.index))))
    for layer in sorted(by_layer):
        if layer + 1 not in by_layer:
            continue
        for left in by_layer[layer]:
            for right in by_layer[layer + 1]:
                overlap = min(left.theta_right, right.theta_right) - max(left.theta_left, right.theta_left)
                if overlap > 1e-10:
                    edges.add(tuple(sorted((left.index, right.index))))
    return edges


def _display_edges(slot_edges: set[tuple[int, int]], assignment: np.ndarray, ids: list[str]) -> set[tuple[str, str]]:
    return {
        tuple(sorted((ids[int(assignment[left])], ids[int(assignment[right])])))
        for left, right in slot_edges if assignment[left] != assignment[right]
    }


def _slot_centroids(slots: list[Slot], assignment: np.ndarray, ids: list[str]) -> dict[str, tuple[float, float]]:
    result = {}
    for slot in slots:
        radius = (2.0 / 3.0) * (slot.r_outer**3 - slot.r_inner**3) / max(slot.r_outer**2 - slot.r_inner**2, 1e-12)
        theta = slot.theta_center
        result[ids[int(assignment[slot.index])]] = (radius * math.cos(theta), radius * math.sin(theta))
    return result


def _objective(reference: RegionReference, slots, slot_edges, assignment, ids, weights) -> float:
    display_edges = _display_edges(slot_edges, assignment, ids)
    display_centroids = _slot_centroids(slots, assignment, ids)
    source_centroids = {str(r.cell_id): (float(r.longitude), float(r.latitude)) for r in reference.cells.itertuples()}
    theta = {str(r.cell_id): float(r.theta) for r in reference.cells.itertuples()}
    rho = {str(r.cell_id): float(r.rho) for r in reference.cells.itertuples()}
    values = evaluate_spatial(ids, reference.edges, display_edges, source_centroids, display_centroids, theta, rho, reference.anchor[1])
    radial = values["radial_spearman"] if np.isfinite(values["radial_spearman"]) else -1.0
    return float(
        weights.get("adjacency", 1.0) * values["adj_f1"]
        + weights.get("neighborhood", 0.0) * values["np2"]
        - weights.get("angular", 0.0) * values["angular_error_deg"] / 180.0
        - weights.get("local_direction", 0.0) * values["local_direction_error_deg"] / 180.0
        - weights.get("radial", 0.0) * (1.0 - radial) / 2.0
    )


def build_topology_embedding(
    reference: RegionReference, *, layer_count: int, optimize_passes: int, seed: int,
    weights: dict[str, float], radial_constraint: bool = True, search_mode: str = "adjacent",
    candidate_budget: int = 0,
) -> TopologyEmbedding:
    frame = reference.cells.reset_index(drop=True)
    ids = frame.cell_id.astype(str).tolist()
    theta = frame.theta.to_numpy(float)
    rho = frame.rho.to_numpy(float)
    if radial_constraint:
        quantiles = np.quantile(rho, np.linspace(0, 1, layer_count + 1))
        quantiles[0] -= 1e-9
        quantiles[-1] += 1e-9
        layers = np.clip(np.searchsorted(quantiles, rho, side="right") - 1, 0, layer_count - 1)
    else:
        angular_order = np.argsort(np.mod(theta, TAU))
        layers = np.empty(len(ids), int)
        layers[angular_order] = np.arange(len(ids)) % layer_count
    counts = np.asarray([(layers == layer).sum() for layer in range(layer_count)], int)
    cumulative = np.r_[0, np.cumsum(counts)] / max(len(ids), 1)
    radial_edges = np.sqrt(cumulative)
    radial_edges[0], radial_edges[-1] = 0.0, 1.0
    seam = _seam(theta)
    slots, assignment = [], []
    slot_index = 0
    for layer in range(layer_count):
        indices = np.flatnonzero(layers == layer)
        if not len(indices):
            continue
        unwrapped = seam + np.mod(theta[indices] - seam, TAU)
        order = indices[np.argsort(unwrapped)]
        centers = np.sort(unwrapped)
        boundaries = np.empty(len(order) + 1)
        boundaries[0], boundaries[-1] = seam, seam + TAU
        if len(order) > 1:
            boundaries[1:-1] = 0.5 * (centers[:-1] + centers[1:])
        for position, cell_index in enumerate(order):
            slots.append(Slot(slot_index, layer, position, float(centers[position]),
                              float(boundaries[position]), float(boundaries[position + 1]),
                              float(radial_edges[layer]), float(radial_edges[layer + 1])))
            assignment.append(int(cell_index))
            slot_index += 1
    assignment = np.asarray(assignment, int)
    edges = _slot_edges(slots)
    initial = assignment.copy()
    current = _objective(reference, slots, edges, assignment, ids, weights)
    initial_objective = current
    by_layer: dict[int, list[int]] = {}
    for slot in slots:
        by_layer.setdefault(slot.layer, []).append(slot.index)
    rng = np.random.default_rng(seed)
    for _ in range(optimize_passes):
        improved = False
        layer_order = list(by_layer)
        rng.shuffle(layer_order)
        for layer in layer_order:
            indexes = by_layer[layer]
            pairs = [(indexes[k], indexes[k + 1]) for k in range(len(indexes) - 1)]
            if len(indexes) > 2:
                pairs.append((indexes[-1], indexes[0]))
            rng.shuffle(pairs)
            for left, right in pairs:
                trial = assignment.copy()
                trial[left], trial[right] = trial[right], trial[left]
                score = _objective(reference, slots, edges, trial, ids, weights)
                if score > current + 1e-10:
                    assignment, current, improved = trial, score, True
        if search_mode in {"expanded", "expanded_cross"}:
            candidates = []
            for indexes in by_layer.values():
                budget = max(len(indexes) * 2, 1)
                for _candidate in range(budget):
                    if len(indexes) >= 2:
                        pair = rng.choice(indexes, size=2, replace=False)
                        candidates.append((int(pair[0]), int(pair[1])))
            if search_mode == "expanded_cross":
                for layer in range(layer_count - 1):
                    left_slots = by_layer.get(layer, []); right_slots = by_layer.get(layer + 1, [])
                    if not left_slots or not right_slots:
                        continue
                    for left in left_slots:
                        right = min(right_slots, key=lambda index: abs(slots[index].theta_center - slots[left].theta_center))
                        candidates.append((left, right))
            rng.shuffle(candidates)
            if candidate_budget > 0:
                candidates = candidates[:candidate_budget]
            for left, right in candidates:
                trial = assignment.copy(); trial[left], trial[right] = trial[right], trial[left]
                score = _objective(reference, slots, edges, trial, ids, weights)
                if score > current + 1e-10:
                    assignment, current, improved = trial, score, True
        if not improved:
            break
    return TopologyEmbedding(ids, slots, edges, initial, assignment, initial_objective, current, layer_count)


def sector_polygon(r0: float, r1: float, a0: float, a1: float, samples: int = 12) -> Polygon:
    outside = np.column_stack([r1*np.cos(np.linspace(a0, a1, samples)), r1*np.sin(np.linspace(a0, a1, samples))])
    if r0 <= 1e-12:
        points = np.vstack([outside, [[0.0, 0.0]]])
    else:
        inside = np.column_stack([r0*np.cos(np.linspace(a1, a0, samples)), r0*np.sin(np.linspace(a1, a0, samples))])
        points = np.vstack([outside, inside])
    return Polygon(points)


def regular_polygons(embedding: TopologyEmbedding, view: str, inner: float = .48, outer: float = 1.0) -> dict[str, Polygon]:
    result = {}
    for slot in embedding.slots:
        cell_id = embedding.cell_ids[int(embedding.assignment[slot.index])]
        if view == "disk":
            r0, r1 = slot.r_inner, slot.r_outer
        else:
            r0 = inner + slot.r_inner * (outer - inner)
            r1 = inner + slot.r_outer * (outer - inner)
        result[cell_id] = sector_polygon(r0, r1, slot.theta_left, slot.theta_right)
    return result


def topology_seed_positions(embedding: TopologyEmbedding, reference: RegionReference, view: str, inner: float = .48, outer: float = 1.0) -> np.ndarray:
    source_rho = {str(r.cell_id): float(r.rho) for r in reference.cells.itertuples()}
    positions = np.zeros((len(embedding.cell_ids), 2), float)
    for slot in embedding.slots:
        cell_index = int(embedding.assignment[slot.index])
        cell_id = embedding.cell_ids[cell_index]
        if view == "disk":
            r0, r1 = slot.r_inner, slot.r_outer
        else:
            r0 = inner + slot.r_inner * (outer - inner)
            r1 = inner + slot.r_outer * (outer - inner)
        midpoint = .5 * (r0 + r1)
        spread = r1 - r0
        jitter = .08 * spread * (source_rho[cell_id] - .5)
        radius = float(np.clip(midpoint + jitter, r0 + .06*spread, r1 - .06*spread))
        theta = slot.theta_center
        positions[cell_index] = (radius * math.cos(theta), radius * math.sin(theta))
    return positions
