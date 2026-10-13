"""
SQLAlchemy 2.x Data Models for EcoTwin.

Enforces explicit types, relationships, constraints, and the 5-tier data provenance classification:
- Tier 1: Original sensor values (Rotational speed, Torque, Tool wear, Air/Process temp)
- Tier 2: Physically derived metrics (Power Watts, Energy kWh, SEC kWh/part)
- Tier 3: Calibrated operational context (Machine ID, Shift, Tariff, Ambient temp)
- Tier 4: Model baseline predictions & residual anomalies
- Tier 5: What-If simulation scenarios
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    JSON,
    Index,
    func,
)
from sqlalchemy.orm import relationship

from src.db.database import Base
from src.utils.constants import TIER_2_PHYSICALLY_DERIVED


class Machine(Base):
    """
    Manufacturing machine metadata entity.
    """
    __tablename__ = "machines"

    id = Column(String(16), primary_key=True)  # e.g., 'M-01', 'M-02'
    name = Column(String(64), nullable=False)
    model_type = Column(String(32), nullable=False, default="CNC 3-Axis Mill")
    rated_power_kw = Column(Float, nullable=False, default=15.0)
    status = Column(String(16), nullable=False, default="OPERATIONAL")  # OPERATIONAL, WARNING, MAINTENANCE, OFFLINE
    created_at = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    telemetry_records = relationship("TelemetryReading", back_populates="machine", cascade="all, delete-orphan")
    anomalies = relationship("AnomalyEvent", back_populates="machine", cascade="all, delete-orphan")
    scenarios = relationship("SimulationScenario", back_populates="machine", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "model_type": self.model_type,
            "rated_power_kw": self.rated_power_kw,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ProductionBatch(Base):
    """
    Production batch grouping parts manufactured together.
    """
    __tablename__ = "production_batches"

    batch_id = Column(String(32), primary_key=True)  # e.g., 'B-0000'
    product_type = Column(String(8), nullable=False)  # 'L', 'M', 'H'
    target_quantity = Column(Integer, nullable=False, default=50)
    created_at = Column(DateTime, nullable=False, default=func.now())

    telemetry_records = relationship("TelemetryReading", back_populates="batch")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "product_type": self.product_type,
            "target_quantity": self.target_quantity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TelemetryReading(Base):
    """
    Time-series operational reading per manufactured part.
    Clearly tags original sensor measurements vs physically derived energy.
    """
    __tablename__ = "telemetry_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    machine_id = Column(String(16), ForeignKey("machines.id"), nullable=False, index=True)
    batch_id = Column(String(32), ForeignKey("production_batches.batch_id"), nullable=True)
    product_type = Column(String(8), nullable=False)
    shift = Column(String(16), nullable=False)  # 'Day', 'Evening', 'Night'

    # Tier 1: Original Sensor Measurements
    rotational_speed_rpm = Column(Float, nullable=False)
    torque_nm = Column(Float, nullable=False)
    tool_wear_min = Column(Float, nullable=False)
    air_temp_k = Column(Float, nullable=False)
    process_temp_k = Column(Float, nullable=False)
    temp_diff_k = Column(Float, nullable=False)
    machine_failure = Column(Integer, nullable=False, default=0)

    # Tier 2: Physically Derived Metrics
    power_watts = Column(Float, nullable=False)  # Mechanical power P = tau * omega
    electrical_power_watts = Column(Float, nullable=False)  # P_elec = P_mech / 0.85
    cycle_time_minutes = Column(Float, nullable=False)
    energy_kwh = Column(Float, nullable=False)  # Derived energy
    sec_kwh_per_part = Column(Float, nullable=False)  # Specific energy consumption

    # Tier 3: Calibrated Operational Context
    idle_time_seconds = Column(Float, nullable=False, default=0.0)
    ambient_temperature = Column(Float, nullable=False, default=25.0)
    maintenance_status = Column(String(16), nullable=False, default="OK")
    maintenance_days_since = Column(Float, nullable=False, default=0.0)
    electricity_tariff = Column(Float, nullable=False, default=8.50)
    provenance_tier = Column(String(32), nullable=False, default=TIER_2_PHYSICALLY_DERIVED)

    # Relationships
    machine = relationship("Machine", back_populates="telemetry_records")
    batch = relationship("ProductionBatch", back_populates="telemetry_records")

    __table_args__ = (
        Index("ix_telemetry_machine_time", "machine_id", "timestamp"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "machine_id": self.machine_id,
            "batch_id": self.batch_id,
            "product_type": self.product_type,
            "shift": self.shift,
            "rotational_speed_rpm": round(self.rotational_speed_rpm, 2),
            "torque_nm": round(self.torque_nm, 2),
            "tool_wear_min": round(self.tool_wear_min, 2),
            "air_temp_k": round(self.air_temp_k, 2),
            "process_temp_k": round(self.process_temp_k, 2),
            "temp_diff_k": round(self.temp_diff_k, 2),
            "power_watts": round(self.power_watts, 2),
            "electrical_power_watts": round(self.electrical_power_watts, 2),
            "cycle_time_minutes": round(self.cycle_time_minutes, 2),
            "energy_kwh": round(self.energy_kwh, 6),
            "sec_kwh_per_part": round(self.sec_kwh_per_part, 6),
            "idle_time_seconds": round(self.idle_time_seconds, 1),
            "ambient_temperature": round(self.ambient_temperature, 1),
            "maintenance_status": self.maintenance_status,
            "electricity_tariff": round(self.electricity_tariff, 2),
            "provenance_tier": self.provenance_tier,
        }


class AnomalyEvent(Base):
    """
    Logged statistical energy deviations.
    """
    __tablename__ = "anomaly_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telemetry_id = Column(Integer, ForeignKey("telemetry_readings.id"), nullable=True)
    machine_id = Column(String(16), ForeignKey("machines.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    actual_kwh = Column(Float, nullable=False)
    predicted_kwh = Column(Float, nullable=False)
    residual_kwh = Column(Float, nullable=False)
    z_score = Column(Float, nullable=False)
    severity = Column(String(16), nullable=False)  # 'watch', 'warning', 'critical'
    reason_code = Column(String(64), nullable=False)
    contributors = Column(JSON, nullable=True)
    potential_saving_kwh = Column(Float, nullable=False, default=0.0)
    is_resolved = Column(Boolean, nullable=False, default=False)

    machine = relationship("Machine", back_populates="anomalies")

    __table_args__ = (
        Index("ix_anomaly_machine_severity", "machine_id", "severity"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "telemetry_id": self.telemetry_id,
            "machine_id": self.machine_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "actual_kwh": round(self.actual_kwh, 6),
            "predicted_kwh": round(self.predicted_kwh, 6),
            "residual_kwh": round(self.residual_kwh, 6),
            "z_score": round(self.z_score, 2),
            "severity": self.severity,
            "reason_code": self.reason_code,
            "contributors": self.contributors,
            "potential_saving_kwh": round(self.potential_saving_kwh, 6),
            "is_resolved": self.is_resolved,
        }


class SimulationScenario(Base):
    """
    User-saved What-If simulation runs and projected impacts.
    """
    __tablename__ = "simulation_scenarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    machine_id = Column(String(16), ForeignKey("machines.id"), nullable=False)
    parameters_in = Column(JSON, nullable=False)
    result_out = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    machine = relationship("Machine", back_populates="scenarios")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "machine_id": self.machine_id,
            "parameters_in": self.parameters_in,
            "result_out": self.result_out,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SystemSetting(Base):
    """
    Configurable regulatory, tariff, and operational settings.
    """
    __tablename__ = "system_settings"

    key = Column(String(64), primary_key=True)
    value = Column(String(256), nullable=False)
    description = Column(String(256), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
