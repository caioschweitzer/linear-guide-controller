"""Utilities for aggregating and normalizing multi-curve open-loop step responses."""

import math
from typing import Any, Dict, List, Sequence


def compute_sine_setpoint(
    elapsed_s: float,
    center_mm: float,
    amplitude_mm: float,
    freq_hz: float,
    min_mm: float = 0.0,
    max_mm: float = 670.0,
) -> float:
    """Compute a clamped sinusoidal position setpoint (mm) for closed-loop tracking."""
    raw = float(center_mm) + float(amplitude_mm) * math.sin(2.0 * math.pi * float(freq_hz) * float(elapsed_s))
    return max(min_mm, min(max_mm, raw))


def compute_normalized_curve(
    curves: Sequence[Sequence[Dict[str, Any]]],
    duty_pct: float = 100.0,
) -> List[Dict[str, Any]]:
    """
    Align N collected open-loop curves by sample index (up to the shortest curve),
    compute point-wise mean position and velocity, and normalize both to [0.0, 1.0].

    Returns a list of dicts with keys:
      time_s, position_mean_mm, velocity_mean_mm_s,
      position_norm, velocity_norm, duty_pct, curve_count
    """
    non_empty = [c for c in curves if c]
    if not non_empty:
        return []

    curve_count = len(non_empty)
    min_len = min(len(c) for c in non_empty)

    mean_positions: List[float] = []
    mean_velocities: List[float] = []
    times: List[float] = []

    for i in range(min_len):
        t_avg = sum(float(c[i]["time_s"]) for c in non_empty) / curve_count
        p_avg = sum(float(c[i]["position_mm"]) for c in non_empty) / curve_count
        v_avg = sum(float(c[i]["velocity_mm_s"]) for c in non_empty) / curve_count
        times.append(t_avg)
        mean_positions.append(p_avg)
        mean_velocities.append(v_avg)

    pos_min = min(mean_positions)
    pos_max = max(mean_positions)
    pos_span = pos_max - pos_min

    vel_min = min(mean_velocities)
    vel_max = max(mean_velocities)
    vel_span = vel_max - vel_min

    duty_rounded = round(float(duty_pct), 2)
    result: List[Dict[str, Any]] = []
    for t, p, v in zip(times, mean_positions, mean_velocities):
        p_norm = (p - pos_min) / pos_span if pos_span > 1e-9 else 0.0
        v_norm = (v - vel_min) / vel_span if vel_span > 1e-9 else 0.0
        result.append({
            "time_s": round(t, 3),
            "position_mean_mm": round(p, 3),
            "velocity_mean_mm_s": round(v, 3),
            "position_norm": round(p_norm, 6),
            "velocity_norm": round(v_norm, 6),
            "duty_pct": duty_rounded,
            "curve_count": curve_count,
        })

    return result
