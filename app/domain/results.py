from pathlib import Path
import json
from typing import List, Dict, Any

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
RESULTS_JSON_PATH = BASE_DIR / "results.json"


def _clean_results_df(df: pd.DataFrame, preferred_cols: list) -> pd.DataFrame:
    def row_contains_footer(row) -> bool:
        for val in row:
            if isinstance(val, str) and 'Powered by CrossMgr' in val:
                return True
        return False

    if not df.empty:
        df = df[~df.apply(row_contains_footer, axis=1)]

    drops = [
        c
        for c in df.columns
        if str(c).strip().lower() in (
            "licence",
            "license",
            "bc licence",
            "bc license",
            "bc_licence",
            "bc_license",
        )
        or "licen" in str(c).strip().lower()
    ]
    if drops:
        df = df.drop(columns=drops)

    keep = []
    col_map = {}
    for src, disp in preferred_cols:
        if src in df.columns and src not in keep:
            keep.append(src)
            col_map[src] = disp

    if not keep:
        return pd.DataFrame()

    df = df[keep].rename(columns=col_map)
    df = df.dropna(how='all')
    df = df.where(df.notna(), '')
    return df


def _map_filename_to_title(stem: str) -> str:
    name = stem.lower()
    if 'elite female' in name or 'elite women' in name:
        return 'Women'
    if 'elite open' in name or 'senior open' in name or 'senior' in name:
        return 'Senior Open'
    if 'under 12' in name or 'u12' in name:
        return 'Under 12'
    if 'under 16' in name or 'u16' in name:
        return 'Youth U16/U14'
    if 'v40' in name or 'm40' in name:
        return 'Veteran 40 Open'
    if 'v50' in name or 'm50' in name:
        return 'Veteran 50 Open'
    return stem


def build_results_sections(year: int, round_num: int) -> List[Dict[str, Any]]:
    results_sections: List[Dict[str, Any]] = []
    results_dir = Path(__file__).resolve().parents[2] / 'results' / str(year) / str(round_num)
    if not results_dir.exists():
        return results_sections

    base_cols = [
        ('Pos', 'Position'),
        ('Position', 'Position'),
        ('Last Name', 'Last Name'),
        ('Surname', 'Last Name'),
        ('First Name', 'First Name'),
        ('Forename', 'First Name'),
        ('Team', 'Team'),
        ('Club', 'Team'),
        ('Category', 'Category'),
        ('Time', 'Time'),
        ('Gap', 'Gap'),
    ]
    lap_cols = [(f'Lap {i}', f'Lap {i}') for i in range(1, 20)]
    preferred_cols = base_cols + lap_cols

    files = list(results_dir.glob('*.csv')) + list(results_dir.glob('*.CSV')) + list(results_dir.glob('*.xlsx'))
    for path in sorted(files):
        df = pd.DataFrame()
        try:
            if path.suffix.lower() == '.csv':
                for enc in (None, 'utf-8', 'utf-8-sig', 'latin-1'):
                    try:
                        if enc is None:
                            df = pd.read_csv(path)
                        else:
                            df = pd.read_csv(path, encoding=enc)
                        break
                    except Exception:
                        df = pd.DataFrame()
                if df.empty:
                    continue
            else:
                df = pd.read_excel(path, header=5)
        except Exception:
            continue

        df = _clean_results_df(df, preferred_cols)
        if df.empty:
            continue

        table_html = df.to_html(index=False, border=0, classes='event-results-table', na_rep='')
        section_title = _map_filename_to_title(path.stem)
        results_sections.append({'title': section_title, 'html': table_html})

    return results_sections


def save_results_to_json(year: int, round_num: int, sections: List[Dict[str, Any]], json_path: Path = RESULTS_JSON_PATH) -> None:
    payload: Dict[str, Any] = {}
    if json_path.exists():
        try:
            payload = json.loads(json_path.read_text(encoding='utf-8'))
        except Exception:
            payload = {}

    payload.setdefault(str(year), {})[str(round_num)] = sections
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def load_results_from_json(year: int, round_num: int, json_path: Path = RESULTS_JSON_PATH) -> List[Dict[str, Any]]:
    if not json_path.exists():
        return []
    try:
        data = json.loads(json_path.read_text(encoding='utf-8'))
        return data.get(str(year), {}).get(str(round_num), [])
    except Exception:
        return []




