"""Contract-independent synthetic fixture tests for 4th-team integration boundary.

No test claims to exercise team 2's /simulate or team 3's actual calibration.
"""
import copy
import json
import math
import unittest
from pathlib import Path

from optimizer.synthetic_adapter import adapt_synthetic_grid


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic_grid_handoff.json"


def data():
    return copy.deepcopy(json.loads(FIXTURE.read_text(encoding="utf-8")))


class SyntheticHandoffTests(unittest.TestCase):
    def test_rows_are_z_columns_are_x_and_values_not_transposed(self):
        d = data()
        result = adapt_synthetic_grid(d["grid"], d["probes"])
        self.assertEqual(result["probeCellsRowZColX"], [[0, 1], [1, 0], [1, 2]])
        self.assertEqual(result["prediction"]["rssisDbm"], [-60, -55, -75])
        self.assertEqual(result["prediction"]["position"], d["grid"]["routerPosition"])
        self.assertTrue(result["isSynthetic"])
        self.assertEqual(result["contractStatus"], "UNVERIFIED_SYNTHETIC")

    def test_coordinate_conversion_with_nonzero_origin_and_step(self):
        d = data()
        grid = d["grid"]
        grid["originXZ"] = {"x": 2, "z": 8}
        grid["gridStepM"] = 0.5
        probes = [{"x": 2.75, "z": 8.25, "y": 1},
                  {"x": 2.25, "z": 8.75, "y": 1},
                  {"x": 3.25, "z": 8.75, "y": 1}]
        r = adapt_synthetic_grid(grid, probes)
        self.assertEqual(r["probeCellsRowZColX"], [[0, 1], [1, 0], [1, 2]])
        self.assertEqual(r["prediction"]["rssisDbm"], [-60, -55, -75])

    def test_row_z_col_x_axes_are_explicit(self):
        d = data()
        d["grid"]["rowAxis"] = "Y"
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_column_axis_must_be_x(self):
        d = data()
        d["grid"]["columnAxis"] = "Y"
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_vertical_axis_must_be_y(self):
        d = data()
        d["grid"]["verticalAxis"] = "Z"
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_floor_plane_must_be_xz(self):
        d = data()
        d["grid"]["coordinateSystem"] = "XY"
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_grid_anchor_must_be_cell_center(self):
        d = data()
        d["grid"]["cellAnchor"] = "corner"
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_probe_must_be_at_cell_center_no_unagreed_interpolation(self):
        d = data()
        d["probes"][0]["x"] = 1.1
        with self.assertRaisesRegex(ValueError, "cell centre"):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_probe_outside_grid_is_rejected(self):
        d = data()
        d["probes"][0]["z"] = 20.5
        with self.assertRaisesRegex(ValueError, "outside synthetic grid"):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_probe_height_uses_y_not_grid_row(self):
        d = data()
        d["probes"][0]["y"] = 1.5
        with self.assertRaisesRegex(ValueError, "receiver Y"):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_receiver_y_is_required(self):
        d = data()
        del d["grid"]["receiverY"]
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_missing_origin_is_rejected(self):
        d = data()
        del d["grid"]["originXZ"]
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_zero_grid_step_rejected(self):
        d = data()
        d["grid"]["gridStepM"] = 0
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_ragged_rssi_rows_rejected(self):
        d = data()
        d["grid"]["values"][1].pop()
        with self.assertRaisesRegex(ValueError, "rectangular"):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_empty_rssi_grid_rejected(self):
        d = data()
        d["grid"]["values"] = []
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_empty_rssi_row_rejected(self):
        d = data()
        d["grid"]["values"] = [[]]
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_rssi_below_minimum_rejected(self):
        d = data()
        d["grid"]["values"][0][1] = -151
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_rssi_above_maximum_rejected(self):
        d = data()
        d["grid"]["values"][0][1] = 31
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_non_finite_rssi_rejected(self):
        for invalid in (math.nan, math.inf, -math.inf):
            with self.subTest(value=repr(invalid)):
                d = data()
                d["grid"]["values"][0][0] = invalid
                with self.assertRaises(ValueError):
                    adapt_synthetic_grid(d["grid"], d["probes"])

    def test_only_24_and_5ghz_accepted(self):
        d = data()
        d["grid"]["frequencyGHz"] = 6
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_expected_frequency_mismatch_rejected(self):
        d = data()
        with self.assertRaisesRegex(ValueError, "requested band"):
            adapt_synthetic_grid(d["grid"], d["probes"], expected_frequency_ghz=5)

    def test_expected_frequency_can_match(self):
        d = data()
        r = adapt_synthetic_grid(d["grid"], d["probes"], expected_frequency_ghz=2.4)
        self.assertEqual(r["prediction"]["rssisDbm"], [-60, -55, -75])

    def test_no_probes_rejected(self):
        d = data()
        with self.assertRaisesRegex(ValueError, "at least one probe"):
            adapt_synthetic_grid(d["grid"], [])

    def test_flag_is_synthetic_mandatory(self):
        d = data()
        del d["grid"]["isSynthetic"]
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_is_synthetic_false_rejected(self):
        d = data()
        d["grid"]["isSynthetic"] = False
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_source_must_say_unverified_synthetic(self):
        d = data()
        d["grid"]["contractStatus"] = "VERIFIED_REAL"
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_unrecognized_grid_field_rejected(self):
        d = data()
        d["grid"]["interpolation"] = "silently_guess"
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"])

    def test_absent_calibration_is_not_applied(self):
        d = data()
        r = adapt_synthetic_grid(d["grid"], d["probes"])
        self.assertEqual(r["calibrationStatus"], "missing")
        self.assertEqual(r["signalSource"], "synthetic_grid_unadjusted")
        self.assertEqual(r["prediction"]["rssisDbm"], [-60, -55, -75])

    def test_explicit_missing_calibration_still_unadjusted(self):
        d = data()
        r = adapt_synthetic_grid(d["grid"], d["probes"], d["missingCalibration"])
        self.assertEqual(r["calibrationStatus"], "missing")
        self.assertEqual(r["prediction"]["rssisDbm"], [-60, -55, -75])

    def test_provided_synthetic_correction_does_not_compute_bias(self):
        d = data()
        r = adapt_synthetic_grid(d["grid"], d["probes"], d["providedSyntheticCalibration"])
        self.assertEqual(r["calibrationStatus"], "provided_synthetic")
        self.assertEqual(r["signalSource"], "synthetic_corrected_fixture")
        self.assertEqual(r["prediction"]["rssisDbm"], [-61, -56, -76])

    def test_failed_calibration_never_silent_fallback(self):
        d = data()
        with self.assertRaisesRegex(ValueError, "explicitly failed"):
            adapt_synthetic_grid(d["grid"], d["probes"], d["failedCalibration"])

    def test_failed_calibration_requires_reason(self):
        d = data()
        cal = d["failedCalibration"]
        del cal["errorCode"]
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"], cal)

    def test_mismatched_calibration_band_rejected(self):
        d = data()
        cal = d["providedSyntheticCalibration"]
        cal["frequencyGHz"] = 5
        with self.assertRaisesRegex(ValueError, "frequencyGHz differs"):
            adapt_synthetic_grid(d["grid"], d["probes"], cal)

    def test_mismatched_calibration_router_position_rejected(self):
        d = data()
        cal = d["providedSyntheticCalibration"]
        cal["routerPosition"]["x"] = 2
        with self.assertRaisesRegex(ValueError, "routerPosition differs"):
            adapt_synthetic_grid(d["grid"], d["probes"], cal)

    def test_mismatched_calibration_probe_order_rejected(self):
        d = data()
        cal = d["providedSyntheticCalibration"]
        cal["probeCells"] = list(reversed(cal["probeCells"]))
        with self.assertRaisesRegex(ValueError, "order does not match"):
            adapt_synthetic_grid(d["grid"], d["probes"], cal)

    def test_mismatched_calibration_vector_length_rejected(self):
        d = data()
        cal = d["providedSyntheticCalibration"]
        cal["correctedRssiDbm"] = [-60]
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"], cal)

    def test_missing_calibration_cannot_contain_corrected_values(self):
        d = data()
        cal = d["missingCalibration"]
        cal["correctedRssiDbm"] = [-61, -56, -76]
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"], cal)

    def test_bad_corrected_rssi_rejected(self):
        d = data()
        cal = d["providedSyntheticCalibration"]
        cal["correctedRssiDbm"][0] = -160
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"], cal)

    def test_nonfinite_corrected_rssi_rejected(self):
        d = data()
        cal = d["providedSyntheticCalibration"]
        cal["correctedRssiDbm"][0] = math.nan
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"], cal)

    def test_not_synthetic_calibration_rejected(self):
        d = data()
        cal = d["providedSyntheticCalibration"]
        cal["isSynthetic"] = False
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"], cal)

    def test_calibration_status_provided_requires_evidence(self):
        d = data()
        cal = d["providedSyntheticCalibration"]
        cal["probeCells"] = None
        with self.assertRaises(ValueError):
            adapt_synthetic_grid(d["grid"], d["probes"], cal)


if __name__ == "__main__":
    unittest.main(verbosity=2)
