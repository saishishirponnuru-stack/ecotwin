import os
import sys
import math
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from fastapi.testclient import TestClient
from dashboard.app import app

client = TestClient(app)

def test_energy_overview():
    response = client.get("/api/v1/energy/overview")
    assert response.status_code == 200, f"Unexpected status: {response.status_code}"
    data = response.json()
    # Basic schema checks – ensure keys exist
    assert isinstance(data, dict)
    # Expected keys from ExecutiveOverviewResponse (subset)
    for key in ["facility_health_score", "avg_sec_kwh_per_part", "total_energy_kwh", "cost_inr", "co2_tonnes"]:
        assert key in data, f"Missing key {key} in overview response"

def test_machine_comparison():
    response = client.get("/api/v1/energy/machine-comparison")
    assert response.status_code == 200, f"Unexpected status: {response.status_code}"
    data = response.json()
    assert isinstance(data, list)
    assert data
    config_response = client.get("/api/v1/config")
    assert config_response.status_code == 200
    settings = {item["key"]: float(item["value"]) for item in config_response.json()}
    for item in data:
        for key in ["machine_id", "machine_name", "avg_sec_kwh_per_part", "total_energy_kwh", "cost_inr", "co2_tonnes"]:
            assert key in item, f"Missing key {key} in machine comparison item"
        assert item["machine_name"]
        assert item["machine_id"]
        assert "co2_kg" not in item
        for key in ["avg_sec_kwh_per_part", "total_energy_kwh", "cost_inr", "co2_tonnes"]:
            assert isinstance(item[key], (int, float)) and math.isfinite(item[key]), f"Invalid {key} for {item['machine_id']}"
        assert item["avg_sec_kwh_per_part"] > 0
        assert item["total_energy_kwh"] > 0
        assert math.isclose(item["cost_inr"], round(item["total_energy_kwh"] * settings["base_tariff_inr"], 0))
        assert math.isclose(item["co2_tonnes"], round(item["total_energy_kwh"] * settings["grid_emission_factor"] / 1000.0, 2))
