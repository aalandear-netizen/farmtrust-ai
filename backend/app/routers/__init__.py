"""Package init for routers."""

from app.routers import (
    audit,
    auth,
    farmers,
    government,
    insurance,
    loans,
    market,
    notifications,
    trust_scores,
)

__all__ = [
    "auth",
    "farmers",
    "trust_scores",
    "loans",
    "insurance",
    "market",
    "government",
    "audit",
    "notifications",
]
