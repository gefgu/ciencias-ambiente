import pytest
from pydantic import ValidationError
from src.m1.contract import EXAMPLE, IntersectionMessage


def test_example_valid():
    IntersectionMessage.model_validate(EXAMPLE)


def test_negative_queue_rejected():
    bad = {**EXAMPLE, "instantaneous_metrics": {"queue_length_meters": -1, "co2_grams_per_second": 1}}
    with pytest.raises(ValidationError):
        IntersectionMessage.model_validate(bad)
