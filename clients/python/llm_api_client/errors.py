from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ApiError(Exception):
    status_code: int
    code: Optional[str]
    message: str
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        code = f" ({self.code})" if self.code else ""
        return f"{self.status_code}{code}: {self.message}"
