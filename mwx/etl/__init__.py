# 2025/11/25
"""ETL for MyWallet data.

Defines MWXNamespace namedtuple, which provides collections of MyWallet
entities: accounts, categories, entries, counterparts.

"""

from . import excel
from .common import MWXNamespace
from .read import read
from .write import write
