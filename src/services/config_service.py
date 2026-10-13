"""
System Settings Service for EcoTwin.
Manages configurable tariffs, emission factors, and operational constants.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from src.db.models import SystemSetting


class ConfigService:
    @staticmethod
    def get_all_settings(db: Session) -> List[Dict[str, Any]]:
        """Fetch all system configuration records."""
        settings = db.query(SystemSetting).all()
        return [s.to_dict() for s in settings]

    @staticmethod
    def update_settings(db: Session, updates: Dict[str, str]) -> List[Dict[str, Any]]:
        """Update configurable settings in the database."""
        for key, value in updates.items():
            setting = db.query(SystemSetting).filter_by(key=key).first()
            if setting:
                setting.value = str(value)
            else:
                db.add(SystemSetting(key=key, value=str(value), description=f"Custom setting {key}"))
        db.commit()
        return ConfigService.get_all_settings(db)
