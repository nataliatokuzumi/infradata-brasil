"""Ad-hoc exploration of the SICRO silver Parquet data in Blob Storage.

No dbt build required — connects straight to the silver/ prefix, so it
reflects whatever's in Blob Storage right now. One view per report_type
(materiais, equipamentos, mao_de_obra), matching transform/models/staging.

Usage:
    python transform/scripts/explore_silver.py                     # summary per report_type
    python transform/scripts/explore_silver.py "select * from materiais limit 10"
    python transform/scripts/explore_silver.py "select state_slug, avg(preco_unitario) from materiais group by 1"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import duckdb

from connectors.common.config import azure_storage_connection_string, azure_storage_container
from connectors.sicro.parse.classify import REPORT_TYPES
from connectors.sicro.parse.settings import silver_prefix


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL azure; LOAD azure;")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    # Not logged/printed anywhere below — keep it that way (see docs/... on
    # the Azure key that leaked into a dbt log earlier).
    con.execute(f"SET azure_storage_connection_string = '{azure_storage_connection_string}'")

    for report_type in REPORT_TYPES:
        # union_by_name: mao_de_obra has two column layouts (pre/post the
        # 2025 SICRO change) coexisting in the same glob.
        con.execute(
            f"""
            CREATE VIEW {report_type} AS
            SELECT * FROM read_parquet(
                'azure://{azure_storage_container}/{silver_prefix}/report_type={report_type}/**/*.parquet',
                union_by_name = true
            )
            """
        )

    return con


def print_summary(con: duckdb.DuckDBPyConnection) -> None:
    for report_type in REPORT_TYPES:
        print(f"\n=== {report_type} ===")
        con.sql(
            f"""
            SELECT
                count(*) AS rows,
                count(DISTINCT state_slug) AS states,
                min(year) AS min_year,
                max(year) AS max_year
            FROM {report_type}
            """
        ).show()
        con.sql(f"SELECT * FROM {report_type} LIMIT 5").show()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "sql",
        nargs="?",
        help="SQL to run against the materiais/equipamentos/mao_de_obra views. "
        "Omit for a row-count/sample summary of all three.",
    )
    args = parser.parse_args()

    con = connect()

    if args.sql:
        con.sql(args.sql).show(max_rows=200)
    else:
        print_summary(con)


if __name__ == "__main__":
    main()
