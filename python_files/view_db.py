import argparse
import sqlite3
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent if APP_DIR.name == "python_files" else APP_DIR
DB_PATH = PROJECT_ROOT / "data" / "database.db"


def shorten(value, max_length=70):
    text = "" if value is None else str(value)
    return text if len(text) <= max_length else text[: max_length - 3] + "..."


def print_table(headers, rows):
    rows = [[shorten(cell) for cell in row] for row in rows]
    widths = [
        max(len(str(header)), *(len(row[index]) for row in rows)) if rows else len(str(header))
        for index, header in enumerate(headers)
    ]

    line = "-+-".join("-" * width for width in widths)
    print(" | ".join(str(header).ljust(widths[index]) for index, header in enumerate(headers)))
    print(line)

    if not rows:
        print("(no rows)")
        return

    for row in rows:
        print(" | ".join(row[index].ljust(widths[index]) for index in range(len(headers))))


def get_tables(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [row[0] for row in cursor.fetchall()]


def show_table(cursor, table_name, limit):
    cursor.execute(f"PRAGMA table_info({table_name})")
    headers = [column[1] for column in cursor.fetchall()]

    if not headers:
        print(f"\nTable not found: {table_name}")
        return

    cursor.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,))
    rows = cursor.fetchall()

    print(f"\nTable: {table_name}")
    print_table(headers, rows)


def main():
    parser = argparse.ArgumentParser(description="View SQLite database tables.")
    parser.add_argument("table", nargs="?", help="Optional table name to view")
    parser.add_argument("--limit", type=int, default=30, help="Rows per table")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    tables = get_tables(cursor)
    if not tables:
        print("No tables found.")
        conn.close()
        return

    if args.table:
        show_table(cursor, args.table, args.limit)
    else:
        print("Tables:", ", ".join(tables))
        for table in tables:
            show_table(cursor, table, args.limit)

    conn.close()


if __name__ == "__main__":
    main()
