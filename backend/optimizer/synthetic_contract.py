"""Strict synthetic-only contract adapter for GATE 3.

IMPORTANT: This is NOT the teammate 2 /simulate adapter or teammate 3 calibration.
A synthetic fixture has to opt in explicitly. No real measured or calibrated data
is accepted until its real signed-off contract has been inspected.
"""
from __future__ import annotations

import math
from typing import Any

from pydantic import ValidationError

from .core import OptimizeRequest, _within_floor


class SyntheticContractError(ValueError):
    """Invalid or unverified synthetic RSSI integration payload."""


GRID_KEYS = {
    "schema", "source", "frequencyGHz", "routerPosition", "originXZ",
    "gridStepM", "values", "sampling",
}
ENVELOPE_KEYS = {
    "schema", "synthetic", "floor", "lanPort", "priorityGrid",
    "candidates", "current",
}


def _object(raw: Any, label: str) -> dict:
    if not isinstance(raw, dict):
        raise SyntheticContractError(f"{label} must be an object")
    return raw


def _exact_keys(obj: dict, required: set[str], optional: set[str], label: str) -> None:
    missing = required - set(obj)
    extra = set(obj) - required - optional
    if missing or extra:
        raise SyntheticContractError(
            f"{label} fields invalid: missing={sorted(missing)}, unexpected={sorted(extra)}"
        )


def _number(raw: Any, label: str) -> float:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise SyntheticContractError(f"{label} must be a finite number")
    val = float(raw)
    if not math.isfinite(val):
        raise SyntheticContractError(f"{label} must be finite")
    return val


def _parse_position(raw: Any) -> dict:
    position = _object(raw, "routerPosition")
    _exact_keys(position, {"x", "z", "y"}, set(), "routerPosition")
    return {axis: _number(position[axis], f"routerPosition.{axis}")
            for axis in ("x", "z", "y")}


def _parse_grid(raw: Any) -> dict:
    grid = _object(raw, "prediction grid")
    _exact_keys(grid, GRID_KEYS, {"correction"}, "prediction grid")
    if grid["schema"] != "synthetic-grid-v1" or grid["source"] != "synthetic-fixture":
        raise SyntheticContractError("Only explicitly synthetic-grid-v1 fixtures are supported")
    if grid["sampling"] != "cell-center":
        raise SyntheticContractError("Only explicit cell-center sampling is supported")
    band = _number(grid["frequencyGHz"], "frequencyGHz")
    if band not in (2.4, 5.0):
        raise SyntheticContractError("frequencyGHz must be 2.4 or 5")
    origin = grid["originXZ"]
    if not isinstance(origin, list) or len(origin) != 2:
        raise SyntheticContractError("originXZ must be [x,z] in meters")
    ox = _number(origin[0], "originXZ.x")
    oz = _number(origin[1], "originXZ.z")
    step = _number(grid["gridStepM"], "gridStepM")
    if not (0 < step <= 10):
        raise SyntheticContractError("gridStepM must be within (0,10] meters")
    raw_rows = grid["values"]
    if not isinstance(raw_rows, list) or not raw_rows or len(raw_rows) > 128:
        raise SyntheticContractError("values must be a nonempty row-major matrix")
    if not isinstance(raw_rows[0], list) or not raw_rows[0]:
        raise SyntheticContractError("values rows must be nonempty arrays")
    cols = len(raw_rows[0])
    if cols > 128 or cols * len(raw_rows) > 512:
        raise SyntheticContractError("grid cells exceed optimizer probe limit (512)")
    values = []
    for iz, row in enumerate(raw_rows):
        if not isinstance(row, list) or len(row) != cols:
            raise SyntheticContractError("RSSI values must be a rectangular row-major matrix")
        converted = []
        for ix, value in enumerate(row):
            dbm = _number(value, f"values[{iz}][{ix}]")
            if not -150 <= dbm <= 30:
                raise SyntheticContractError("RSSI must be in [-150,30] dBm")
            converted.append(dbm)
        values.append(converted)

    correction = grid.get("correction")
    if correction is not None:
        obj = _object(correction, "correction")
        _exact_keys(obj, {"status", "reason"}, set(), "correction")
        if obj["status"] != "unavailable" or not isinstance(obj["reason"], str) or not obj["reason"].strip():
            raise SyntheticContractError(
                "Synthetic adapter cannot accept applied/unknown/malformed calibration; "
                "real teammate-3 contract is not confirmed"
            )
    return {
        "position": _parse_position(grid["routerPosition"]),
        "frequencyGHz": band,
        "originXZ": (ox, oz),
        "gridStepM": step,
        "values": values,
        "rows": len(values), "cols": cols,
        "correctionStatus": "unavailable",
    }


def _parse_priority(raw: Any, rows: int, cols: int) -> list[list[int]]:
    if not isinstance(raw, list) or len(raw) != rows:
        raise SyntheticContractError("priorityGrid row count does not match RSSI matrix")
    out = []
    for row in raw:
        if not isinstance(row, list) or len(row) != cols:
            raise SyntheticContractError("priorityGrid column count does not match RSSI matrix")
        if any(type(v) is not int or v not in (-100, 0, 100) for v in row):
            raise SyntheticContractError("priorityGrid must contain only -100, 0, 100")
        out.append(row)
    if all(v == -100 for row in out for v in row):
        raise SyntheticContractError("all probes have zero evaluation weight")
    return out


def prepare_synthetic_optimizer_request(
    payload: dict, *, require_calibrated: bool = False
) -> dict:
    """Build a validated /optimize JSON request from explicit synthetic grids only.

    Contract assumption is deliberately test-only: values[row z][column x],
    with a cell centered at origin + (index + 0.5)*gridStepM.
    Never infer the real /simulate schema or apply invented RSSI calibration.
    """
    env = _object(payload, "envelope")
    _exact_keys(env, ENVELOPE_KEYS - {"current"}, {"current"}, "envelope")
    if env["schema"] != "synthetic-integration-v1" or env["synthetic"] is not True:
        raise SyntheticContractError("Only explicitly flagged synthetic-integration-v1 is accepted")

    if require_calibrated:
        raise SyntheticContractError(
            "Real calibration is unavailable: teammate-3 output contract has not been verified"
        )

    raw_candidates = env["candidates"]
    if not isinstance(raw_candidates, list) or not 1 <= len(raw_candidates) <= 250:
        raise SyntheticContractError("candidates must contain between 1 and 250 synthetic grids")
    candidates = [_parse_grid(item) for item in raw_candidates]
    current = _parse_grid(env["current"]) if env.get("current") is not None else None
    reference = candidates[0]

    def assert_matching(other: dict) -> None:
        for key in ("frequencyGHz", "originXZ", "gridStepM", "rows", "cols"):
            if other[key] != reference[key]:
                raise SyntheticContractError(
                    f"prediction grids disagree on {key}; no resampling/axis guessing"
                )

    for grid in candidates[1:]:
        assert_matching(grid)
    if current is not None:
        assert_matching(current)
    priorities = _parse_priority(env["priorityGrid"], reference["rows"], reference["cols"])

    ox, oz = reference["originXZ"]
    step = reference["gridStepM"]
    probes = [
        {
            "x": round(ox + (ix + 0.5) * step, 8),
            "z": round(oz + (iz + 0.5) * step, 8),
            "priorityPct": priorities[iz][ix],
            "targetDbm": -67,  # A synthetic TEST criterion, not a team-approved threshold
        }
        for iz in range(reference["rows"])
        for ix in range(reference["cols"])
    ]

    def prediction(grid: dict) -> dict:
        return {
            "position": grid["position"],
            "rssisDbm": [dbm for row in grid["values"] for dbm in row],
        }

    positions = [tuple(g["position"][axis] for axis in ("x", "z", "y"))
                 for g in candidates]
    if len(positions) != len(set(positions)):
        raise SyntheticContractError("duplicate candidate positions are not supported")

    body = {
        "floor": env["floor"],
        "lanPort": env["lanPort"],
        "probes": probes,
        "candidates": [prediction(g) for g in candidates],
        "current": prediction(current) if current is not None else None,
    }
    try:
        validated = OptimizeRequest.model_validate(body)
    except (ValidationError, ValueError) as exc:
        raise SyntheticContractError(f"optimizer request invalid: {exc}") from exc

    if any(not _within_floor(validated.floor, p.x, p.z) for p in validated.probes):
        raise SyntheticContractError("a synthetic RSSI probe lies outside the floor footprint")

    return {
        "optimizeRequest": validated.model_dump(exclude_none=False),
        "provenance": {
            "testOnly": True,
            "signalSource": "synthetic-fixture",
            "calibrationStatus": "unavailable",
            "frequencyGHz": reference["frequencyGHz"],
            "plane": "XZ",
            "heightAxis": "Y",
            "rowAxis": "Z",
            "columnAxis": "X",
            "sampleLocation": "cell-center",
            "verifiedTeamContracts": False,
        },
    }
