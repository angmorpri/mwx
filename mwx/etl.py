# 2025/08/21
"""
etl.py - Defines the read and write operations for the application.

Read extracts data from MyWallet SQLite databases, and transforms it into MWX
data models (defined in model.py).
Write serializes MWX data models back into a MyWallet SQLite database.

"""

from pathlib import Path


def read(path: str | Path) -> MWXNamespace:
    pass


def write(data: MWXNamespace, path: str | Path) -> None:
    pass
