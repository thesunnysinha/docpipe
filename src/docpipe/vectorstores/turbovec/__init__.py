"""TurboVec plugin adapter and safe local persistence."""

from docpipe.vectorstores.turbovec.adapter import (
    TurboVecAdapter,
    TurboVecRepository,
)
from docpipe.vectorstores.turbovec.configuration import TurboVecConfig
from docpipe.vectorstores.turbovec.repository import TurboVecFileRepository
from docpipe.vectorstores.turbovec.vendor import (
    LazyTurboVecIndexFactory,
    TurboVecIndex,
    TurboVecIndexFactory,
)

__all__ = [
    "LazyTurboVecIndexFactory",
    "TurboVecAdapter",
    "TurboVecConfig",
    "TurboVecFileRepository",
    "TurboVecIndex",
    "TurboVecIndexFactory",
    "TurboVecRepository",
]
