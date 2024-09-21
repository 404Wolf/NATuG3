from functools import cache

from PyQt6.QtGui import QIcon


@cache
def fetch_icon(name: str, folder="generic_icons") -> QIcon:
    """Fetch an icon by name, and cache it."""
    return QIcon(f"ui/resources/icons/{folder}/{name}.svg")
