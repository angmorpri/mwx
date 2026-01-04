# MWX

> **MWX** is a Python toolkit to inspect, manipulate, and regenerate backup databases from the Android app **MyWallet**.

> ⚠️ The project is intended for **personal use** only.

It provides a clean data model on top of the app’s SQLite backup format, making it possible to automate analysis, reporting, and bulk edits using Python scripts.

---

## ✨ Features

- Typed data model mirroring MyWallet’s core concepts
- Safe read–modify–write workflow for backup databases
- Powerful filtering and aggregation utilities
- Script-friendly API (no GUI dependencies)

---

## 🧠 Data Model

Everything stored in a MyWallet database is represented by **four entities**:

- **`Account`** – where the money is stored
- **`Counterpart`** – where the money comes from or goes to
- **`Category`** – high‑level classification of an entry
- **`Entry`** – the atomic accounting unit

An `Entry` represents a movement of money on a specific date, between a source and a target, within a category, and with optional descriptive information.

---

## 🧩 Base Class: `WalletEntity`

All entities inherit from the base class `WalletEntity`, which defines the minimum common interface:

- **`mwid`** – numeric ID of the entity in the MyWallet database
- **`sorting_key`** – key used to compare and sort entities
- **`to_dict()`** – serialize the entity to a Python dictionary
- **`to_mywallet()`** – serialize the entity to the MyWallet database format

> ℹ️ If an entity has not yet been persisted in the database, its `mwid` **must be `-1`**.

---

## 📦 Entities

### `Account(mwid, name, order=-1, color="#000000", is_visible=True, is_legacy=False)`

Represents a money container inside the app.

- **`name`** – account name (no whitespace, first letter capitalized)
- **`repr_name`** – display name, mainly to distinguish from counterparts
- **`order`** – UI ordering index (1–999). Defaults to the next available index
- **`color`** – hexadecimal color in `#RRGGBB` format
- **`is_visible`** – whether the account is visible in the app UI
- **`is_legacy`** – marks accounts no longer in use (kept for historical entries)

---

### `Counterpart(mwid, name)`

Represents an external entity involved in a transaction.

- **`name`** – counterpart name
- **`repr_name`** – alias of `name`, for compatibility with `Account`
- **`is_legacy`** – unused, present only for interface compatibility

---

### `Category(mwid, repr_name, cat_type, icon_id=0, color="#000000", is_legacy=False)`

Classifies entries at a high level.

- **`repr_name`** – full category name in `<code>. <name>` format
- **`code`** – category identifier (`X##`, where `X` is an uppercase letter)
- **`name`** – human‑readable name (should start with a capital letter)
- **`type`** – `+1` income, `-1` expense, `0` transfer
- **`icon_id`** – UI icon ID (0–99, `0` means no icon)
- **`color`** – hexadecimal color in `#RRGGBB` format
- **`is_legacy`** – category no longer in use

---

### `Entry(mwid, amount, date, ent_type, source, target, category, item="", details="", is_bill=False)`

Represents a single money movement.

- **`amount`** – `Money` object (fixed two decimals, euro‑aware formatting)
- **`date`** – `datetime` of the movement
- **`type`** – `+1` income, `-1` expense, `0` transfer
- **`source`** – origin (`Account` or `Counterpart`)
- **`target`** – destination (`Account` or `Counterpart`)
- **`category`** – associated `Category` (type must match the entry)
- **`item`** – short description (defaults to _"Sin concepto"_)
- **`details`** – optional extended description
- **`is_bill`** – whether the entry comes from a recurring fee

Utility methods:

- **`has_account(account)`** – checks if the account is involved
- **`flow(account)`** – returns `+1`, `-1`, or `0` from the account’s perspective

---

## 🗂️ Class `Wallet`

The `Wallet` class orchestrates reading, writing, querying, and aggregating data.

### `read(path)`

Reads a MyWallet backup database and populates:

- `accounts`
- `counterparts`
- `categories`
- `entries`

Derived read‑only collections:

- `incomes`
- `expenses`
- `transfers`

---

### `write(path=None, new_db_name="MWX_{now}_{stem}.sqlite", overwrite=False, safe_delete=False, verbose=2)`

Writes the current in‑memory state to a new MyWallet backup database.

- Requires a **source database path** (from `read`) to know what to modify
- Creates a new database file in the same directory

Supported filename placeholders:

- `{now}` – current timestamp (`YYYYMMDDHHMMSS`)
- `{name}` – original filename with extension
- `{stem}` – original filename without extension
- `{ext}` – original file extension

Additional options:

- **`overwrite`** – allow overwriting existing files
- **`safe_delete`** – prompt before deleting entities
- **`verbose`** – output level:
  - `0`: silent
  - `1`: warnings only
  - `2`: warnings + info (default)

---

### `find(*funcs, **params)`

Filters entities using predicates and attribute‑based criteria.

- All conditions must match
- List‑valued parameters are expanded and combined

Special parameters:

- **`entity`** – limit search to a specific entity type
- **`date`** – single date, partial date string, range, or `daterange`
- **`year`**, **`month`**, **`day`** – calendar filters
- **`amount`** – exact value or range
- **`source`**, **`target`**, **`category`** – accept objects, names, codes, or MWIDs
- **`account`**, **`counterpart`** – searched in both source and target
- **`flow`** – direction of money flow from an account’s perspective

Predicate functions must accept an entity and return `True` or `False` without raising.

---

### `sum(account, date, *funcs, **params)`

Returns the accumulated balance variation for an `account` over a date range.

Equivalent to:

```
sum(e.amount * e.flow(account)
    for e in wallet.find(*funcs, account=account, date=date, **params))
```

---

### `budget(account, date, *funcs, **params)`

Returns the available budget of an account up to a given date.

Internally equivalent to:

```
wallet.sum(account, (..., date), *funcs, **params)
```

---

## 🧩 Installation

Although **MWX** is not published on PyPI, it can be installed directly from GitHub using `pip`:

```bash
pip install "git+https://github.com/angmorpri/mwx.git"
```

---

## 🧪 Usage Example

The following example generates a simple **accounting snapshot** based on available accounts in the MyWallet database.

It aggregates liquid accounts into a global total and then breaks down illiquid assets by item:

```python
from mwx import Wallet

wallet = Wallet(PATH_TO_MYWALLET_DB)

liquid_accounts = [
    "@Presupuesto",
    "@Básicos",
    "@Personales",
    "@Metálico",
    "@UpGourmet",
    "@Hucha",
    "@Reserva",
]
illiquid_account = "@Inversión"

total = 0.0
for asset in liquid_accounts:
    budget = wallet.budget(asset, "2100-01-01")
    print(f"{asset:.<25}{budget}")
    total += budget
print("-" * 40)
print(f"{'TOTAL':.<25}{total}")

illiquid_assets = set()
for entry in wallet.find(account=illiquid_account):
    illiquid_assets.add(entry.item)

for asset in illiquid_assets:
    budget = wallet.budget(illiquid_account, "2100-01-01", item=asset)
    print(f"{asset:.<35}{budget}")
    total += budget
print("-" * 40)
print(f"{'TOTAL':.<35}{total}")
```

This pattern can be adapted to generate personal balance sheets, asset breakdowns, or long-term budget projections.

---

## 🐍 Python Version

MWX targets **Python 3.12**.

Earlier versions are not officially supported.

---

## ⚠️ Disclaimer

This project is **not affiliated with, endorsed by, or connected to** the original *MyWallet* Android application.

MyWallet has been discontinued since 2016. MWX only operates on user-owned backup databases for personal analysis and automation purposes.

---

## 📄 License

This project is licensed under the **MIT License**.

