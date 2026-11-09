"""UNVERIFIED synthetic-only handoff adapter, NOT the real team 2/3 API.

Explicit XZ geometry and cell-centre sampling. Unknown contracts fail closed:
no interpolation, inferred axis names, synthetic RSSI generation, or fallback
when a synthetic calibration fails. Keep this independent of the v1.6 UI.
"""
from __future__ import annotations

import math
from typing import Literal

from pydantic import Field, model_validator

from .core import Position, Prediction, StrictModel


class OriginXZ(StrictModel):
    x: float
    z: float


class SamplePoint(StrictModel):
    x: float
    z: float
    y: float = Field(ge=0)


class SyntheticGridFrame(StrictModel):
    schemaVersion: Literal["synthetic-grid-v1"]
    contractStatus: Literal["UNVERIFIED_SYNTHETIC"]
    isSynthetic: Literal[True]
    coordinateSystem: Literal["XZ"]
    verticalAxis: Literal["Y"]
    rowAxis: Literal["Z"]
    columnAxis: Literal["X"]
    cellAnchor: Literal["center"]
    originXZ: OriginXZ
    gridStepM: float = Field(gt=0, le=10)
    receiverY: float = Field(ge=0, le=10)
    frequencyGHz: Literal[2.4, 5.0]
    routerPosition: Position
    values: list[list[float]] = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_grid(self):
        cols = len(self.values[0])
        if not cols or cols > 128:
            raise ValueError("grid column count must be 1..128")
        for row in self.values:
            if len(row) != cols:
                raise ValueError("grid must be rectangular, not ragged")
            for v in row:
                if not math.isfinite(v) or not (-150 <= v <= 30):
                    raise ValueError("synthetic RSSI must be finite and -150..30 dBm")
        return self


class SyntheticCalibration(StrictModel):
    schemaVersion: Literal["synthetic-calibration-v1"]
    contractStatus: Literal["UNVERIFIED_SYNTHETIC"]
    isSynthetic: Literal[True]
    status: Literal["missing", "provided", "failed"]
    frequencyGHz: Literal[2.4, 5.0]
    routerPosition: Position
    probeCells: list[tuple[int, int]] | None = None  # [row Z, col X]
    correctedRssiDbm: list[float] | None = None
    errorCode: str | None = None

    @model_validator(mode="after")
    def validate_status(self):
        if self.status == "provided":
            if not self.probeCells or not self.correctedRssiDbm:
                raise ValueError("provided synthetic correction requires probeCells and correctedRssiDbm")
            if len(self.probeCells) != len(self.correctedRssiDbm):
                raise ValueError("corrected synthetic RSSI vector must match probeCells")
            if self.errorCode is not None:
                raise ValueError("provided calibration cannot have errorCode")
            for v in self.correctedRssiDbm:
                if not math.isfinite(v) or not (-150 <= v <= 30):
                    raise ValueError("corrected synthetic RSSI must be finite and -150..30 dBm")
        else:
            if self.probeCells is not None or self.correctedRssiDbm is not None:
                raise ValueError("missing/failed calibration cannot contain corrected samples")
            if self.status == "failed" and not self.errorCode:
                raise ValueError("failed calibration requires an errorCode")
            if self.status == "missing" and self.errorCode is not None:
                raise ValueError("missing calibration cannot carry errorCode")
        return self


def _cell_index(frame: SyntheticGridFrame, point: SamplePoint) -> tuple[int, int]:
    """Return (row Z, column X); require explicit cell-centre position."""
    if not math.isclose(point.y, frame.receiverY, abs_tol=1e-6):
        raise ValueError("receiver Y does not match frame receiverY")
    col_f = (point.x - frame.originXZ.x) / frame.gridStepM - 0.5
    row_f = (point.z - frame.originXZ.z) / frame.gridStepM - 0.5
    col, row = round(col_f), round(row_f)
    if not (math.isclose(col_f, col, abs_tol=1e-6) and
            math.isclose(row_f, row, abs_tol=1e-6)):
        raise ValueError("probe must be exactly at a grid cell centre; no implicit interpolation")
    if not (0 <= row < len(frame.values) and 0 <= col < len(frame.values[0])):
        raise ValueError("probe is outside synthetic grid")
    return row, col


def adapt_synthetic_grid(
    frame_data: dict,
    probes_data: list[dict],
    calibration_data: dict | None = None,
    *,
    expected_frequency_ghz: float | None = None,
) -> dict:
    """Adapt a clearly marked SYNTHETIC grid to GATE 2 Prediction format.

    All axes, provenance, units and calibration status are mandatory/validated.
    Returns only caller-supplied grid readings (or provided synthetic corrected
    readings). Does NOT generate or correct RSSI, call /simulate, or assume an
    actual team-2/team-3 API schema.
    """
    frame = SyntheticGridFrame.model_validate(frame_data)
    if expected_frequency_ghz is not None and frame.frequencyGHz != expected_frequency_ghz:
        raise ValueError("frequencyGHz does not match the requested band")
    if not probes_data:
        raise ValueError("at least one probe is required")
    probes = [SamplePoint.model_validate(item) for item in probes_data]
    cells = [_cell_index(frame, probe) for probe in probes]
    readings = [frame.values[row][col] for row, col in cells]
    cal_status = "missing"
    source = "synthetic_grid_unadjusted"
    if calibration_data is not None:
        cal = SyntheticCalibration.model_validate(calibration_data)
        if cal.frequencyGHz != frame.frequencyGHz:
            raise ValueError("calibration frequencyGHz differs from prediction grid")
        if cal.routerPosition != frame.routerPosition:
            raise ValueError("calibration routerPosition differs from prediction grid")
        if cal.status == "failed":
            raise ValueError("synthetic calibration explicitly failed: " + cal.errorCode)
        if cal.status == "provided":
            if [tuple(p) for p in cal.probeCells] != cells:
                raise ValueError("calibration probe cell order does not match prediction probes")
            readings = list(cal.correctedRssiDbm)
            cal_status = "provided_synthetic"
            source = "synthetic_corrected_fixture"
    predicted = Prediction(position=frame.routerPosition, rssisDbm=readings)
    return {
        "prediction": predicted.model_dump(),
        "probeCellsRowZColX": [list(cell) for cell in cells],
        "calibrationStatus": cal_status,
        "signalSource": source,
        "isSynthetic": True,
        "contractStatus": "UNVERIFIED_SYNTHETIC",
    }
