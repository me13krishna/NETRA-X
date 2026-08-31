"""
Lightweight additive migrations.

`Base.metadata.create_all()` creates missing *tables*, but never adds a column
to a table that already exists. So adding the retraction columns to Evidence
worked on a fresh database and failed on every existing one with
"table evidence has no column named retracted_at".

This applies additive ALTER TABLE statements idempotently, which is the whole
migration surface this project needs -- no column is ever dropped or retyped.
Anything beyond that should go to Alembic rather than grow here.
"""

from typing import Dict, List, Tuple

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# table -> [(column, SQL type)]
ADDITIVE_COLUMNS: Dict[str, List[Tuple[str, str]]] = {
    "evidence": [
        ("retracted_at", "DATETIME"),
        ("retracted_by", "VARCHAR(36)"),
        ("retraction_reason", "TEXT"),
    ],
}


def apply(engine: Engine) -> List[str]:
    """Add any missing columns. Returns the changes made."""
    applied: List[str] = []
    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())

    with engine.begin() as conn:
        for table, columns in ADDITIVE_COLUMNS.items():
            if table not in existing_tables:
                continue
            present = {c["name"] for c in insp.get_columns(table)}
            for name, sql_type in columns:
                if name in present:
                    continue
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))
                applied.append(f"{table}.{name}")
    return applied
