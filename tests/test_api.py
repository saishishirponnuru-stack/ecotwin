"""Integration tests for EcoTwin FastAPI endpoints."""
import sys
import os
import pytest
from fastapi.testclient import TestClient

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dashboard.app import app

client = TestClient(app)

def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model"] == "XGBoost"
    assert data["dataset_rows"] == 10000

def test_api_simulate_valid():
    response = client.get("/api/simulate", params={
        "torque": 40.0,
        "process_temp": 310.0,
        "speed": 1500,
        "idle_time": 25,
        "tool_wear": 80,
        "daily_production": 800,
    })
    assert response.status_code == 200
    data = response.json()
    assert "current_energy" in data
    assert "new_energy" in data
    assert "annual_cost_saving" in data
    assert "annual_co2_reduction" in data
    assert data["current_energy"] > 0
    assert data["new_energy"] > 0

def test_overview_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "EcoTwin" in response.text
    assert "Factory Overview" in response.text
    assert "chart-energy-trend" in response.text

def test_machine_page():
    response = client.get("/machine/M-02")
    assert response.status_code == 200
    assert "M-02" in response.text
    assert "chart-timeline" in response.text

def test_whatif_page():
    response = client.get("/whatif")
    assert response.status_code == 200
    assert "What-If Lab" in response.text
    assert "simulate()" in response.text

def test_recommendations_page():
    response = client.get("/recommendations")
    assert response.status_code == 200
    assert "Prioritized Recommendations" in response.text
