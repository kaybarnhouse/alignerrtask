import json
import math
import sys
from pathlib import Path

# Deterministic score in [0, 1]
# Expected input:
# - a JSON file path may be provided as argv[1], containing the candidate configuration
# - otherwise, read JSON from stdin
#
# Expected fields:
# {
#   "flap_deflection": float,
#   "hinge_gap": float,
#   "chord_fraction": float,
#   "blend_radius": float
# }
#
# Scoring logic:
# - reward lower drag proxy
# - penalize constraint violations
# - penalize infeasible geometry
#
# NOTE: Replace the proxy model below with the ground-truth evaluator when ready.

BOUNDS = {
    "flap_deflection": (-20.0, 20.0),
    "hinge_gap": (0.0, 0.02),
    "chord_fraction": (0.05, 0.25),
    "blend_radius": (0.0, 0.05),
}


def load_candidate():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return json.load(sys.stdin)


def clamp01(x):
    return max(0.0, min(1.0, x))


def score_candidate(x):
    # Basic validation
    for k in BOUNDS:
        if k not in x:
            return 0.0

    vals = {k: float(x[k]) for k in BOUNDS}

    # Hard bounds check
    for k, (lo, hi) in BOUNDS.items():
        if not (lo <= vals[k] <= hi):
            return 0.0

    # Smooth proxy for drag: lower is better
    # Minimum near a modest negative flap deflection and moderate chord fraction.
    defl = vals["flap_deflection"]
    gap = vals["hinge_gap"]
    chord = vals["chord_fraction"]
    blend = vals["blend_radius"]

    # Proxy objective with a known optimum region
    drag_proxy = (
        0.012 * (defl + 6.0) ** 2
        + 180.0 * (gap - 0.004) ** 2
        + 55.0 * (chord - 0.14) ** 2
        + 260.0 * (blend - 0.018) ** 2
    )

    # Geometric feasibility penalties
    feasibility_penalty = 0.0
    if chord < 0.08:
        feasibility_penalty += (0.08 - chord) * 8.0
    if blend > 0.03 and gap < 0.002:
        feasibility_penalty += 0.5
    if abs(defl) > 18.0:
        feasibility_penalty += 0.3

    total = drag_proxy + feasibility_penalty

    # Convert to [0,1], best near 1.0
    score = math.exp(-total)
    return clamp01(score)


def main():
    try:
        candidate = load_candidate()
        score = score_candidate(candidate)
    except Exception:
        score = 0.0

    print(json.dumps({"score": score}))


if __name__ == "__main__":
    main()
