from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class BaseGuardrail(ABC):
    @abstractmethod
    def evaluate(self, target: Any) -> Any:
        pass
