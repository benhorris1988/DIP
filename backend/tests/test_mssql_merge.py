"""Unit tests for the MSSQL MERGE SQL builder.

We can't easily spin up a SQL Server in CI, but the SQL string is the
contract. These tests pin its shape so regressions show up immediately.
"""

from __future__ import annotations

import pytest

from app.connectors.destinations.mssql import MssqlDestination, build_merge_sql


def test_merge_sql_single_key():
    sql = build_merge_sql(
        schema="dbo",
        table="dim_customer",
        cols=["customer_key", "customer_name", "country_code"],
        keys=["customer_key"],
    )
    assert "MERGE [dbo].[dim_customer]" in sql
    assert "USING #dip_stage" in sql
    assert "ON tgt.[customer_key] = src.[customer_key]" in sql
    # Non-key columns appear in UPDATE SET, not in the ON clause.
    assert "WHEN MATCHED THEN UPDATE SET" in sql
    assert "tgt.[customer_name] = src.[customer_name]" in sql
    assert "tgt.[country_code] = src.[country_code]" in sql
    assert "WHEN NOT MATCHED BY TARGET THEN" in sql
    # Insert column list includes every column, including the key.
    assert "INSERT ([customer_key],[customer_name],[country_code])" in sql


def test_merge_sql_composite_key():
    sql = build_merge_sql(
        schema="sales",
        table="fact_order_lines",
        cols=["order_id", "line_id", "qty", "amount"],
        keys=["order_id", "line_id"],
    )
    assert "ON tgt.[order_id] = src.[order_id] AND tgt.[line_id] = src.[line_id]" in sql
    assert "tgt.[qty] = src.[qty]" in sql
    assert "tgt.[amount] = src.[amount]" in sql
    # Key columns must not appear in the SET clause.
    assert "tgt.[order_id] = src.[order_id]" not in sql.split("WHEN MATCHED")[1]
    assert "tgt.[line_id] = src.[line_id]" not in sql.split("WHEN MATCHED")[1]


def test_merge_sql_all_keys_no_update():
    """If every column is a key, MATCHED has nothing to update — the
    statement skips the UPDATE clause entirely so the server doesn't
    complain about an empty SET."""
    sql = build_merge_sql(
        schema="dbo",
        table="bridge_xy",
        cols=["x", "y"],
        keys=["x", "y"],
    )
    assert "WHEN MATCHED" not in sql
    assert "WHEN NOT MATCHED BY TARGET THEN" in sql


async def test_upsert_requires_key_columns():
    dest = MssqlDestination(
        config={"host": "h", "database": "d"},
        secrets={"user": "u", "password": "p"},
    )
    with pytest.raises(ValueError, match="key_columns"):
        await dest.write("t", [{"a": 1}], mode="upsert", key_columns=None)


async def test_upsert_rejects_missing_keys():
    dest = MssqlDestination(
        config={"host": "h", "database": "d"},
        secrets={"user": "u", "password": "p"},
    )
    with pytest.raises(ValueError, match="not present"):
        await dest.write(
            "t",
            [{"a": 1, "b": 2}],
            mode="upsert",
            key_columns=["missing_col"],
        )


async def test_empty_records_is_noop():
    dest = MssqlDestination(
        config={"host": "h", "database": "d"},
        secrets={"user": "u", "password": "p"},
    )
    written = await dest.write("t", [], mode="upsert", key_columns=["a"])
    assert written == 0
