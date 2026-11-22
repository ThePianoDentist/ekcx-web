"""Read the published standings HTML tables into plain rows."""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Dict, List, Optional


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: List[List[List[str]]] = []
        self._rows: Optional[List[List[str]]] = None
        self._row: Optional[List[str]] = None
        self._cell: Optional[List[str]] = None

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ARG002
        if tag == "table":
            self._rows = []
        elif tag == "tr" and self._rows is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
        elif tag == "br" and self._cell is not None:
            self._cell.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._row is not None and self._cell is not None:
            text = "".join(self._cell).strip()
            self._row.append(text)
            self._cell = None
        elif tag == "tr" and self._rows is not None and self._row is not None:
            if any(self._row):
                self._rows.append(self._row)
            self._row = None
        elif tag == "table" and self._rows is not None:
            self.tables.append(self._rows)
            self._rows = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def _first_table(html: str) -> List[List[str]]:
    parser = _TableParser()
    parser.feed(html)
    if not parser.tables:
        return []
    return parser.tables[0]


def _blank_int(text: str) -> Optional[int]:
    if text == "":
        return None
    return int(text)


def parse_rider_standings(html: str) -> List[dict]:
    """Rider rows: name, team, per-round points, total, and points excluding lowest."""
    table = _first_table(html)
    if not table or table[0][0] != "Position":
        return []
    header = table[0]
    round_cols = {index: int(label) for index, label in enumerate(header) if label.isdigit()}
    total_at = header.index("Points")
    excl_at = header.index("Points excluding lowest") if "Points excluding lowest" in header else None
    last_at = header.index("Last Name")
    first_at = header.index("First Name")
    team_at = header.index("Team")

    rows = []
    for cells in table[1:]:
        rounds: Dict[int, Optional[int]] = {}
        for index, round_num in round_cols.items():
            rounds[round_num] = _blank_int(cells[index]) if index < len(cells) else None
        rows.append(
            {
                "position": int(cells[0]),
                "last_name": cells[last_at],
                "first_name": cells[first_at],
                "team": cells[team_at],
                "rounds": rounds,
                "total": int(cells[total_at]),
                "excl": int(cells[excl_at]) if excl_at is not None else int(cells[total_at]),
            }
        )
    return rows


def parse_team_standings(html: str) -> List[dict]:
    """Team rows. A blank points cell is zero, matching the generator."""
    table = _first_table(html)
    if not table or table[0][0] != "Position":
        return []
    header = table[0]
    rows = []
    for cells in table[1:]:
        points = {}
        for index, label in enumerate(header):
            if label in ("Position", "Team"):
                continue
            value = _blank_int(cells[index]) if index < len(cells) else None
            points[label] = 0 if value is None else value
        rows.append(
            {
                "position": int(cells[0]),
                "team": cells[header.index("Team")],
                "points": points,
            }
        )
    return rows
