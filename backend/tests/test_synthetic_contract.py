"""Contract tests use explicitly SYNTHETIC data only, not real team RSSI."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from optimizer.api import app
from optimizer.synthetic_contract import (
    SyntheticContractError,
    prepare_synthetic_optimizer_request,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic_gate3_case.json"


def synthetic_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class SyntheticContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = synthetic_fixture()

    def prepare(self, **kwargs) -> dict:
        return prepare_synthetic_optimizer_request(self.payload, **kwargs)

    def fails(self, snippet: str) -> None:
        with self.assertRaises(SyntheticContractError) as caught:
            self.prepare()
        self.assertIn(snippet, str(caught.exception))

    def test_synthetic_provenance_is_explicit(self):
        result = self.prepare()
        self.assertIs(result["provenance"]["testOnly"], True)
        self.assertIs(result["provenance"]["verifiedTeamContracts"], False)
        self.assertEqual(result["provenance"]["signalSource"], "synthetic-fixture")
        self.assertEqual(result["provenance"]["calibrationStatus"], "unavailable")
        self.assertEqual(result["provenance"]["rowAxis"], "Z")
        self.assertEqual(result["provenance"]["columnAxis"], "X")
        self.assertEqual(result["provenance"]["heightAxis"], "Y")

    def test_cell_center_coordinates_map_row_to_z_column_to_x(self):
        req = self.prepare()["optimizeRequest"]
        probes = req["probes"]
        self.assertEqual(len(probes), 6)
        self.assertEqual((probes[0]["x"], probes[0]["z"]), (0.5, 0.5))
        self.assertEqual((probes[1]["x"], probes[1]["z"]), (1.5, 0.5))
        self.assertEqual((probes[2]["x"], probes[2]["z"]), (2.5, 0.5))
        self.assertEqual((probes[3]["x"], probes[3]["z"]), (0.5, 1.5))
        self.assertEqual((probes[5]["x"], probes[5]["z"]), (2.5, 1.5))
        self.assertNotIn("y", probes[0])  # height is a separate physical axis

    def test_rssi_row_major_order_and_router_height_preserved(self):
        req = self.prepare()["optimizeRequest"]
        self.assertEqual(req["candidates"][0]["rssisDbm"], [-55, -59, -69, -60, -65, -72])
        self.assertEqual(req["candidates"][0]["position"], {"x": 1.0, "z": 1.0, "y": 1.2})
        self.assertEqual(req["current"]["rssisDbm"][4], -70)
        self.assertEqual([p["priorityPct"] for p in req["probes"]], [100, 0, -100, 0, 100, 0])

    def test_synthetic_request_reaches_real_optimizer_api(self):
        body = self.prepare()["optimizeRequest"]
        response = TestClient(app).post("/optimize", json=body)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertIn(result["status"], ("ok", "no_feasible_candidate"))
        self.assertEqual(result["signalSource"], "caller_supplied_predictions")

    def test_rejects_real_or_unverified_prediction_source(self):
        self.payload["candidates"][0]["source"] = "team2-live-rssi"
        self.fails("Only explicitly synthetic")
        self.payload["candidates"][0]["source"] = "synthetic-fixture"
        self.payload["candidates"][0]["schema"] = "team2-grid-v1"
        self.fails("Only explicitly synthetic")

    def test_requires_synthetic_envelope_marker(self):
        self.payload["synthetic"] = False
        self.fails("Only explicitly flagged")
        self.payload["synthetic"] = True
        self.payload["schema"] = "live-integration-v1"
        self.fails("Only explicitly flagged")

    def test_rejects_misleading_calibration_claim(self):
        self.payload["candidates"][0]["correction"] = {
            "status": "applied", "reason": "unverified calibration"
        }
        self.fails("cannot accept applied")

    def test_rejects_malformed_calibration_metadata(self):
        self.payload["candidates"][0]["correction"] = {"status": "unavailable"}
        self.fails("fields invalid")
        self.payload["candidates"][0]["correction"] = {"status": "unavailable", "reason": ""}
        self.fails("cannot accept applied")

    def test_missing_calibration_is_explicitly_unavailable(self):
        for grid in self.payload["candidates"]:
            grid.pop("correction", None)
        self.payload["current"].pop("correction", None)
        result = self.prepare()
        self.assertEqual(result["provenance"]["calibrationStatus"], "unavailable")

    def test_requiring_calibration_fails_closed(self):
        self.fails_calibrated()

    def fails_calibrated(self) -> None:
        with self.assertRaisesRegex(SyntheticContractError, "calibration is unavailable"):
            self.prepare(require_calibrated=True)

    def test_rejects_ragged_rssi_matrix(self):
        self.payload["candidates"][0]["values"][1].pop()
        self.fails("rectangular")

    def test_rejects_nan_and_out_of_range_rssi(self):
        self.payload["candidates"][0]["values"][0][0] = float("nan")
        self.fails("finite")
        self.payload["candidates"][0]["values"][0][0] = -175
        self.fails("RSSI must be")
        self.payload["candidates"][0]["values"][0][0] = "-60"
        self.fails("finite number")

    def test_rejects_mismatched_frequency(self):
        self.payload["candidates"][1]["frequencyGHz"] = 2.4
        self.fails("frequencyGHz")

    def test_rejects_mismatched_grid_origin_or_spacing(self):
        self.payload["candidates"][1]["originXZ"] = [1, 0]
        self.fails("originXZ")
        self.payload["candidates"][1]["originXZ"] = [0, 0]
        self.payload["candidates"][1]["gridStepM"] = 0.5
        self.fails("gridStepM")

    def test_rejects_mismatched_current_prediction(self):
        self.payload["current"]["values"].append([-65, -66, -67])
        self.fails("rows")

    def test_rejects_unconfirmed_grid_sampling(self):
        self.payload["candidates"][0]["sampling"] = "grid-nodes"
        self.fails("cell-center")

    def test_rejects_priority_shape_and_unknown_priority(self):
        self.payload["priorityGrid"][0].pop()
        self.fails("column count")
        self.payload["priorityGrid"][0].append(55)
        self.fails("only -100, 0, 100")

    def test_all_low_importance_is_not_silently_scored(self):
        self.payload["priorityGrid"] = [[-100, -100, -100], [-100, -100, -100]]
        self.fails("zero evaluation weight")

    def test_rejects_outside_probe_instead_of_guessing_footprint(self):
        self.payload["floor"]["footprint"] = [
            [0, 0], [4, 0], [4, 1], [1, 1], [1, 3], [0, 3]
        ]
        self.fails("outside the floor footprint")

    def test_outside_candidate_is_filtered_by_optimizer_not_moved_silently(self):
        self.payload["candidates"][0]["routerPosition"]["x"] = -1
        # Preserve original coordinates; the optimizer itself must reject an outdoor candidate.
        req = self.prepare()["optimizeRequest"]
        self.assertEqual(req["candidates"][0]["position"]["x"], -1.0)
        response = TestClient(app).post("/optimize", json=req)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["feasibleCandidatesCount"], 1)

    def test_rejects_duplicate_candidate_positions(self):
        self.payload["candidates"][1]["routerPosition"] = copy.deepcopy(
            self.payload["candidates"][0]["routerPosition"]
        )
        self.fails("duplicate candidate")

    def test_rejects_unexpected_fields_in_synthetic_contract(self):
        self.payload["candidates"][0]["correctedRssiDbm"] = [-50]
        self.fails("unexpected")

    def test_no_current_data_does_not_invent_before_score(self):
        self.payload["current"] = None
        req = self.prepare()["optimizeRequest"]
        self.assertIsNone(req["current"])

    def test_explicit_band_24_accepted(self):
        for grid in self.payload["candidates"] + [self.payload["current"]]:
            grid["frequencyGHz"] = 2.4
        out = self.prepare()
        self.assertEqual(out["provenance"]["frequencyGHz"], 2.4)


if __name__ == "__main__":
    unittest.main()
