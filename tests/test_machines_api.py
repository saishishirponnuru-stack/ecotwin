import os
import sys
import math
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from dashboard.app import app

client = TestClient(app)

def test_list_machines():
    response = client.get("/api/v1/machines")
    assert response.status_code == 200, f"Unexpected status: {response.status_code}"
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Check required fields in first machine
    machine = data[0]
    for key in ["id", "name", "model_type", "rated_power_kw", "status"]:
        assert key in machine, f"Missing key {key} in machine list"

def test_machine_detail():
    # Use first machine id from list
    list_resp = client.get("/api/v1/machines")
    assert list_resp.status_code == 200
    machines = list_resp.json()
    machine_id = machines[0]["id"]
    detail_resp = client.get(f"/api/v1/machines/{machine_id}")
    assert detail_resp.status_code == 200, f"Unexpected status: {detail_resp.status_code}"
    detail = detail_resp.json()
    # Verify top-level keys
    for key in ["machine", "operating_stats", "recent_readings", "active_anomalies"]:
        assert key in detail, f"Missing key {key} in machine detail"
    # Verify machine subfields
    assert "id" in detail["machine"]
    assert "name" in detail["machine"]
    # operating_stats contains expected keys
    for stat_key in ["total_cycles_recorded", "health_score", "avg_sec_kwh_per_part", "avg_spindle_speed_rpm", "avg_spindle_torque_nm", "max_tool_wear_min", "avg_power_watts", "avg_temp_diff_k", "active_anomalies_count", "tool_wear_status"]:
        assert stat_key in detail["operating_stats"], f"Missing operating stat {stat_key}"

def test_fleet_summary_metrics_are_machine_specific_and_finite():
    machines_response = client.get("/api/v1/machines")
    overview_response = client.get("/api/v1/overview")
    comparison_response = client.get("/api/v1/energy/machine-comparison")
    assert machines_response.status_code == overview_response.status_code == comparison_response.status_code == 200

    machines = {machine["id"]: machine for machine in machines_response.json()}
    fleet_summary = {machine["id"]: machine for machine in overview_response.json()["fleet_summary"]}
    comparisons = {machine["machine_id"]: machine for machine in comparison_response.json()}
    assert machines.keys() == fleet_summary.keys() == comparisons.keys()

    facility_avg_sec = overview_response.json()["avg_sec_kwh_per_part"]
    for machine_id, machine in machines.items():
        summary = fleet_summary[machine_id]
        comparison = comparisons[machine_id]
        assert machine["name"] == comparison["machine_name"]
        assert math.isfinite(summary["avg_sec"])
        assert math.isfinite(summary["efficiency_score"])
        assert isinstance(summary["total_anomalies"], int)
        assert math.isclose(summary["avg_sec"], comparison["avg_sec_kwh_per_part"], rel_tol=1e-9)
        assert summary["provenance_tier"] == "TIER_2_PHYSICALLY_DERIVED"
    assert any(not math.isclose(summary["avg_sec"], facility_avg_sec, rel_tol=1e-6) for summary in fleet_summary.values())
