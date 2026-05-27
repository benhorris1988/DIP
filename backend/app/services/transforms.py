"""In-flight record transformation engine.

A pipeline carries an ordered list of *transform steps* (stored on
``Pipeline.transform['steps']``). Each batch of records flowing from a
source to a destination is pushed through the steps in order before it is
written.

Each step is a dict::

    {"type": "rename", "config": {"from": "A", "to": "B"}, "enabled": true}

Steps fall into two families:

* **structural** (``rename``, ``drop``, ``select``, ``set_constant`` …) —
  reshape the record. Bad *config* fails the whole job at compile time;
  these rarely fail on an individual row.
* **row-level** (``cast``, ``string_op``, ``python_column``, ``python_row``,
  ``filter``) — run per record. A row that raises is handled according to
  the pipeline ``on_error`` policy: ``skip`` drops + logs the row, ``fail``
  aborts the whole job.

The ``python_*`` / ``filter`` steps execute user-supplied Python in a
restricted namespace (no ``__import__``, a small builtins whitelist, a few
safe modules). This trims footguns but is **not** a hardened security
sandbox — only operators who are already trusted to define pipelines can
author transforms.
"""

from __future__ import annotations

import builtins
import datetime as _datetime
import json as _json
import math as _math
import re as _re
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

MAX_ERROR_SAMPLE = 50


class TransformError(Exception):
    """Raised when a transform fails and the policy is to fail the job, or
    when a step's configuration is invalid."""


# ---------------------------------------------------------------------------
# Restricted Python execution
# ---------------------------------------------------------------------------

_SAFE_BUILTIN_NAMES = (
    "abs", "all", "any", "ascii", "bin", "bool", "chr", "dict", "divmod",
    "enumerate", "filter", "float", "format", "hex", "int", "isinstance",
    "len", "list", "map", "max", "min", "oct", "ord", "pow", "range", "repr",
    "reversed", "round", "set", "sorted", "str", "sum", "tuple", "zip",
)
_SAFE_BUILTINS = {n: getattr(builtins, n) for n in _SAFE_BUILTIN_NAMES}

# Modules exposed to user code by name.
_SAFE_MODULES: dict[str, Any] = {
    "re": _re,
    "math": _math,
    "json": _json,
    "datetime": _datetime,
    "date": _datetime.date,
    "timedelta": _datetime.timedelta,
}


def _python_globals() -> dict[str, Any]:
    return {"__builtins__": _SAFE_BUILTINS, **_SAFE_MODULES}


def _compile_expr(code: str, what: str) -> Any:
    try:
        return compile(code, f"<{what}>", "eval")
    except SyntaxError as exc:  # pragma: no cover - surfaced as config error
        raise TransformError(f"{what}: syntax error: {exc.msg}") from exc


def _compile_stmts(code: str, what: str) -> Any:
    try:
        return compile(code, f"<{what}>", "exec")
    except SyntaxError as exc:  # pragma: no cover
        raise TransformError(f"{what}: syntax error: {exc.msg}") from exc


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------


def _coerce_scalar(raw: Any) -> Any:
    """Best-effort conversion of a string form value into a typed scalar so
    a constant of ``"0"`` lands as an int and ``"true"`` as a bool."""
    if not isinstance(raw, str):
        return raw
    s = raw.strip()
    low = s.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "none", ""):
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return raw


_TRUTHY = {"1", "true", "t", "yes", "y", "on"}
_FALSY = {"0", "false", "f", "no", "n", "off", ""}


def _to_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value).strip().lower()
    if s in _TRUTHY:
        return True
    if s in _FALSY:
        return False
    raise ValueError(f"cannot interpret {value!r} as boolean")


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(float(value))


def _cast_value(value: Any, to: str) -> Any:
    if value is None:
        return None
    if to in ("string", "str"):
        return str(value)
    if to in ("int", "integer"):
        return _to_int(value)
    if to in ("float", "number", "double"):
        return float(value)
    if to in ("bool", "boolean"):
        return _to_bool(value)
    if to == "date":
        if isinstance(value, _datetime.datetime):
            return value.date().isoformat()
        if isinstance(value, _datetime.date):
            return value.isoformat()
        return _datetime.date.fromisoformat(str(value)[:10]).isoformat()
    if to == "datetime":
        if isinstance(value, _datetime.datetime):
            return value.isoformat()
        return _datetime.datetime.fromisoformat(str(value)).isoformat()
    raise TransformError(f"cast: unknown target type {to!r}")


def _split_columns(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(c).strip() for c in raw if str(c).strip()]
    return [c.strip() for c in str(raw or "").split(",") if c.strip()]


# ---------------------------------------------------------------------------
# Step compilation — turns a step dict into a callable (row) -> row | None.
# Returning None drops the row (used by `filter`).
# ---------------------------------------------------------------------------

CompiledStep = Callable[[dict], dict | None]


def _need(cfg: dict, key: str, step_type: str) -> Any:
    val = cfg.get(key)
    if val is None or (isinstance(val, str) and not val.strip()):
        raise TransformError(f"{step_type}: missing required config '{key}'")
    return val


def _compile_step(step: dict) -> CompiledStep:
    stype = step.get("type")
    cfg = step.get("config") or {}

    if stype == "rename":
        src = _need(cfg, "from", stype)
        dst = _need(cfg, "to", stype)

        def _rename(row: dict) -> dict:
            if src in row:
                row[dst] = row.pop(src)
            return row

        return _rename

    if stype == "drop":
        cols = _split_columns(_need(cfg, "columns", stype))

        def _drop(row: dict) -> dict:
            for c in cols:
                row.pop(c, None)
            return row

        return _drop

    if stype == "select":
        cols = _split_columns(_need(cfg, "columns", stype))

        def _select(row: dict) -> dict:
            return {c: row[c] for c in cols if c in row}

        return _select

    if stype == "set_constant":
        col = _need(cfg, "column", stype)
        value = _coerce_scalar(cfg.get("value"))

        def _const(row: dict) -> dict:
            row[col] = value
            return row

        return _const

    if stype == "fill_null":
        col = _need(cfg, "column", stype)
        value = _coerce_scalar(cfg.get("value"))

        def _fill(row: dict) -> dict:
            if row.get(col) is None:
                row[col] = value
            return row

        return _fill

    if stype == "cast":
        col = _need(cfg, "column", stype)
        to = _need(cfg, "to", stype)

        def _cast(row: dict) -> dict:
            if col in row:
                row[col] = _cast_value(row[col], to)
            return row

        return _cast

    if stype == "string_op":
        col = _need(cfg, "column", stype)
        op = _need(cfg, "op", stype)
        ops: dict[str, Callable[[str], str]] = {
            "upper": str.upper,
            "lower": str.lower,
            "trim": str.strip,
            "strip": str.strip,
            "lstrip": str.lstrip,
            "rstrip": str.rstrip,
            "title": str.title,
            "capitalize": str.capitalize,
        }
        if op not in ops:
            raise TransformError(f"string_op: unknown op {op!r}")
        fn = ops[op]

        def _strop(row: dict) -> dict:
            v = row.get(col)
            if v is not None:
                row[col] = fn(str(v))
            return row

        return _strop

    if stype == "replace":
        col = _need(cfg, "column", stype)
        find = cfg.get("find", "")
        repl = cfg.get("replace", "")
        use_regex = bool(cfg.get("regex", False))
        pattern = _re.compile(find) if use_regex else None

        def _replace(row: dict) -> dict:
            v = row.get(col)
            if v is not None:
                s = str(v)
                row[col] = pattern.sub(repl, s) if pattern else s.replace(find, repl)
            return row

        return _replace

    if stype == "concat":
        target = _need(cfg, "target", stype)
        cols = _split_columns(_need(cfg, "columns", stype))
        sep = cfg.get("separator", "")

        def _concat(row: dict) -> dict:
            parts = [str(row.get(c, "")) if row.get(c) is not None else "" for c in cols]
            row[target] = sep.join(parts)
            return row

        return _concat

    if stype == "python_column":
        col = _need(cfg, "column", stype)
        compiled = _compile_expr(_need(cfg, "code", stype), "python_column")
        g = _python_globals()

        def _pycol(row: dict) -> dict:
            row[col] = eval(compiled, g, {"value": row.get(col), "row": row})  # noqa: S307
            return row

        return _pycol

    if stype == "python_row":
        compiled = _compile_stmts(_need(cfg, "code", stype), "python_row")
        g = _python_globals()

        def _pyrow(row: dict) -> dict:
            local = {"row": row}
            exec(compiled, g, local)  # noqa: S102
            result = local.get("row")
            if not isinstance(result, dict):
                raise TransformError("python_row: 'row' must remain a dict")
            return result

        return _pyrow

    if stype == "filter":
        compiled = _compile_expr(_need(cfg, "code", stype), "filter")
        g = _python_globals()

        def _filter(row: dict) -> dict | None:
            keep = eval(compiled, g, {"row": row})  # noqa: S307
            return row if keep else None

        return _filter

    raise TransformError(f"unknown transform type {stype!r}")


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------


@dataclass
class TransformOutcome:
    records: list[dict]
    failed: int = 0
    filtered: int = 0
    errors: list[dict] = field(default_factory=list)


def _enabled_steps(steps: list[dict]) -> list[dict]:
    return [s for s in steps if s and s.get("enabled", True) and s.get("type")]


def apply_transforms(
    records: list[dict[str, Any]],
    steps: list[dict[str, Any]] | None,
    *,
    on_error: str = "skip",
) -> TransformOutcome:
    """Run ``records`` through ``steps`` in order.

    ``on_error`` is ``"skip"`` (drop + record the offending row and carry on)
    or ``"fail"`` (raise :class:`TransformError`, aborting the batch/job).
    Invalid step configuration always raises regardless of policy.
    """
    steps = _enabled_steps(steps or [])
    if not steps or not records:
        return TransformOutcome(records=records)

    # Compile once; a config error here fails the whole job up front.
    compiled = [_compile_step(s) for s in steps]

    out: list[dict] = []
    outcome = TransformOutcome(records=out)
    for idx, original in enumerate(records):
        row: dict | None = dict(original)
        try:
            for fn in compiled:
                row = fn(row)  # type: ignore[arg-type]
                if row is None:  # dropped by filter
                    outcome.filtered += 1
                    break
        except TransformError:
            raise
        except Exception as exc:  # noqa: BLE001 - user code / data error
            if on_error == "fail":
                raise TransformError(
                    f"row {idx}: {type(exc).__name__}: {exc}"
                ) from exc
            outcome.failed += 1
            if len(outcome.errors) < MAX_ERROR_SAMPLE:
                outcome.errors.append(
                    {
                        "row_index": idx,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
            continue
        if row is not None:
            out.append(row)
    return outcome


# ---------------------------------------------------------------------------
# Catalog — drives the drag-and-drop builder UI and documents each step.
# ---------------------------------------------------------------------------


@dataclass
class TransformField:
    name: str
    label: str
    type: str = "string"  # string | text | code | select | boolean | columns
    required: bool = False
    placeholder: str | None = None
    help: str | None = None
    options: list[str] | None = None
    default: Any = None


@dataclass
class TransformSpec:
    type: str
    label: str
    category: str  # "schema" | "values" | "python" | "rows"
    icon: str
    description: str
    fields: list[TransformField] = field(default_factory=list)
    example: str | None = None


TRANSFORM_CATALOG: list[TransformSpec] = [
    TransformSpec(
        type="rename",
        label="Rename column",
        category="schema",
        icon="rename",
        description="Rename a single column.",
        fields=[
            TransformField("from", "From column", required=True, placeholder="BusinessPartner"),
            TransformField("to", "To column", required=True, placeholder="customer_key"),
        ],
    ),
    TransformSpec(
        type="drop",
        label="Drop columns",
        category="schema",
        icon="drop",
        description="Remove one or more columns from every record.",
        fields=[
            TransformField(
                "columns", "Columns", type="columns", required=True,
                placeholder="col_a, col_b", help="Comma-separated column names.",
            ),
        ],
    ),
    TransformSpec(
        type="select",
        label="Keep only columns",
        category="schema",
        icon="select",
        description="Keep only the listed columns (drops everything else).",
        fields=[
            TransformField(
                "columns", "Columns", type="columns", required=True,
                placeholder="customer_key, customer_name",
                help="Comma-separated column names, in output order.",
            ),
        ],
    ),
    TransformSpec(
        type="cast",
        label="Change type",
        category="values",
        icon="cast",
        description="Convert a column to another data type.",
        fields=[
            TransformField("column", "Column", required=True, placeholder="amount"),
            TransformField(
                "to", "Target type", type="select", required=True,
                options=["string", "int", "float", "bool", "date", "datetime"],
                default="string",
            ),
        ],
    ),
    TransformSpec(
        type="string_op",
        label="String operation",
        category="values",
        icon="string",
        description="Upper/lower/trim and similar text operations on a column.",
        fields=[
            TransformField("column", "Column", required=True, placeholder="country_code"),
            TransformField(
                "op", "Operation", type="select", required=True,
                options=["upper", "lower", "trim", "title", "capitalize", "lstrip", "rstrip"],
                default="trim",
            ),
        ],
    ),
    TransformSpec(
        type="replace",
        label="Find & replace",
        category="values",
        icon="replace",
        description="Replace text inside a column (literal or regular expression).",
        fields=[
            TransformField("column", "Column", required=True),
            TransformField("find", "Find", required=True, placeholder="\\s+"),
            TransformField("replace", "Replace with", placeholder=" "),
            TransformField("regex", "Treat 'find' as regex", type="boolean", default=False),
        ],
    ),
    TransformSpec(
        type="fill_null",
        label="Fill nulls",
        category="values",
        icon="fill",
        description="Replace null/missing values in a column with a default.",
        fields=[
            TransformField("column", "Column", required=True),
            TransformField("value", "Default value", required=True, placeholder="0"),
        ],
    ),
    TransformSpec(
        type="set_constant",
        label="Set constant",
        category="values",
        icon="constant",
        description="Set (or add) a column to a fixed value on every record.",
        fields=[
            TransformField("column", "Column", required=True, placeholder="source_system"),
            TransformField("value", "Value", required=True, placeholder="SAP"),
        ],
    ),
    TransformSpec(
        type="concat",
        label="Concatenate columns",
        category="values",
        icon="concat",
        description="Join several columns into a new target column.",
        fields=[
            TransformField("target", "Target column", required=True, placeholder="full_name"),
            TransformField(
                "columns", "Source columns", type="columns", required=True,
                placeholder="first_name, last_name",
            ),
            TransformField("separator", "Separator", default=" ", placeholder="' '"),
        ],
    ),
    TransformSpec(
        type="python_column",
        label="Python — column value",
        category="python",
        icon="python",
        description=(
            "Compute a column's value with a Python expression. "
            "`value` is the current cell, `row` is the whole record."
        ),
        fields=[
            TransformField("column", "Target column", required=True, placeholder="amount_gbp"),
            TransformField(
                "code", "Python expression", type="code", required=True,
                placeholder="round(float(value or 0) * 1.18, 2)",
                help="An expression returning the new value. `value` and `row` are in scope.",
            ),
        ],
        example=(
            "# Convert USD to GBP and round\n"
            "round(float(value or 0) * 0.79, 2)\n"
            "\n"
            "# Build a value from other columns\n"
            "# f\"{row['city']}, {row['country']}\"\n"
            "\n"
            "# Normalise a code, fall back to UNKNOWN\n"
            "# (value or 'UNKNOWN').strip().upper()"
        ),
    ),
    TransformSpec(
        type="python_row",
        label="Python — whole row",
        category="python",
        icon="python",
        description=(
            "Run Python statements against the whole `row` dict. Mutate `row` "
            "to add, change or remove columns."
        ),
        fields=[
            TransformField(
                "code", "Python statements", type="code", required=True,
                placeholder="row['full_name'] = f\"{row['first']} {row['last']}\"",
                help="Statements that mutate the `row` dict in place.",
            ),
        ],
        example=(
            "# Derive new columns\n"
            "row['full_name'] = f\"{row.get('first','')} {row.get('last','')}\".strip()\n"
            "row['amount_gbp'] = round(float(row.get('amount') or 0) * 0.79, 2)\n"
            "\n"
            "# Drop a column conditionally\n"
            "if not row.get('email'):\n"
            "    row.pop('email', None)\n"
            "\n"
            "# Split a field\n"
            "row['domain'] = (row.get('email') or '').split('@')[-1]"
        ),
    ),
    TransformSpec(
        type="filter",
        label="Filter rows",
        category="rows",
        icon="filter",
        description=(
            "Keep only rows where a Python expression is true. `row` is the "
            "whole record."
        ),
        fields=[
            TransformField(
                "code", "Keep when (expression)", type="code", required=True,
                placeholder="row['status'] == 'active'",
                help="A boolean expression. Rows evaluating to false are dropped.",
            ),
        ],
        example=(
            "# Keep active customers only\n"
            "row.get('status') == 'active'\n"
            "\n"
            "# Numeric threshold\n"
            "# float(row.get('amount') or 0) >= 100\n"
            "\n"
            "# Non-empty key\n"
            "# bool((row.get('customer_key') or '').strip())"
        ),
    ),
]


def catalog_as_dicts() -> list[dict[str, Any]]:
    return [asdict(spec) for spec in TRANSFORM_CATALOG]
