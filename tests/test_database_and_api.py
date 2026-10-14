"""
Integration and Unit Tests for Milestone 2:
Pluggable Database, Seeding, Data Provenance, and FastAPI v1 Endpoints.
========================================================================
Uses an isolated SQLite database to verify persistence, relationships,
idempotency, and API contracts without requiring external services.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.db.database import Base, get_db
from src.db.models import Machine, ProductionBatch, TelemetryReading, AnomalyEvent, SystemSetting
from src.db.seed import seed_database
from src.utils.constants import TIER_2_PHYSICALLY_DERIVED
from dashboard.app import app

client = TestClient(app)

from sqlalchemy.pool import StaticPool

# Isolated test engine and session using StaticPool so in-memory DB is preserved across connections
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)



@pytest.fixture(scope="module", autouse=True)
def setup_isolated_test_db():
    """Create isolated in-memory tables and seed initial test records."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    seed_database(session=session, max_rows=50)
    session.close()

    # Override get_db dependency in FastAPI app
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


# ─── Database & Seeding Tests ────────────────────────────────────────────────
def test_isolated_db_init_and_tables():
    """Verify all 6 tables exist in the database."""
    inspector = inspect(test_engine)
    table_names = inspector.get_table_names()
    expected = {
        "machines",
        "production_batches",
        "telemetry_readings",
        "anomaly_events",
        "simulation_scenarios",
        "system_settings",
    }
    assert expected.issubset(set(table_names))


def test_db_relationships_and_foreign_keys():
    """Verify entity relationships navigation."""
    session = TestingSessionLocal()
    reading = session.query(TelemetryReading).first()
    assert reading is not None
    assert reading.machine is not None
    assert reading.machine.id == reading.machine_id
    session.close()


def test_seeding_idempotency_repeat_execution():
    """Verify running seed_database again on the same session creates 0 duplicates."""
    session = TestingSessionLocal()
    initial_count = session.query(TelemetryReading).count()
    
    # Re-run seeder
    res = seed_database(session=session, max_rows=50)
    assert res["status"] in ["success_already_seeded", "success"]
    assert res["telemetry_inserted"] == 0
    assert res["telemetry_skipped"] == 50

    final_count = session.query(TelemetryReading).count()
    assert final_count == initial_count
    session.close()


def test_data_provenance_tier_in_seeded_readings():
    """Verify telemetry readings are tagged with TIER_2_PHYSICALLY_DERIVED."""
    session = TestingSessionLocal()
    readings = session.query(TelemetryReading).limit(10).all()
    for r in readings:
        assert r.provenance_tier == TIER_2_PHYSICALLY_DERIVED
    session.close()


# ─── FastAPI v1 Router Tests ─────────────────────────────────────────────────
def test_api_v1_health():
    """Test /api/v1/health response schema."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "total_telemetry_records" in data
    assert data["total_machines"] == 4
    assert data["data_provenance_model"] == "5-Tier Categorized"


def test_api_v1_overview():
    """Test /api/v1/overview response schema and KPI values."""
    response = client.get("/api/v1/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["facility_name"] == "EcoTwin Smart Manufacturing Center"
    assert data["total_energy_kwh"] > 0
    assert data["avg_sec_kwh_per_part"] > 0
    assert len(data["fleet_summary"]) == 4
    assert len(data["daily_trend"]) >= 1


def test_api_v1_machines_list_and_detail():
    """Test /api/v1/machines and /api/v1/machines/{machine_id}."""
    res_list = client.get("/api/v1/machines")
    assert res_list.status_code == 200
    machines = res_list.json()
    assert len(machines) == 4
    assert any(m["id"] == "M-02" for m in machines)

    res_detail = client.get("/api/v1/machines/M-02")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["machine"]["id"] == "M-02"
    assert "operating_stats" in detail
    assert detail["operating_stats"]["avg_sec_kwh_per_part"] > 0
    assert len(detail["recent_readings"]) > 0


def test_api_v1_machines_not_found():
    """Test 404 error handling for non-existent machine."""
    response = client.get("/api/v1/machines/NON-EXISTENT-99")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_api_v1_telemetry_query_and_filter():
    """Test /api/v1/telemetry pagination and filtering."""
    res = client.get("/api/v1/telemetry?limit=5&page=1")
    assert res.status_code == 200
    data = res.json()
    assert len(data["records"]) <= 5
    assert data["total_count"] > 0

    res_filtered = client.get("/api/v1/telemetry?machine_id=M-01&limit=5")
    assert res_filtered.status_code == 200
    for r in res_filtered.json()["records"]:
        assert r["machine_id"] == "M-01"


def test_api_v1_anomalies_and_resolution():
    """Test /api/v1/anomalies listing and resolution endpoint."""
    res = client.get("/api/v1/anomalies")
    assert res.status_code == 200
    data = res.json()
    assert "total_count" in data
    assert len(data["anomalies"]) > 0

    first_anomaly_id = data["anomalies"][0]["id"]
    res_resolve = client.post(
        f"/api/v1/anomalies/{first_anomaly_id}/resolve",
        json={"resolution_notes": "Recalibrated spindle bearings"},
    )
    assert res_resolve.status_code == 200
    assert res_resolve.json()["is_resolved"] is True

    resolved = client.get("/api/v1/anomalies?is_resolved=true")
    assert resolved.status_code == 200
    assert all(event["is_resolved"] for event in resolved.json()["anomalies"])

    # 404 test
    res_404 = client.post("/api/v1/anomalies/9999999/resolve", json={})
    assert res_404.status_code == 404


def test_api_v1_whatif_simulate_valid():
    """Test What-If simulation endpoint with tool replacement and speed change."""
    payload = {
        "machine_id": "M-02",
        "spindle_speed_rpm": 1600.0,
        "torque_nm": 38.0,
        "tool_replacement": True,
        "idle_cutoff_seconds": 15.0,
        "daily_production": 800,
    }
    response = client.post("/api/v1/whatif/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["baseline_energy_kwh"] > 0
    assert data["simulated_energy_kwh"] > 0
    assert "daily_saving_kwh" in data
    assert "annual_cost_saving_inr" in data
    assert data["reliability_status"] in ["Interpolation (High)", "Mild Extrapolation (Caution)"]


def test_api_v1_whatif_simulate_invalid_bounds():
    """Test Pydantic input validation rejection on out-of-spec parameters."""
    payload = {
        "machine_id": "M-02",
        "spindle_speed_rpm": 99999.0,  # Exceeds max 4000 rpm
    }
    response = client.post("/api/v1/whatif/simulate", json=payload)
    assert response.status_code == 422  # Unprocessable Entity


def test_api_v1_whatif_rejects_non_finite_values():
    response = client.post("/api/v1/whatif/simulate", json={"machine_id": "M-02", "torque_nm": "NaN"})
    assert response.status_code == 422


def test_api_v1_whatif_rejects_unknown_machine():
    """A simulation must use observed telemetry from a registered machine."""
    response = client.post("/api/v1/whatif/simulate", json={"machine_id": "M-99"})
    assert response.status_code == 404


def test_api_v1_recommendations_have_evidence_without_unvalidated_benefits():
    """Rules expose their observed evidence but do not invent savings estimates."""
    response = client.get("/api/v1/recommendations")
    assert response.status_code == 200
    recommendations = response.json()["recommendations"]
    for recommendation in recommendations:
        assert recommendation["evidence_source"]
        assert recommendation["evidence_summary"]
        assert "confidence" not in recommendation
        assert recommendation["expected_benefit"] == {}


def test_api_v1_config_get_and_update():
    """Test configurable tariffs and emission factors."""
    res_get = client.get("/api/v1/config")
    assert res_get.status_code == 200
    items = res_get.json()
    assert any(i["key"] == "base_tariff_inr" for i in items)

    # Update tariff to 9.25
    res_put = client.put(
        "/api/v1/config",
        json={"settings": {"base_tariff_inr": "9.25"}},
    )
    assert res_put.status_code == 200
    updated_items = res_put.json()
    tariff_entry = next(i for i in updated_items if i["key"] == "base_tariff_inr")
    assert tariff_entry["value"] == "9.25"


def test_api_v1_config_rejects_invalid_energy_settings():
    before = {item["key"]: item["value"] for item in client.get("/api/v1/config").json()}
    invalid_updates = [
        {"base_tariff_inr": "-1"},
        {"base_tariff_inr": "not-a-number"},
        {"base_tariff_inr": "NaN"},
        {"base_tariff_inr": "Infinity"},
        {"grid_emission_factor": "-0.01"},
        {"motor_efficiency": "0"},
        {"motor_efficiency": "1.01"},
    ]
    for settings in invalid_updates:
        response = client.put("/api/v1/config", json={"settings": settings})
        assert response.status_code == 422

    after = {item["key"]: item["value"] for item in client.get("/api/v1/config").json()}
    assert after == before
