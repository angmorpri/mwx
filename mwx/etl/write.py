# 2025/11/25
"""
write.py - Writing MyWallet data.

Defines function 'write', to save data to a SQLite database with MyWallet
backup format.

"""

from pathlib import Path

from mwx.etl.common import MYWALLET_TABLES, MWXNamespace


def write(path: str | Path, data: MWXNamespace) -> None:
    # TODO
    pass
