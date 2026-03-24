#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "snowflake-connector-python>=3.6.0",
#     "cryptography>=42.0.0",
# ]
# ///
"""Deploy Streamlit app files to Snowflake SiS stage."""

import glob
import os
from pathlib import Path
from upload_to_snowflake import create_connection, write_ok, write_info, write_fail

STAGE = "CLAUDE_USAGE_DB.LAYER3.CLAUDE_DASHBOARD_STAGE"
APP_DIR = Path(__file__).parent.parent / "snowflake" / "app"


def main():
    conn = create_connection()
    cur = conn.cursor()

    # Ensure schema and stage exist
    cur.execute("USE SCHEMA CLAUDE_USAGE_DB.LAYER3")
    cur.execute(
        "CREATE STAGE IF NOT EXISTS CLAUDE_DASHBOARD_STAGE "
        "DIRECTORY = (ENABLE = TRUE) "
        "COMMENT = 'Streamlit in Snowflake アプリファイル置き場'"
    )

    py_files = sorted(APP_DIR.glob("*.py"))
    write_info(f"Deploying {len(py_files)} files to @{STAGE}")
    print()

    for f in py_files:
        local_path = str(f).replace("\\", "/")
        put_sql = (
            f"PUT 'file://{local_path}' '@{STAGE}' "
            f"AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
        )
        try:
            cur.execute(put_sql)
            result = cur.fetchall()
            status = result[0][6] if result and len(result[0]) > 6 else "OK"
            write_ok(f"{f.name} -> {status}")
        except Exception as e:
            write_fail(f"{f.name}: {e}")

    print()

    # List files on stage
    write_info("Files on stage:")
    cur.execute(f"LIST @{STAGE}")
    for row in cur.fetchall():
        print(f"  {row[0]} ({row[1]} bytes)")

    cur.close()
    conn.close()
    write_ok("Deploy complete!")


if __name__ == "__main__":
    main()
