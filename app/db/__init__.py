from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "var" / "ekcx.sqlite3"

__all__ = ["DEFAULT_DB_PATH"]