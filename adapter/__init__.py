"""Exposure adapters (contract-first).

The mock adapter (`mock.py`) implements the `ExposureSource` Protocol.
`normalize()` is the single gateway that turns raw records into `Exposure`
ontology objects and enforces secret masking at the boundary.
"""

# StealthMole live-API exports intentionally removed (owner directive, 2026-07-05).

from .base import (
    Device,
    Exposure,
    ExposureSource,
    Identity,
    Secret,
    normalize,
)

__all__ = [
    "Device",
    "Exposure",
    "ExposureSource",
    "Identity",
    "Secret",
    "normalize",
]
