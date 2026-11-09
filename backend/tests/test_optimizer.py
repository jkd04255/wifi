"""Geometry, cable, priority, AP advice and API checks. No RSSI engine mocked as real."""
import copy
import unittest

from fastapi.testclient import TestClient
from optimizer.api import app
from optimizer.core import CandidateSearchRequest, OptimizeRequest, generate_candidate_positions, optimize


def example():
    return {
        "floor": {"widthM": 6, "depthM": 4, "heightM": 2.7, "walls": []},
        "lanPort": {"x": 0.5, "z": 0.5, "y": 0.3, "maxCableLengthM": 15},
        "probes": [
            {"x": 1, "z": 1, "priorityPct": 100, "targetDbm": -67},
            {"x": 5, "z": 3, "priorityPct": 0, "targetDbm": -67},
            {"x": 2, "z": 3, "priorityPct": -100, "targetDbm": -67}
        ],
        "candidates": [
            {"position": {"x": 1, "z": 1, "y": 1.2}, "rssisDbm": [-55, -85, -30]},
            {"position": {"x": 4, "z": 3, "y": 1.2}, "rssisDbm": [-80, -50, -95]}
        ],
        "current": {
            "position": {"x": 2, "z": 2, "y": 1.2}, "rssisDbm": [-70, -70, -60]
        }
    }


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.data = example()

    def run_opt(self):
        return optimize(OptimizeRequest.model_validate(self.data))

    def test_priority_high_over_normal_and_negative_is_ignored(self):
        a = self.run_opt()
        self.assertEqual(a["status"], "ok")
        self.assertEqual(a["recommendedPosition"]["x"], 1)
        self.assertGreater(a["scoreAfter"], a["scoreBefore"])

        # -100 위치 RSSI를 크게 바꿔도 점수·선정 결과는 변하지 않아야 함
        self.data["candidates"][0]["rssisDbm"][2] = -120
        b = self.run_opt()
        self.assertEqual(a["scoreAfter"], b["scoreAfter"])
        self.assertEqual(a["recommendedPosition"], b["recommendedPosition"])

    def test_router_outside_building_excluded(self):
        self.data["candidates"][0]["position"]["x"] = -1
        # 현재 공유기 위치가 더 좋으면 이동시키지 않는 것이 정상: 후보 필터만 검증
        self.data.pop("current")
        a = self.run_opt()
        self.assertEqual(a["recommendedPosition"]["x"], 4)
        self.assertEqual(a["feasibleCandidatesCount"], 1)

    def test_wall_and_clearance_exclusion(self):
        self.data["floor"]["walls"] = [{"x1": 1, "z1": 0, "x2": 1, "z2": 4}]
        a = self.run_opt()
        self.assertEqual(a["status"], "no_feasible_candidate")
        # candidate x=1은 벽 위, candidate x=4는 포트에서 벽을 통과해야 함

    def test_cable_length_constraint(self):
        self.data["lanPort"]["maxCableLengthM"] = 1.5
        a = self.run_opt()
        self.assertEqual(a["status"], "no_feasible_candidate")

    def test_wall_forces_detour_not_euclidean_distance(self):
        self.data["floor"]["walls"] = [{"x1": 2.0, "z1": 0.0, "x2": 2.0, "z2": 3.0}]
        self.data["lanPort"]["maxCableLengthM"] = 5.3
        self.data["candidates"] = [
            {"position": {"x": 3, "z": 0.5, "y": 1.2}, "rssisDbm": [-50, -50, -50]}
        ]
        a = self.run_opt()
        self.assertEqual(a["status"], "no_feasible_candidate")
        # 유클리드 2.5m 정도이지만 벽의 아래 끝 z=3 부근으로 돌아야 함.
        self.data["lanPort"]["maxCableLengthM"] = 12
        b = self.run_opt()
        self.assertEqual(b["status"], "ok")
        self.assertGreater(b["estimatedCableLengthM"], 6)

    def test_no_feasible_position(self):
        self.data["candidates"] = [
            {"position": {"x": -3, "z": -2}, "rssisDbm": [-50, -50, -50]}
        ]
        self.assertEqual(self.run_opt()["status"], "no_feasible_candidate")

    def test_additional_ap_advice(self):
        self.data["candidates"][0]["rssisDbm"][0] = -74
        self.data["candidates"][1]["rssisDbm"][0] = -78
        self.data["current"]["rssisDbm"][0] = -80
        res = self.run_opt()
        self.assertTrue(res["additionalApAdvised"])
        self.assertEqual(res["criticalCoveragePct"], 0)

    def test_current_better_no_forced_move(self):
        self.data["current"]["rssisDbm"] = [-40, -40, -80]
        res = self.run_opt()
        self.assertEqual(res["recommendedPosition"]["x"], 2)
        self.assertEqual(res["deltaScore"], 0)

    def test_candidate_generator_enforces_cable_length(self):
        req=CandidateSearchRequest.model_validate({
            "floor": self.data["floor"],
            "lanPort": {**self.data["lanPort"], "maxCableLengthM": 2},
            "gridStepM": 1
        })
        result=generate_candidate_positions(req)
        self.assertGreater(result["feasiblePositionsCount"], 0)
        self.assertLess(result["feasiblePositionsCount"], result["generatedPositionsCount"])
        self.assertTrue(all(p["estimatedCableLengthM"] <= 2 for p in result["positions"]))

    def test_candidate_generator_respects_l_shape(self):
        f=dict(self.data["floor"])
        f["footprint"]=[[0,0],[6,0],[6,2],[3,2],[3,4],[0,4]]
        result=generate_candidate_positions(CandidateSearchRequest.model_validate({
            "floor": f, "lanPort": self.data["lanPort"], "gridStepM": 1
        }))
        self.assertGreater(result["feasiblePositionsCount"],0)
        self.assertTrue(all(not (p["x"] > 3 and p["z"] > 2) for p in result["positions"]))

    def test_lan_port_touching_wall_can_exit_room_side(self):
        f=dict(self.data["floor"])
        f["walls"]=[{"x1":0.5,"z1":0,"x2":0.5,"z2":2}]
        results=generate_candidate_positions(CandidateSearchRequest.model_validate({
            "floor": f, "lanPort": {**self.data["lanPort"],"x":0.5},
            "gridStepM": 1
        }))
        self.assertGreater(results["feasiblePositionsCount"], 0)

    def test_without_current_no_invented_score(self):
        self.data.pop("current")
        result = self.run_opt()
        self.assertIsNone(result["scoreBefore"])
        self.assertIsNone(result["deltaScore"])

    def test_l_shape_footprint_filters_candidate(self):
        self.data["floor"]["footprint"] = [
            [0,0],[6,0],[6,2],[3,2],[3,4],[0,4]
        ]
        # L자 바닥 내부의 측정 위치만 입력해야 함
        self.data["probes"][1]["z"] = 1
        a = self.run_opt()
        self.assertEqual(a["recommendedPosition"]["x"], 1)
        self.assertEqual(a["feasibleCandidatesCount"], 1)

    def test_invalid_probe_position_rejected(self):
        self.data["probes"][0]["x"] = 10
        with self.assertRaisesRegex(ValueError, "probe"):
            self.run_opt()

    def test_determinism(self):
        a=self.run_opt()
        b=self.run_opt()
        self.assertEqual(a,b)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health(self):
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_post_success(self):
        r=self.client.post("/optimize",json=example())
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()["signalSource"],"caller_supplied_predictions")

    def test_mismatched_rssi_vector(self):
        body=example()
        body["candidates"][0]["rssisDbm"]=[-50]
        self.assertEqual(self.client.post("/optimize",json=body).status_code,422)

    def test_all_negative_priority_rejected(self):
        body=example()
        for p in body["probes"]:
            p["priorityPct"]=-100
        self.assertEqual(self.client.post("/optimize",json=body).status_code,422)

    def test_candidate_locations_endpoint(self):
        body={"floor":example()["floor"],"lanPort":example()["lanPort"],"gridStepM":1}
        r=self.client.post("/candidate-locations",json=body)
        self.assertEqual(r.status_code,200,r.text)
        self.assertGreater(r.json()["feasiblePositionsCount"],0)

    def test_invalid_extra_fields_rejected(self):
        body=example()
        body["guessedStrength"] = -50
        self.assertEqual(self.client.post("/optimize",json=body).status_code,422)


if __name__=="__main__":
    unittest.main()
