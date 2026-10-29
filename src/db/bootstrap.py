"""Safe schema and demo-data initialization for application startup."""

import logging
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session, sessionmaker

from src.db.database import Base, SessionLocal, engine, init_db
from src.db.models import (
    AnomalyEvent,
    Machine,
    ProductionBatch,
    SimulationScenario,
    SystemSetting,
    TelemetryReading,
)

logger = logging.getLogger(__name__)

_DATA_TABLES = (
    Machine,
    ProductionBatch,
    TelemetryReading,
    AnomalyEvent,
    SimulationScenario,
    SystemSetting,
)


def initialize_database(
    *,
    engine_override=None,
    session_factory: Optional[Callable[[], Session]] = None,
    csv_path: Optional[str] = None,
    max_rows: Optional[int] = None,
) -> dict[str, Any]:
    """Create missing tables and seed demo data only when all data tables are empty.

    Existing rows are never modified or supplemented by automatic demo seeding.
    Optional engine/session inputs make the operation testable without the live DB.
    """
    target_engine = engine_override or engine
    init_db(target_engine)

    factory = session_factory
    if factory is None:
        factory = SessionLocal if engine_override is None else sessionmaker(bind=target_engine)

    db = factory()
    try:
        has_existing_rows = any(db.query(model).first() is not None for model in _DATA_TABLES)
        if has_existing_rows:
            logger.info("Database schema is ready; existing application data preserved without demo seeding.")
            return {"status": "existing_data_preserved", "seed_report": None}

        # Importing the CSV seeder only for an empty database keeps its pandas
        # dependency out of the normal warm-start path.
        from src.db.seed import seed_database

        report = seed_database(csv_path=csv_path, session=db, max_rows=max_rows)
        if report.get("status") not in {"success", "success_already_seeded"}:
            errors = "; ".join(report.get("errors", [])) or report.get("status", "unknown error")
            raise RuntimeError(f"Demo-data initialization failed: {errors}")
        if db.query(TelemetryReading).count() == 0:
            raise RuntimeError("Demo-data initialization completed without telemetry records.")

        logger.info(
            "Database schema and demo data initialized: %s telemetry readings.",
            db.query(TelemetryReading).count(),
        )
        return {"status": "seeded", "seed_report": report}
    except Exception:
        db.rollback()
        logger.exception("EcoTwin database initialization failed.")
        raise
    finally:
        db.close()
