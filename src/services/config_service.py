"""
System Settings Service for EcoTwin.
Manages configurable tariffs, emission factors, and operational constants.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from src.db.models import SystemSetting


class ConfigService:
    _NON_NEGATIVE_KEYS = {"base_tariff_inr", "grid_emission_factor"}
    _POSITIVE_KEYS = {"peak_multiplier", "offpeak_multiplier"}

    @classmethod
    def _validate_updates(cls, updates: Dict[str, str]) -> None:
        """Validate the numeric settings used in energy and simulation calculations."""
        for key, value in updates.items():
            if key not in cls._NON_NEGATIVE_KEYS | cls._POSITIVE_KEYS | {"motor_efficiency"}:
                continue
            try:
                numeric_value = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Setting '{key}' must be numeric") from exc
            if not numeric_value == numeric_value or numeric_value in (float("inf"), float("-inf")):
                raise ValueError(f"Setting '{key}' must be finite")
            if key in cls._NON_NEGATIVE_KEYS and numeric_value < 0:
                raise ValueError(f"Setting '{key}' cannot be negative")
            if key in cls._POSITIVE_KEYS and numeric_value <= 0:
                raise ValueError(f"Setting '{key}' must be greater than zero")
            if key == "motor_efficiency" and not 0 < numeric_value <= 1:
                raise ValueError("Setting 'motor_efficiency' must be in (0, 1]")

    @staticmethod
    def get_all_settings(db: Session) -> List[Dict[str, Any]]:
        """Fetch all system configuration records."""
        settings = db.query(SystemSetting).all()
        return [s.to_dict() for s in settings]

    @staticmethod
    def update_settings(db: Session, updates: Dict[str, str]) -> List[Dict[str, Any]]:
        """Update configurable settings in the database."""
        ConfigService._validate_updates(updates)
        try:
            for key, value in updates.items():
                setting = db.query(SystemSetting).filter_by(key=key).first()
                if setting:
                    setting.value = str(value)
                else:
                    db.add(SystemSetting(key=key, value=str(value), description=f"Custom setting {key}"))
            db.commit()
        except Exception:
            db.rollback()
            raise
        return ConfigService.get_all_settings(db)
