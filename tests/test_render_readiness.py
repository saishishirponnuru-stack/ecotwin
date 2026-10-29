"""Render-oriented startup and CORS tests that never connect to the live database."""

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from dashboard import app as dashboard_module
from src.db.bootstrap import initialize_database
from src.db.models import Machine, TelemetryReading


def test_cors_origins_support_explicit_production_frontend(monkeypatch):
    origins = dashboard_module.get_cors_origins(
        " https://ecotwin-frontend.onrender.com,https://dashboard.example.org/ "
    )

    assert "https://ecotwin-frontend.onrender.com" in origins
    assert "https://dashboard.example.org" in origins
    assert "http://localhost:5173" not in origins
    assert "*" not in origins

    monkeypatch.setenv("FRONTEND_ORIGINS", "https://ecotwin-frontend.onrender.com")
    environment_origins = dashboard_module.get_cors_origins()
    assert environment_origins == ["https://ecotwin-frontend.onrender.com"]


def test_cors_origins_reject_wildcards_and_non_origin_urls():
    with pytest.raises(ValueError, match="wildcard"):
        dashboard_module.get_cors_origins("https://*.onrender.com")

    with pytest.raises(ValueError, match="Invalid frontend origin"):
        dashboard_module.get_cors_origins("https://example.org/app")


def test_cors_middleware_uses_exact_origins_with_credentials():
    test_app = FastAPI()
    origins = dashboard_module.configure_cors(test_app, "https://ecotwin-frontend.onrender.com")
    response = TestClient(test_app).options(
        "/resource",
        headers={
            "Origin": "https://ecotwin-frontend.onrender.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "https://ecotwin-frontend.onrender.com" in origins
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://ecotwin-frontend.onrender.com"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_startup_calls_database_bootstrap_without_eager_model_load(monkeypatch):
    calls = []
    attempted_before = dashboard_module._DATA_LOAD_ATTEMPTED
    monkeypatch.setattr(
        dashboard_module,
        "initialize_database",
        lambda: calls.append("initialized") or {"status": "test-only"},
    )

    async def run_lifespan():
        async with dashboard_module.lifespan(dashboard_module.app):
            pass

    asyncio.run(run_lifespan())

    assert calls == ["initialized"]
    assert dashboard_module._DATA_LOAD_ATTEMPTED is attempted_before


def test_database_bootstrap_seeds_once_in_an_isolated_database(tmp_path):
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_sessions = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    csv_path = tmp_path / "minimal_demo.csv"
    csv_path.write_text(
        "timestamp,machine_id,product_type,shift,rotational_speed_rpm,torque_nm,tool_wear_min,air_temp_k,process_temp_k,power_watts,energy_kwh,production_batch_id\n"
        "2026-01-01 12:00:00,M-01,M,Day,1200,10,1,300,310,1256.64,0.0628,B-1\n",
        encoding="utf-8",
    )

    first = initialize_database(
        engine_override=test_engine,
        session_factory=test_sessions,
        csv_path=str(csv_path),
        max_rows=1,
    )
    second = initialize_database(
        engine_override=test_engine,
        session_factory=test_sessions,
        csv_path=str(csv_path),
        max_rows=1,
    )

    with test_sessions() as session:
        machine_count = session.query(Machine).count()
        telemetry_count = session.query(TelemetryReading).count()

    assert first["status"] == "seeded"
    assert second["status"] == "existing_data_preserved"
    assert machine_count == 4
    assert telemetry_count == 1
    test_engine.dispose()
