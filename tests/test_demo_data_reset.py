"""Tests for the scoped demo-anomaly reset using isolated SQLite databases."""

from datetime import datetime, timedelta
from math import pi
import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dashboard.app import app
from src.db.database import Base, get_db
from src.db.models import AnomalyEvent, Machine, TelemetryReading
from src.services.demo_data_service import (
    DEMO_ANOMALY_CONTRIBUTORS,
    DEMO_ANOMALY_TELEMETRY_IDS,
)


@pytest.fixture
def demo_reset_client(tmp_path):
    # This file is created inside pytest's temporary directory, never ecotwin.db.
    db_file = tmp_path / "ecotwin-test.db"
    engine = create_engine(
        f"sqlite:///{db_file.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with TestSession() as db:
        db.add(Machine(
            id="M-02",
            name="CNC Milling Center 2",
            model_type="CNC 3-Axis Mill",
            rated_power_kw=15.0,
            status="WARNING",
        ))
        db.flush()
        readings = []
        events = []
        for anomaly_id, telemetry_id in DEMO_ANOMALY_TELEMETRY_IDS.items():
            timestamp = datetime(2024, 1, 1) + timedelta(seconds=anomaly_id * 30)
            reading = TelemetryReading(
                id=telemetry_id,
                timestamp=timestamp,
                machine_id="M-02",
                batch_id=None,
                product_type="M",
                shift="Day",
                rotational_speed_rpm=1500.0,
                torque_nm=40.0,
                tool_wear_min=10.0,
                air_temp_k=298.1,
                process_temp_k=308.6,
                temp_diff_k=10.5,
                machine_failure=0,
                power_watts=6283.185307,
                electrical_power_watts=7391.982714,
                cycle_time_minutes=3.0,
                energy_kwh=0.5,
                sec_kwh_per_part=0.5,
                idle_time_seconds=0.0,
                ambient_temperature=25.0,
                maintenance_status="OK",
                maintenance_days_since=0.0,
                electricity_tariff=8.5,
                provenance_tier="TIER_2_PHYSICALLY_DERIVED",
            )
            readings.append(reading)
            nominal = (40.0 * (1500.0 * 2 * pi / 60) / 0.85 * (3.0 / 60)) / 1000
            residual = 0.5 - nominal
            events.append(AnomalyEvent(
                id=anomaly_id,
                telemetry_id=telemetry_id,
                machine_id="M-02",
                timestamp=timestamp,
                actual_kwh=0.5,
                predicted_kwh=nominal,
                residual_kwh=residual,
                z_score=residual / 0.015,
                severity="critical",
                reason_code="EXCESSIVE_TOOL_FRICTION",
                contributors=dict(DEMO_ANOMALY_CONTRIBUTORS),
                potential_saving_kwh=residual,
                is_resolved=True,
            ))

        # An additional non-demo/imported anomaly must remain outside the reset.
        readings.append(TelemetryReading(
            id=101,
            timestamp=datetime(2024, 2, 1),
            machine_id="M-02",
            batch_id=None,
            product_type="M",
            shift="Day",
            rotational_speed_rpm=1500.0,
            torque_nm=40.0,
            tool_wear_min=10.0,
            air_temp_k=298.1,
            process_temp_k=308.6,
            temp_diff_k=10.5,
            machine_failure=0,
            power_watts=6283.185307,
            electrical_power_watts=7391.982714,
            cycle_time_minutes=3.0,
            energy_kwh=0.5,
            sec_kwh_per_part=0.5,
            idle_time_seconds=0.0,
            ambient_temperature=25.0,
            maintenance_status="OK",
            maintenance_days_since=0.0,
            electricity_tariff=8.5,
            provenance_tier="TIER_2_PHYSICALLY_DERIVED",
        ))
        db.add_all(readings)
        db.flush()
        events.append(AnomalyEvent(
            id=21,
            telemetry_id=101,
            machine_id="M-02",
            timestamp=datetime(2024, 2, 1),
            actual_kwh=0.5,
            predicted_kwh=0.4,
            residual_kwh=0.1,
            z_score=6.66,
            severity="critical",
            reason_code="IMPORTED_RECORD",
            contributors={"source": "imported"},
            potential_saving_kwh=0.1,
            is_resolved=True,
        ))
        db.add_all(events)
        db.commit()

    def override_get_db():
        with TestSession() as db:
            yield db

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client, TestSession, db_file
    finally:
        client.close()
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _immutable_snapshot(session_factory):
    with session_factory() as db:
        rows = db.query(AnomalyEvent).order_by(AnomalyEvent.id).all()
        return {
            event.id: (
                event.telemetry_id,
                event.machine_id,
                event.timestamp,
                event.actual_kwh,
                event.predicted_kwh,
                event.residual_kwh,
                event.z_score,
                event.severity,
                event.reason_code,
                event.contributors,
                event.potential_saving_kwh,
            )
            for event in rows
        }


def test_reset_reopens_original_events_preserves_other_data_and_is_idempotent(demo_reset_client):
    client, session_factory, db_file = demo_reset_client
    before = _immutable_snapshot(session_factory)
    with session_factory() as db:
        telemetry_count_before = db.query(TelemetryReading).count()
        anomaly_count_before = db.query(AnomalyEvent).count()

    response = client.post("/api/v1/demo-data/reset", json={"confirm": True})
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert result["updated_count"] == 20
    assert result["total_demo_anomalies"] == 20
    assert result["open_demo_anomalies"] == 20
    assert result["resolved_demo_anomalies"] == 0
    assert result["backup_file"]

    backup_path = db_file.parent / result["backup_file"]
    assert backup_path.is_file()
    backup_db = sqlite3.connect(backup_path.as_uri() + "?mode=ro", uri=True)
    try:
        assert backup_db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert backup_db.execute("SELECT COUNT(*) FROM anomaly_events").fetchone()[0] == 21
        assert backup_db.execute("SELECT COUNT(*) FROM anomaly_events WHERE is_resolved = 1").fetchone()[0] == 21
    finally:
        backup_db.close()

    with session_factory() as db:
        events = {event.id: event for event in db.query(AnomalyEvent).all()}
        assert len(events) == anomaly_count_before == 21
        assert db.query(TelemetryReading).count() == telemetry_count_before
        assert all(not events[event_id].is_resolved for event_id in DEMO_ANOMALY_TELEMETRY_IDS)
        assert events[21].is_resolved is True
        assert events[21].reason_code == "IMPORTED_RECORD"
    assert _immutable_snapshot(session_factory) == before

    # Repeating the request is safe: it changes no more rows and adds no backups.
    repeated = client.post("/api/v1/demo-data/reset", json={"confirm": True})
    assert repeated.status_code == 200
    assert repeated.json()["updated_count"] == 0
    assert repeated.json()["backup_file"] is None
    assert len(list((db_file.parent / "backups").glob("*.db"))) == 1
    with session_factory() as db:
        assert db.query(AnomalyEvent).count() == 21
        assert db.query(TelemetryReading).count() == telemetry_count_before


def test_reset_requires_explicit_confirmation(demo_reset_client):
    client, session_factory, db_file = demo_reset_client
    before = _immutable_snapshot(session_factory)

    response = client.post("/api/v1/demo-data/reset", json={"confirm": False})
    assert response.status_code == 422
    with session_factory() as db:
        assert all(event.is_resolved for event in db.query(AnomalyEvent).all())
    assert _immutable_snapshot(session_factory) == before
    assert not (db_file.parent / "backups").exists()


def test_reset_fails_closed_without_partial_changes_when_seed_fingerprint_differs(demo_reset_client):
    client, session_factory, db_file = demo_reset_client
    with session_factory() as db:
        # Make the last whitelisted ID no longer refer to its original reading.
        db.query(AnomalyEvent).filter(AnomalyEvent.id == 20).one().telemetry_id = 101
        db.commit()
        before = _immutable_snapshot(session_factory)

    response = client.post("/api/v1/demo-data/reset", json={"confirm": True})
    assert response.status_code == 409
    assert "no data was changed" in response.json()["detail"].lower()
    with session_factory() as db:
        assert all(event.is_resolved for event in db.query(AnomalyEvent).filter(AnomalyEvent.id <= 20).all())
    assert _immutable_snapshot(session_factory) == before
    assert not (db_file.parent / "backups").exists()
