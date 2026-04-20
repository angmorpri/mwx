# 2026/04/20
"""
ximport.py - Construct a Wallet from an Excel workbook.

Counterpart of export.py. Reads a .xlsx file previously produced by
Wallet.to_excel() (or hand-crafted following the same schema) and
builds a fresh Wallet instance from its contents.

The Excel is the sole source of truth: no prior wallet state is assumed
or consulted beyond the canonical capital figures stored in __meta__,
which are used only for optional post-construction validation.

Key conventions:
- MWID blank or -1 → entity created with mwid=-1 ("new, pending DB
  assignment"). The model handles these correctly on write().
- Category references in Movimientos accept either the full repr_name
  ('E01. Comida') or just the code ('E01').
- Counterparts are created on the fly from Origen/Destino fields; no
  dedicated sheet is required.
- Detalles: ' // ' (and variants) restored to '\\n'.
- Es factura / Legacy blank → False.
- Errors fail fast with sheet, row and column in the message.

"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Type

from openpyxl import load_workbook

from mwx.etl.common import compute_capital
from mwx.model import Account, Category, Counterpart, Entry
from mwx.util import Money

if TYPE_CHECKING:
    from mwx.wallet import Wallet


# Constants (must stay in sync with export.py)

_META_SHEET_NAME = "__meta__"
_META_SCHEMA_SUPPORTED = {"mwx-export/1"}
_CAPITAL_TOLERANCE = 0.01  # €, at-cent precision

_TYPE_FROM_LABEL = {"Gasto": -1, "Traslado": 0, "Ingreso": +1}


# Exceptions


class ImportError_(Exception):
    """Structural problem with the workbook (missing sheet, bad schema…)."""


class CellError(ImportError_):
    """Invalid value in a specific cell."""

    def __init__(self, sheet: str, row: int, col: str, value: Any, reason: str) -> None:
        self.sheet = sheet
        self.row = row
        self.col = col
        self.value = value
        self.reason = reason
        super().__init__(f"[{sheet}!{col}{row}] {reason} (valor: {value!r})")


class ValidationError(ImportError_):
    """Capital validation failed after reconstruction."""


# Sheet reading


def _sheet_rows(ws, required_headers: list[str]) -> list[dict[str, Any]]:
    """Return data rows as dicts keyed by header, each tagged with __row__."""
    header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), ())
    headers = [h.strip() if isinstance(h, str) else h for h in header_row]

    missing = [h for h in required_headers if h not in headers]
    if missing:
        raise ImportError_(
            f"Hoja '{ws.title}': faltan columnas requeridas {missing}. "
            f"Encontradas: {[h for h in headers if h]}"
        )

    rows = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if all(c is None for c in row):
            continue
        data = {h: v for h, v in zip(headers, row) if h is not None}
        data["__row__"] = row_idx
        rows.append(data)
    return rows


def _read_meta(ws) -> dict[str, Any]:
    """Parse __meta__ sheet → {'metadata': {...}, 'per_account_capital': {...}}."""
    metadata: dict[str, Any] = {}
    per_account: dict[str, float] = {}

    in_top = True
    saw_bottom_header = False
    for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if row_idx == 1:  # top-table header ("Meta" / "Valor")
            continue
        if all(c is None for c in row):
            in_top = False
            continue
        key, val = row[0], (row[1] if len(row) > 1 else None)
        if in_top:
            if key is not None:
                metadata[str(key)] = val
        else:
            if not saw_bottom_header:
                saw_bottom_header = True  # skip "Cuenta" / "Capital" header
                continue
            if key is not None:
                per_account[str(key)] = float(val) if val is not None else 0.0

    return {"metadata": metadata, "per_account_capital": per_account}


# Field coercion helpers


def _mwid(v: Any, s: str, r: int, c: str) -> int:
    if v is None or (isinstance(v, str) and not v.strip()) or v == -1:
        return -1
    try:
        mwid = int(v)
    except (ValueError, TypeError):
        raise CellError(s, r, c, v, "MWID debe ser entero o vacío")
    if mwid < -1:
        raise CellError(s, r, c, v, "MWID no puede ser menor que -1")
    return mwid


def _str(
    v: Any, s: str, r: int, c: str, *, required: bool = False, default: str = ""
) -> str:
    if v is None or (isinstance(v, str) and not v.strip()):
        if required:
            raise CellError(s, r, c, v, "Campo de texto requerido, está vacío")
        return default
    return str(v).strip()


def _bool(v: Any, s: str, r: int, c: str, *, default: bool = False) -> bool:
    if v is None or (isinstance(v, str) and not v.strip()):
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        low = v.strip().lower()
        if low in ("true", "verdadero", "sí", "si", "1", "yes"):
            return True
        if low in ("false", "falso", "no", "0"):
            return False
    raise CellError(s, r, c, v, "Valor booleano no reconocido")


def _int(v: Any, s: str, r: int, c: str, *, default: int | None = None) -> int:
    if v is None or (isinstance(v, str) and not v.strip()):
        if default is not None:
            return default
        raise CellError(s, r, c, v, "Entero requerido, está vacío")
    try:
        return int(v)
    except (ValueError, TypeError):
        raise CellError(s, r, c, v, "No es un entero válido")


def _money(v: Any, s: str, r: int, c: str) -> Money:
    if v is None or (isinstance(v, str) and not v.strip()):
        raise CellError(s, r, c, v, "Importe requerido, está vacío")
    try:
        return Money(v)
    except Exception as e:
        raise CellError(s, r, c, v, f"Importe inválido: {e}")


def _date(v: Any, s: str, r: int, c: str) -> datetime:
    if v is None:
        raise CellError(s, r, c, v, "Fecha requerida, está vacía")
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)
    if isinstance(v, str):
        for fmt in ("%Y-%m-%d", "%Y%m%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(v.strip(), fmt)
            except ValueError:
                continue
    raise CellError(s, r, c, v, "Formato de fecha no reconocido (usa YYYY-MM-DD)")


def _color(v: Any, s: str, r: int, c: str, *, default: str = "#000000") -> str:
    if v is None or (isinstance(v, str) and not v.strip()):
        return default
    raw = str(v).strip()
    norm = raw if raw.startswith("#") else "#" + raw
    if len(norm) != 7:
        raise CellError(s, r, c, v, "Color debe ser '#RRGGBB'")
    return norm.upper()


def _restore_newlines(v: Any) -> str:
    """Reverse export's ' // ' flattening → '\\n'. Tolerates spacing variants."""
    if v is None:
        return ""
    s = str(v)
    for sep in (" // ", "// ", " //", "//"):
        if sep in s:
            return s.replace(sep, "\n")
    return s


# Builders


def _build_account(row: dict) -> Account:
    s, r = "Cuentas", row["__row__"]
    return Account(
        mwid=_mwid(row.get("MWID"), s, r, "A"),
        name=_str(row.get("Nombre"), s, r, "B", required=True),
        order=_int(row.get("Orden"), s, r, "C", default=-1),
        color=_color(row.get("Color"), s, r, "D"),
        is_visible=_bool(row.get("Visible"), s, r, "E", default=True),
        is_legacy=_bool(row.get("Legacy"), s, r, "F", default=False),
    )


def _build_category(row: dict) -> Category:
    s, r = "Categorías", row["__row__"]
    code = _str(row.get("Código"), s, r, "B", required=True)
    name = _str(row.get("Nombre"), s, r, "C", required=True)
    tipo = _str(row.get("Tipo"), s, r, "D", required=True)
    if tipo not in _TYPE_FROM_LABEL:
        raise CellError(
            s, r, "D", tipo, f"Tipo debe ser uno de {list(_TYPE_FROM_LABEL)}"
        )
    return Category(
        mwid=_mwid(row.get("MWID"), s, r, "A"),
        repr_name=f"{code}. {name}",
        cat_type=_TYPE_FROM_LABEL[tipo],
        icon_id=_int(row.get("Icono"), s, r, "E", default=0),
        color=_color(row.get("Color"), s, r, "F"),
        is_legacy=_bool(row.get("Legacy"), s, r, "G", default=False),
    )


def _build_entry(
    row: dict,
    accounts_by_name: dict[str, Account],
    cats_by_key: dict[str, Category],
    counterparts_by_name: dict[str, Counterpart],
) -> Entry:
    s, r = "Movimientos", row["__row__"]

    tipo = _str(row.get("Tipo"), s, r, "C", required=True)
    if tipo not in _TYPE_FROM_LABEL:
        raise CellError(
            s, r, "C", tipo, f"Tipo debe ser uno de {list(_TYPE_FROM_LABEL)}"
        )
    ent_type = _TYPE_FROM_LABEL[tipo]

    src_ref = _str(row.get("Origen"), s, r, "E", required=True)
    tgt_ref = _str(row.get("Destino"), s, r, "F", required=True)
    cat_ref = _str(row.get("Categoría"), s, r, "G", required=True)

    # Resolve category: exact match first (by code or repr_name),
    # then fallback to extracting the code prefix from the ref string.
    if cat_ref not in cats_by_key:
        # Try to extract the code (pattern Xnn) from the beginning of the ref
        potential_code = cat_ref[:3]
        if potential_code not in cats_by_key:
            raise CellError(
                s,
                r,
                "G",
                cat_ref,
                f"Categoría '{cat_ref}' no existe, y el código extraído "
                f"'{potential_code}' tampoco. "
                f"Usa el código (ej. 'E01') o el nombre completo (ej. 'E01. Comida').",
            )
        category = cats_by_key[potential_code]
    else:
        category = cats_by_key[cat_ref]

    # Resolve source and target based on entry type
    def _get_account(ref: str, col: str) -> Account:
        if ref not in accounts_by_name:
            raise CellError(
                s,
                r,
                col,
                ref,
                f"Cuenta '{ref}' no encontrada. "
                f"Disponibles: {sorted(accounts_by_name)}",
            )
        return accounts_by_name[ref]

    def _get_or_create_counterpart(name: str) -> Counterpart:
        if name not in counterparts_by_name:
            counterparts_by_name[name] = Counterpart(name=name)
        return counterparts_by_name[name]

    if ent_type == +1:  # income:   source=Counterpart, target=Account
        source = _get_or_create_counterpart(src_ref)
        target = _get_account(tgt_ref, "F")
    elif ent_type == -1:  # expense: source=Account,     target=Counterpart
        source = _get_account(src_ref, "E")
        target = _get_or_create_counterpart(tgt_ref)
    else:  # transfer: both Accounts
        source = _get_account(src_ref, "E")
        target = _get_account(tgt_ref, "F")

    return Entry(
        mwid=_mwid(row.get("MWID"), s, r, "A"),
        amount=_money(row.get("Importe"), s, r, "D"),
        date=_date(row.get("Fecha"), s, r, "B"),
        ent_type=ent_type,
        source=source,
        target=target,
        category=category,
        item=_str(row.get("Concepto"), s, r, "H"),  # "" → model sets "Sin concepto"
        details=_restore_newlines(row.get("Detalles")),
        is_bill=_bool(row.get("Es factura"), s, r, "J", default=False),
    )


# Public API


def import_(
    cls: Type["Wallet"],
    path: str | Path,
    *,
    validate: bool = False,
) -> "Wallet":
    """Construct a Wallet from an Excel workbook.

    Reads the three visible sheets (Cuentas, Categorías, Movimientos)
    and builds a fresh Wallet instance. Fails fast on the first invalid
    cell, with a message including sheet, row and column.

    If `validate` is True, the capital computed from the reconstructed
    wallet must match (within 0.01 €) the canonical totals stored in
    the hidden '__meta__' sheet; raises ValidationError otherwise.

    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {path}")

    wb = load_workbook(path, data_only=True)

    # Optional __meta__ reading (required only for validate=True)
    meta_info = None
    if _META_SHEET_NAME in wb.sheetnames:
        meta_info = _read_meta(wb[_META_SHEET_NAME])
        schema = meta_info["metadata"].get("schema")
        if schema is not None and schema not in _META_SCHEMA_SUPPORTED:
            raise ImportError_(
                f"Schema no soportado: '{schema}'. "
                f"Soportados: {_META_SCHEMA_SUPPORTED}"
            )
    elif validate:
        raise ImportError_(
            "validate=True requiere la hoja '__meta__', que no está presente. "
            "El archivo debe haber sido generado por Wallet.to_excel()."
        )

    for sheet in ("Cuentas", "Categorías", "Movimientos"):
        if sheet not in wb.sheetnames:
            raise ImportError_(f"Hoja requerida '{sheet}' no encontrada")

    # --- Build accounts ---
    account_rows = _sheet_rows(
        wb["Cuentas"],
        ["MWID", "Nombre", "Orden", "Color", "Visible", "Legacy"],
    )
    accounts = [_build_account(r) for r in account_rows]
    accounts_by_name = {a.repr_name: a for a in accounts}

    # --- Build categories ---
    category_rows = _sheet_rows(
        wb["Categorías"],
        ["MWID", "Código", "Nombre", "Tipo", "Icono", "Color", "Legacy"],
    )
    categories = [_build_category(r) for r in category_rows]
    # Keyed by both repr_name AND code for flexible resolution
    cats_by_key: dict[str, Category] = {}
    for c in categories:
        cats_by_key[c.repr_name] = c
        cats_by_key[c.code] = c

    # --- Build entries (counterparts created on the fly) ---
    entry_rows = _sheet_rows(
        wb["Movimientos"],
        [
            "MWID",
            "Fecha",
            "Tipo",
            "Importe",
            "Origen",
            "Destino",
            "Categoría",
            "Concepto",
            "Detalles",
            "Es factura",
        ],
    )
    counterparts_by_name: dict[str, Counterpart] = {}
    entries = [
        _build_entry(r, accounts_by_name, cats_by_key, counterparts_by_name)
        for r in entry_rows
    ]
    counterparts = list(counterparts_by_name.values())

    # --- Construct wallet ---
    wallet = cls()
    wallet.accounts = accounts
    wallet.categories = categories
    wallet.counterparts = counterparts
    wallet.entries = entries
    wallet.source_path = (
        Path(meta_info["metadata"]["source_path"])
        if meta_info and meta_info["metadata"].get("source_path")
        else None
    )

    # --- Optional capital validation ---
    if validate:
        got_total, got_per_acc = compute_capital(wallet)
        expected_total = float(meta_info["metadata"]["total_capital"])
        expected_per_acc = meta_info["per_account_capital"]

        discrepancies = []
        if abs(got_total - expected_total) > _CAPITAL_TOLERANCE:
            discrepancies.append(
                f"Capital total: esperado {expected_total:.2f}, "
                f"calculado {got_total:.2f} "
                f"(diff {got_total - expected_total:+.2f})"
            )
        for name, expected in expected_per_acc.items():
            got = got_per_acc.get(name)
            if got is None:
                discrepancies.append(f"Cuenta '{name}' presente en meta pero ausente")
                continue
            if abs(got - expected) > _CAPITAL_TOLERANCE:
                discrepancies.append(
                    f"Cuenta {name}: esperado {expected:.2f}, "
                    f"calculado {got:.2f} (diff {got - expected:+.2f})"
                )
        if discrepancies:
            raise ValidationError(
                "Validación de capital fallida:\n  " + "\n  ".join(discrepancies)
            )

    return wallet
