"""CrossMgr exports as licence-stripped CSV text for database storage."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pandas as pd


def is_licence_column(name: object) -> bool:
    text = str(name).strip().lower()
    if text in (
        "licence",
        "license",
        "bc licence",
        "bc license",
        "bc_licence",
        "bc_license",
    ):
        return True
    return "licen" in text


def drop_licence_columns(df: pd.DataFrame) -> pd.DataFrame:
    drops = [column for column in df.columns if is_licence_column(column)]
    if not drops:
        return df
    return df.drop(columns=drops)


def _drop_crossmgr_footer(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    def row_contains_footer(row) -> bool:
        for val in row:
            if isinstance(val, str) and "Powered by CrossMgr" in val:
                return True
        return False

    return df[~df.apply(row_contains_footer, axis=1)]


def _read_csv_path(path: Path) -> pd.DataFrame:
    for enc in (None, "utf-8", "utf-8-sig", "latin-1"):
        try:
            if enc is None:
                return pd.read_csv(path)
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.DataFrame()


def _read_xlsx_path(path: Path) -> pd.DataFrame:
    for header in (5, 4):
        try:
            df = pd.read_excel(path, header=header)
        except Exception:
            continue
        if df.empty:
            continue
        if header == 4 and "Unnamed: 0" in df.columns:
            col_map = {}
            for index, column in enumerate(df.columns):
                if index == 0:
                    col_map[column] = "Pos"
                elif index == 1:
                    col_map[column] = "Bib"
                elif index == 2:
                    col_map[column] = "Last Name"
                elif index == 3:
                    col_map[column] = "First Name"
                elif index == 4:
                    col_map[column] = "Team"
                elif index == 5:
                    col_map[column] = "Category"
                elif index == 6:
                    col_map[column] = "Gender"
                else:
                    continue
            df = df[list(col_map.keys())].copy()
            df = df.rename(columns=col_map)
        return df
    return pd.DataFrame()


def dataframe_to_stored_csv(df: pd.DataFrame) -> str | None:
    df = _drop_crossmgr_footer(df)
    if df.empty:
        return None
    df = drop_licence_columns(df)
    buffer = StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue()


def sanitize_csv_text(text: str) -> str | None:
    try:
        df = pd.read_csv(StringIO(text))
    except Exception:
        return None
    return dataframe_to_stored_csv(df)


def file_to_sanitized_csv(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = _read_csv_path(path)
    elif suffix == ".xlsx":
        df = _read_xlsx_path(path)
    else:
        return None
    return dataframe_to_stored_csv(df)


def round_export_paths(results_dir: Path, round_num: int) -> list[Path]:
    round_dir = results_dir / str(round_num)
    if not round_dir.is_dir():
        return []
    paths = (
        list(round_dir.glob("*.csv"))
        + list(round_dir.glob("*.CSV"))
        + list(round_dir.glob("*.xlsx"))
    )
    return sorted(paths)