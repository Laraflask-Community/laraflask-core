"""Policy - Base class for resource policies."""

from __future__ import annotations
from typing import Any, Optional


class Policy:
    """Base class for resource policies."""

    def before(self, user: Any, ability: str) -> Optional[bool]:
        return None

    def view_any(self, user: Any) -> bool:
        return False

    def view(self, user: Any, model: Any) -> bool:
        return False

    def create(self, user: Any) -> bool:
        return False

    def update(self, user: Any, model: Any) -> bool:
        return False

    def delete(self, user: Any, model: Any) -> bool:
        return False

    def restore(self, user: Any, model: Any) -> bool:
        return False

    def force_delete(self, user: Any, model: Any) -> bool:
        return False
