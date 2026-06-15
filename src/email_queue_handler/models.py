from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Email:
    serial_number: int
    machine: str
    to: str
    datetime: datetime
    subject: str
    message: str
    sent: int
