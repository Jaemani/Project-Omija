"""StealthMole exposure adapters (contract-first).

Real API (`stealthmole.py`) and mock (`mock.py`) implement the same
`ExposureSource` Protocol so the source can be hot-swapped on day-1.
`normalize()` is the single gateway that turns raw records into `Exposure`
ontology objects and enforces secret masking at the boundary.
"""

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
