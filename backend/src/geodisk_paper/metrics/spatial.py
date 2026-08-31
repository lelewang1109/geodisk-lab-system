from __future__ import annotations

from collections import deque
import math
from typing import Mapping

import numpy as np
from scipy.stats import spearmanr


def adjacency_scores(reference: set[tuple[str, str]], display: set[tuple[str, str]]) -> dict[str, float]:
    common = reference & display
    precision = len(common) / len(display) if display else (1.0 if not reference else 0.0)
    recall = len(common) / len(reference) if reference else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "adj_precision": float(precision), "adj_recall": float(recall), "adj_f1": float(f1),
        "original_edge_count": len(reference), "display_edge_count": len(display),
        "preserved_edge_count": len(common), "lost_edge_count": len(reference - display),
        "new_edge_count": len(display - reference),
    }


def _within_k(nodes: list[str], edges: set[tuple[str, str]], k: int) -> dict[str, set[str]]:
    graph = {node: set() for node in nodes}
    for left, right in edges:
        if left in graph and right in graph:
            graph[left].add(right)
            graph[right].add(left)
    output = {}
    for start in nodes:
        seen = {start: 0}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            if seen[current] >= k:
                continue
            for nxt in graph[current]:
                if nxt not in seen:
                    seen[nxt] = seen[current] + 1
                    queue.append(nxt)
        output[start] = set(seen) - {start}
    return output


def neighborhood_preservation(nodes: list[str], reference: set[tuple[str, str]], display: set[tuple[str, str]], k: int = 2) -> float:
    original = _within_k(nodes, reference, k)
    mapped = _within_k(nodes, display, k)
    values = []
    for node in nodes:
        union = original[node] | mapped[node]
        values.append(len(original[node] & mapped[node]) / len(union) if union else 1.0)
    return float(np.mean(values)) if values else float("nan")


def weighted_adjacency_scores(
    reference: Mapping[tuple[str, str], float],
    display: Mapping[tuple[str, str], float],
) -> dict[str, float]:
    """Score adjacency while weighting each edge by its shared boundary.

    Precision weights preserved edges by displayed boundary length, recall by
    original boundary length.  ``weighted_edge_overlap`` additionally compares
    the normalized boundary-length distributions using histogram intersection.
    """
    reference = {tuple(sorted(edge)): max(float(value), 0.0) for edge, value in reference.items()}
    display = {tuple(sorted(edge)): max(float(value), 0.0) for edge, value in display.items()}
    common = set(reference) & set(display)
    reference_total = sum(reference.values())
    display_total = sum(display.values())
    precision = sum(display[edge] for edge in common) / display_total if display_total else (1.0 if not reference_total else 0.0)
    recall = sum(reference[edge] for edge in common) / reference_total if reference_total else 1.0
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    if reference_total and display_total:
        overlap = sum(min(reference.get(edge, 0.0) / reference_total, display.get(edge, 0.0) / display_total)
                      for edge in set(reference) | set(display))
    else:
        overlap = 1.0 if not reference_total and not display_total else 0.0
    return {
        "weighted_adj_precision": float(precision),
        "weighted_adj_recall": float(recall),
        "weighted_adj_f1": float(f1),
        "weighted_edge_overlap": float(overlap),
        "reference_internal_boundary": float(reference_total),
        "display_internal_boundary": float(display_total),
    }


def circular_difference_radians(left: float, right: float) -> float:
    return abs(math.atan2(math.sin(left - right), math.cos(left - right)))


def local_direction_error_deg(
    reference_edges: set[tuple[str, str]],
    original_centroids: Mapping[str, tuple[float, float]],
    display_centroids: Mapping[str, tuple[float, float]],
    reference_latitude: float,
) -> float:
    values = []
    cosine = math.cos(math.radians(reference_latitude))
    for left, right in reference_edges:
        lon1, lat1 = original_centroids[left]
        lon2, lat2 = original_centroids[right]
        original = math.atan2(lat2 - lat1, (lon2 - lon1) * cosine)
        x1, y1 = display_centroids[left]
        x2, y2 = display_centroids[right]
        displayed = math.atan2(y2 - y1, x2 - x1)
        values.append(math.degrees(circular_difference_radians(original, displayed)))
    return float(np.mean(values)) if values else float("nan")


def angular_error_deg(original_theta: Mapping[str, float], display_centroids: Mapping[str, tuple[float, float]]) -> float:
    values = []
    for cell_id, theta in original_theta.items():
        x, y = display_centroids[cell_id]
        values.append(math.degrees(circular_difference_radians(math.atan2(y, x), theta)))
    return float(np.mean(values)) if values else float("nan")


def radial_spearman(original_rho: Mapping[str, float], display_centroids: Mapping[str, tuple[float, float]]) -> float:
    ids = list(original_rho)
    source = [original_rho[cell_id] for cell_id in ids]
    target = [math.hypot(*display_centroids[cell_id]) for cell_id in ids]
    if len(ids) < 3 or np.std(source) < 1e-12 or np.std(target) < 1e-12:
        return float("nan")
    return float(spearmanr(source, target).statistic)


def node_level_fidelity(
    cell_ids: list[str], reference_edges: set[tuple[str, str]], display_edges: set[tuple[str, str]],
    original_centroids: Mapping[str, tuple[float, float]], display_centroids: Mapping[str, tuple[float, float]],
    original_theta: Mapping[str, float], original_rho: Mapping[str, float], reference_latitude: float,
    is_boundary: Mapping[str, bool],
) -> list[dict[str, float | str | bool]]:
    """Return per-cell topology and positional errors for error decomposition."""
    reference_graph = {cell_id: set() for cell_id in cell_ids}
    display_graph = {cell_id: set() for cell_id in cell_ids}
    for left, right in reference_edges:
        if left in reference_graph and right in reference_graph:
            reference_graph[left].add(right); reference_graph[right].add(left)
    for left, right in display_edges:
        if left in display_graph and right in display_graph:
            display_graph[left].add(right); display_graph[right].add(left)
    display_radius = {cell_id: math.hypot(*display_centroids[cell_id]) for cell_id in cell_ids}
    source_order = {cell_id: rank / max(len(cell_ids) - 1, 1) for rank, cell_id in enumerate(sorted(cell_ids, key=original_rho.get))}
    target_order = {cell_id: rank / max(len(cell_ids) - 1, 1) for rank, cell_id in enumerate(sorted(cell_ids, key=display_radius.get))}
    cosine = math.cos(math.radians(reference_latitude))
    rows: list[dict[str, float | str | bool]] = []
    for cell_id in cell_ids:
        expected, actual = reference_graph[cell_id], display_graph[cell_id]
        common, union = expected & actual, expected | actual
        precision = len(common) / len(actual) if actual else (1.0 if not expected else 0.0)
        recall = len(common) / len(expected) if expected else 1.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        x, y = display_centroids[cell_id]
        direction_errors = []
        order_matches = []
        lon1, lat1 = original_centroids[cell_id]
        x1, y1 = display_centroids[cell_id]
        for other in expected:
            lon2, lat2 = original_centroids[other]
            x2, y2 = display_centroids[other]
            original = math.atan2(lat2 - lat1, (lon2 - lon1) * cosine)
            displayed = math.atan2(y2 - y1, x2 - x1)
            direction_errors.append(math.degrees(circular_difference_radians(original, displayed)))
        common_neighbors = sorted(common)
        for first_index, first in enumerate(common_neighbors):
            for second in common_neighbors[first_index + 1:]:
                lon_first, lat_first = original_centroids[first]
                lon_second, lat_second = original_centroids[second]
                source_cross = ((lon_first - lon1) * cosine) * (lat_second - lat1) - (lat_first - lat1) * ((lon_second - lon1) * cosine)
                x_first, y_first = display_centroids[first]
                x_second, y_second = display_centroids[second]
                display_cross = (x_first - x1) * (y_second - y1) - (y_first - y1) * (x_second - x1)
                if abs(source_cross) > 1e-12 and abs(display_cross) > 1e-12:
                    order_matches.append(float(np.sign(source_cross) == np.sign(display_cross)))
        rows.append({
            "cell_id": cell_id,
            "is_boundary": bool(is_boundary.get(cell_id, False)),
            "reference_degree": len(expected),
            "display_degree": len(actual),
            "degree_absolute_error": abs(len(expected) - len(actual)),
            "node_adj_precision": float(precision),
            "node_adj_recall": float(recall),
            "node_adj_f1": float(f1),
            "node_neighbor_jaccard": len(common) / len(union) if union else 1.0,
            "node_angular_error_deg": math.degrees(circular_difference_radians(math.atan2(y, x), original_theta[cell_id])),
            "node_radial_rank_error": abs(source_order[cell_id] - target_order[cell_id]),
            "node_direction_error_deg": float(np.mean(direction_errors)) if direction_errors else float("nan"),
            "node_neighbor_order_accuracy": float(np.mean(order_matches)) if order_matches else float("nan"),
        })
    return rows


def evaluate_spatial(
    cell_ids: list[str], reference_edges: set[tuple[str, str]], display_edges: set[tuple[str, str]],
    original_centroids: Mapping[str, tuple[float, float]], display_centroids: Mapping[str, tuple[float, float]],
    original_theta: Mapping[str, float], original_rho: Mapping[str, float], reference_latitude: float,
) -> dict[str, float]:
    return {
        **adjacency_scores(reference_edges, display_edges),
        "np2": neighborhood_preservation(cell_ids, reference_edges, display_edges, 2),
        "np3": neighborhood_preservation(cell_ids, reference_edges, display_edges, 3),
        "local_direction_error_deg": local_direction_error_deg(reference_edges, original_centroids, display_centroids, reference_latitude),
        "angular_error_deg": angular_error_deg(original_theta, display_centroids),
        "radial_spearman": radial_spearman(original_rho, display_centroids),
    }
