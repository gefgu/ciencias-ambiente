"""Shared data contract (manual §5.2): hardware sim (Automação) -> signal manager (Computação) + emissions (Mecânica)."""
from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class Sensor(BaseModel):
    sensor_id: str
    state: Literal["occupied", "free"]
    vehicle_speed_kmh: float | None = Field(default=None, ge=0)


class Metrics(BaseModel):
    queue_length_meters: float = Field(ge=0)
    co2_grams_per_second: float = Field(ge=0)


class IntersectionMessage(BaseModel):
    timestamp: datetime
    intersection_id: str
    sensors: list[Sensor]
    instantaneous_metrics: Metrics


EXAMPLE = {"timestamp": "2026-08-21T17:30:00Z", "intersection_id": "cruzamento_rua_xv_floriano",
           "sensors": [{"sensor_id": "sensor_indutivo_lane_1", "state": "occupied", "vehicle_speed_kmh": 14.5}],
           "instantaneous_metrics": {"queue_length_meters": 32.0, "co2_grams_per_second": 12.4}}
# Preliminary MQTT topic tree (to be finalised in M3)
TOPICS = ["cps/curitiba/{intersection_id}/sensors/{sensor_id}", "cps/curitiba/{intersection_id}/metrics",
          "cps/curitiba/{intersection_id}/signal/cmd", "cps/curitiba/bus/{line}/priority"]

if __name__ == "__main__":
    print(IntersectionMessage.model_validate(EXAMPLE).model_dump_json(indent=1))
