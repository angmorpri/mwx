# 2025/08/21
"""
frames.py - Useful DataFrames generators for reporting.

"""

from datetime import datetime
from itertools import groupby

import pandas as pd

from mwx.etl import MWXNamespace


def MonthlyFrame(mwxns: MWXNamespace) -> pd.DataFrame:
    """Monthly summary DataFrame

    Contains:
    - account and date multi-index
    - list of categories by code, as columns
    - total income, expense and net result, for transactions only
    - total transfers in and out, and net transfers, for transfers only
    - total inbounds and outbounds, and net balance (transactions + transfers)
    - accumulated balance

    """
    accounts = [a.name for a in sorted(mwxns.accounts) if not a.legacy]
    categories = [c.code for c in sorted(mwxns.categories) if not c.legacy]
    entries = [e for e in mwxns.entries if e.is_paid]
    monthly_entries = []
    dates = []
    for (year, month), group in groupby(
        sorted(entries),
        key=lambda e: (e.date.year, e.date.month),
    ):
        dates.append(datetime(year, month, 1))
        monthly_entries.append(((year, month), list(group)))

    df = pd.DataFrame(
        index=pd.MultiIndex.from_product([accounts, dates], names=["account", "date"]),
        columns=[
            "total_income",
            "total_expense",
            "net_result",
            "total_transfer_in",
            "total_transfer_out",
            "net_transfers",
            "total_inbound",
            "total_outbound",
            "net_balance",
            "accum",
        ]
        + categories,
        dtype=float,
    )

    for (year, month), group in monthly_entries:
        group = list(group)
        date = datetime(year, month, 1)
        for account in accounts:
            acc_ents = [e for e in group if e.has_account(account)]
            income = sum(e.amount for e in acc_ents if e.type == +1)
            expense = sum(e.amount for e in acc_ents if e.type == -1)
            transfer_in = sum(e.amount for e in acc_ents if e.tflow(account) == +1)
            transfer_out = sum(e.amount for e in acc_ents if e.tflow(account) == -1)

            df.loc[(account, date), "total_income"] = round(income, 2)
            df.loc[(account, date), "total_expense"] = round(expense, 2)
            df.loc[(account, date), "total_transfer_in"] = round(transfer_in, 2)
            df.loc[(account, date), "total_transfer_out"] = round(transfer_out, 2)

            # Categories
            for category in categories:
                cat_amount = sum(
                    e.amount for e in acc_ents if e.category.code == category
                )
                df.loc[(account, date), category] = round(cat_amount, 2)

    # Computed values
    df["net_result"] = df["total_income"] - df["total_expense"]
    df["net_transfers"] = df["total_transfer_in"] - df["total_transfer_out"]
    df["total_inbound"] = df["total_income"] + df["total_transfer_in"]
    df["total_outbound"] = df["total_expense"] + df["total_transfer_out"]
    df["net_balance"] = df["total_inbound"] - df["total_outbound"]
    df["accum"] = df.groupby(level=0)["net_balance"].cumsum()

    return df
