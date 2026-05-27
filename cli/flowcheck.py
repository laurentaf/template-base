"""
FlowCheck — Pipeline debugging CLI.

Trace data through Medallion layers, inspect quality, profile tables.

Usage:
    uv run python -m cli.flowcheck trace <table>
    uv run python -m cli.flowcheck status
    uv run python -m cli.flowcheck profile <table>
    uv run python -m cli.flowcheck quality <table>
"""

import argparse
from pathlib import Path

import duckdb

from src.tools.database import safe_column, safe_layer, safe_table

DATA_DIR = Path("data")


def fmt(val):
    if val is None:
        return "—"
    return str(val)


def cmd_status(args):
    print("=" * 60)
    print("FlowCheck — Pipeline Health Dashboard")
    print("=" * 60)

    layers = {
        "Bronze": "data/bronze.duckdb",
        "Silver": "data/silver.duckdb",
        "Gold": "data/gold.duckdb",
    }

    for name, db_path in layers.items():
        path = Path(db_path)
        if not path.exists():
            print(f"\n{name}: ❌ Not found")
            continue
        con = duckdb.connect(str(path))
        tables = con.execute(
            "SELECT table_name, table_schema "
            "FROM information_schema.tables "
            "WHERE table_type = 'BASE TABLE'"
        ).fetchall()
        print(f"\n{name}: ✅ ({path.stat().st_size / 1024:.1f} KB)")
        for t in tables:
            tref = f"{safe_layer(t[1])}.{safe_table(t[0])}"
            count = con.execute(f"SELECT count(*) FROM {tref}").fetchone()[0]
            cols = con.execute(
                "SELECT count(*) FROM information_schema.columns WHERE table_name = ?",
                [t[0]],
            ).fetchone()[0]
            print(f" {t[0]} ({t[1]}): {count} rows, {cols} columns")
        con.close()

    sample_dir = DATA_DIR / "sample"
    if sample_dir.exists():
        files = list(sample_dir.glob("*"))
        total_kb = sum(f.stat().st_size for f in files) / 1024
        print(f"\nSample data: {len(files)} files, {total_kb:.1f} KB")


def cmd_trace(args):
    table = args.table
    print(f"Tracing '{table}' through pipeline...\n")
    layers = {
        "Bronze": "data/bronze.duckdb",
        "Silver": "data/silver.duckdb",
        "Gold": "data/gold.duckdb",
    }
    for name, db_path in layers.items():
        path = Path(db_path)
        if not path.exists():
            print(f"{name}: ❌ Not available")
            continue
        con = duckdb.connect(str(path))
        try:
            tref = f"{safe_layer(name.lower())}.{safe_table(table)}"
            rows = con.execute(f"SELECT count(*) FROM {tref}").fetchone()[0]
            cols = con.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = ? AND table_schema = ?",
                [table, name.lower()],
            ).fetchall()
            print(f"{name}: ✅ {rows} rows")
            for col, dtype in cols:
                print(f" {col}: {dtype}")
        except Exception:
            print(f"{name}: ⚠️ Not found")
        con.close()


def cmd_profile(args):
    table = args.table
    layer = args.layer or "silver"
    db_path = DATA_DIR / f"{layer}.duckdb"
    if not db_path.exists():
        print(f"❌ {db_path} not found. Run the pipeline first.")
        return
    con = duckdb.connect(str(db_path))
    try:
        cols = con.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = ? AND table_schema = ?",
            [table, layer],
        ).fetchall()
        tref = f"{safe_layer(layer)}.{safe_table(table)}"
        total_rows = con.execute(f"SELECT count(*) FROM {tref}").fetchone()[0]
        print(f"Table: {layer}.{table} — {total_rows} rows\n")
        for col, dtype in cols:
            qcol = safe_column(col)
            nulls = con.execute(f"SELECT count(*) FROM {tref} WHERE {qcol} IS NULL").fetchone()[0]
            distinct = con.execute(f"SELECT count(DISTINCT {qcol}) FROM {tref}").fetchone()[0]
            null_pct = round(nulls / total_rows * 100, 1) if total_rows else 0
            print(
                f" {col:25s} {dtype:15s} "
                f"nulls: {nulls:>5d} ({null_pct:>4.1f}%) "
                f"distinct: {distinct}"
            )
    except Exception as e:
        print(f"❌ Error: {e}")
    con.close()


def cmd_quality(args):
    table = args.table
    layer = args.layer or "silver"
    db_path = DATA_DIR / f"{layer}.duckdb"
    if not db_path.exists():
        print(f"❌ {db_path} not found.")
        return
    con = duckdb.connect(str(db_path))
    try:
        cols = con.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = ? AND table_schema = ?",
            [table, layer],
        ).fetchall()
        checks = [("not_null", c[0]) for c in cols]
        print(f"Quality checks for {layer}.{table}:\n")
        tref = f"{safe_layer(layer)}.{safe_table(table)}"
        passed = 0
        for rule, col in checks:
            try:
                qcol = safe_column(col)
                failed = con.execute(
                    f"SELECT count(*) FROM {tref} WHERE {qcol} IS NULL"
                ).fetchone()[0]
                ok = failed == 0
                marker = "✅" if ok else "❌"
                print(f" {marker} {col} {rule} (failures: {failed})")
                if ok:
                    passed += 1
            except Exception as e:
                print(f" ⚠️ {col} {rule}: {e}")
        print(f"\n{passed}/{len(checks)} checks passed")
    except Exception as e:
        print(f"❌ Error: {e}")
    con.close()


def main():
    parser = argparse.ArgumentParser(description="FlowCheck — Pipeline Debugging CLI")
    sub = parser.add_subparsers()

    p_status = sub.add_parser("status", help="Health dashboard")
    p_status.set_defaults(func=cmd_status)

    p_trace = sub.add_parser("trace", help="Trace table through layers")
    p_trace.add_argument("table")
    p_trace.set_defaults(func=cmd_trace)

    p_profile = sub.add_parser("profile", help="Profile table columns")
    p_profile.add_argument("table")
    p_profile.add_argument("--layer", default="silver")
    p_profile.set_defaults(func=cmd_profile)

    p_quality = sub.add_parser("quality", help="Run quality checks")
    p_quality.add_argument("table")
    p_quality.add_argument("--layer", default="silver")
    p_quality.set_defaults(func=cmd_quality)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
