import os
from src.core.telemetry import setup_observability
from src.tools.database import get_duckdb_connection

setup_observability("sota-data-engine")

def run_poc():
    con = get_duckdb_connection()
    con.execute("CREATE TABLE IF NOT EXISTS ledger (id INTEGER, task VARCHAR, status VARCHAR)")
    con.execute("INSERT INTO ledger VALUES (1, 'Initialize Project', 'COMPLETED')")
    df = con.execute("SELECT * FROM ledger").df()
    print(df)

if __name__ == "__main__":
    run_poc()
