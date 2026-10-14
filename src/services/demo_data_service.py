"""Narrow, reversible reset of EcoTwin's original seeded anomaly statuses.

The anomaly table has no provenance column. The reset is therefore restricted
to the original seeded event IDs and telemetry links, and validates every event
against the seed's physics calculation before changing only ``is_resolved``.
For file-backed SQLite, a verified pre-reset database backup is required before
any status change. Any baseline or backup mismatch fails closed.
"""

from contextlib import closing
from datetime import datetime, timezone
from math import isclose, pi
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from src.db.models import AnomalyEvent, TelemetryReading


# Stable keys observed in the original seed database. Additional anomaly rows
# (including future/imported rows) are never selected by this reset.
DEMO_ANOMALY_TELEMETRY_IDS = {
    1: 10,
    2: 21,
    3: 23,
    4: 26,
    5: 27,
    6: 28,
    7: 34,
    8: 35,
    9: 43,
    10: 49,
    11: 50,
    12: 52,
    13: 66,
    14: 70,
    15: 71,
    16: 72,
    17: 74,
    18: 76,
    19: 87,
    20: 90,
}
DEMO_ANOMALY_CONTRIBUTORS = {
    "tool_wear": 0.45,
    "thermal_delta": 0.35,
    "friction_penalty": 0.20,
}


class DemoDataResetNotSafe(ValueError):
    """The current database or backup state does not permit a safe reset."""


def _close(actual: float, expected: float) -> bool:
    return isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9)


def _matches_seed_event(event: AnomalyEvent, reading: TelemetryReading, expected_id: int) -> bool:
    """Validate the immutable identity and seed-computed event values."""
    if (
        event.id != expected_id
        or event.telemetry_id != DEMO_ANOMALY_TELEMETRY_IDS[expected_id]
        or event.machine_id != "M-02"
        or reading.machine_id != "M-02"
        or event.timestamp != reading.timestamp
        or event.reason_code != "EXCESSIVE_TOOL_FRICTION"
        or event.contributors != DEMO_ANOMALY_CONTRIBUTORS
    ):
        return False

    # Match the exact nominal-energy calculation used by src/db/seed.py.
    nominal_kwh = (
        reading.torque_nm
        * (reading.rotational_speed_rpm * 2 * pi / 60)
        / 0.85
        * (reading.cycle_time_minutes / 60)
    ) / 1000
    residual_kwh = reading.energy_kwh - nominal_kwh
    if residual_kwh <= 0.005:
        return False

    expected_z_score = residual_kwh / 0.015
    expected_severity = (
        "critical" if expected_z_score >= 3.0 else "warning" if expected_z_score >= 2.0 else "watch"
    )
    return (
        _close(event.actual_kwh, reading.energy_kwh)
        and _close(event.predicted_kwh, nominal_kwh)
        and _close(event.residual_kwh, residual_kwh)
        and _close(event.z_score, expected_z_score)
        and event.severity == expected_severity
        and _close(event.potential_saving_kwh, residual_kwh)
    )


def _create_pre_reset_backup(db: Session) -> str | None:
    """Create an integrity-checked backup for a file-backed SQLite database."""
    bind = db.get_bind()
    if bind.dialect.name != "sqlite":
        raise DemoDataResetNotSafe(
            "Automatic pre-reset backup is supported only for file-backed SQLite; "
            "create a verified database backup before resetting this database."
        )

    database = bind.url.database
    if database in (None, "", ":memory:") or (database.startswith("file:") and "mode=memory" in database):
        # Ephemeral in-memory test/dev databases do not contain persistent user data.
        return None

    db_path = Path(database).expanduser().resolve()
    if not db_path.is_file():
        raise DemoDataResetNotSafe(
            "The SQLite database file was not found; no reset was performed."
        )

    backup_dir = db_path.parent / "backups"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_name = f"{db_path.stem}.pre-demo-reset-{timestamp}-{uuid4().hex[:8]}{db_path.suffix or '.db'}"
    backup_path = backup_dir / backup_name

    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(str(db_path), timeout=10)) as source:
            with closing(sqlite3.connect(str(backup_path), timeout=10)) as destination:
                source.backup(destination)
                integrity = destination.execute("PRAGMA integrity_check").fetchone()
                if not integrity or integrity[0] != "ok":
                    raise sqlite3.DatabaseError("backup integrity check failed")
    except (OSError, sqlite3.Error) as exc:
        raise DemoDataResetNotSafe(
            "The pre-reset SQLite backup failed; no reset was performed. "
            f"Backup error: {exc}"
        ) from exc

    return str(Path("backups") / backup_name)


class DemoDataService:
    @staticmethod
    def reset_demo_anomalies(db: Session) -> dict[str, Any]:
        """Restore only the original seed anomaly resolution flags atomically."""
        expected_ids = set(DEMO_ANOMALY_TELEMETRY_IDS)
        backup_file: str | None = None
        try:
            with db.begin():
                events = (
                    db.query(AnomalyEvent)
                    .filter(AnomalyEvent.id.in_(expected_ids))
                    .order_by(AnomalyEvent.id)
                    .with_for_update()
                    .all()
                )
                event_by_id = {event.id: event for event in events}
                if set(event_by_id) != expected_ids:
                    raise DemoDataResetNotSafe(
                        "The original 20 demo anomaly records are not all present; no data was changed."
                    )

                telemetry_ids = set(DEMO_ANOMALY_TELEMETRY_IDS.values())
                readings = (
                    db.query(TelemetryReading)
                    .filter(TelemetryReading.id.in_(telemetry_ids))
                    .all()
                )
                reading_by_id = {reading.id: reading for reading in readings}
                if set(reading_by_id) != telemetry_ids:
                    raise DemoDataResetNotSafe(
                        "The original demo telemetry links do not match; no data was changed."
                    )

                # Validate every row before changing any status, so a partial or
                # non-demo database state is rejected atomically.
                for anomaly_id, telemetry_id in DEMO_ANOMALY_TELEMETRY_IDS.items():
                    event = event_by_id[anomaly_id]
                    reading = reading_by_id[telemetry_id]
                    if not _matches_seed_event(event, reading, anomaly_id):
                        raise DemoDataResetNotSafe(
                            "The demo anomaly baseline differs from the known seed data; no data was changed."
                        )

                updated_count = sum(1 for event in events if event.is_resolved)
                if updated_count:
                    # Back up the whole DB before changing any persistent data.
                    backup_file = _create_pre_reset_backup(db)
                    for event in events:
                        event.is_resolved = False

            return {
                "status": "success",
                "updated_count": updated_count,
                "total_demo_anomalies": len(expected_ids),
                "open_demo_anomalies": len(expected_ids),
                "resolved_demo_anomalies": 0,
                "backup_file": backup_file,
                "message": (
                    "The 20 original demo anomaly events are now open/unresolved. "
                    "Only their resolution status flags were changed; no records were created or deleted."
                ),
            }
        except DemoDataResetNotSafe:
            raise
