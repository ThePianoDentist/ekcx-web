"""Clean CrossMgr race tables into scored rows."""

from __future__ import annotations

import pandas as pd

from app.results.domain.positions import classify_position


def prepare_race_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Drop DNS, blank chips, and DNF rows; normalise name columns."""
    required_cols = ["Pos", "Last Name", "First Name", "Team", "Category"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return pd.DataFrame()

    df = df[
        df["Pos"].apply(
            lambda value: pd.notna(value)
            and classify_position(value) in ("finished", "dnf")
        )
    ].copy()
    if df.empty:
        return df

    def _has_name(value) -> bool:
        if pd.isna(value):
            return False
        text = str(value).strip()
        return bool(text) and text.lower() != "nan"

    scored = df["Last Name"].apply(_has_name) | df["First Name"].apply(_has_name)
    if not scored.any():
        return pd.DataFrame()
    df = df.loc[scored].copy()
    df["_dnf"] = df["Pos"].apply(lambda value: classify_position(value) == "dnf")
    df.loc[df["_dnf"], "Pos"] = pd.NA
    finish_mask = ~df["_dnf"]
    if finish_mask.any():
        df.loc[finish_mask, "Pos"] = pd.to_numeric(
            df.loc[finish_mask, "Pos"],
            errors="coerce",
        )
    df.drop(columns=["_dnf"], inplace=True)

    df["Last Name"] = df["Last Name"].fillna("").astype(str)
    df["First Name"] = df["First Name"].fillna("").astype(str)
    df["Team"] = df["Team"].fillna("").astype(str)
    df["Category"] = df["Category"].fillna("").astype(str)
    if "Gender" not in df.columns:
        df["Gender"] = ""
    else:
        df["Gender"] = df["Gender"].fillna("").astype(str)
    return df