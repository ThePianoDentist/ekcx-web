from pathlib import Path
from typing import Dict

from app.domain.results import build_results_sections, save_results_to_json


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    results_root = project_root / 'results'
    if not results_root.exists():
        print("No results directory found; nothing to generate.")
        return

    # Discover available years/rounds from the results directory
    discovered: Dict[int, list] = {}
    for year_dir in sorted([p for p in results_root.iterdir() if p.is_dir()]):
        try:
            year = int(year_dir.name)
        except ValueError:
            continue
        rounds = []
        for round_dir in sorted([p for p in year_dir.iterdir() if p.is_dir()]):
            try:
                rnd = int(round_dir.name)
            except ValueError:
                continue
            rounds.append(rnd)
        if rounds:
            discovered[year] = rounds

    if not discovered:
        print("No year/round directories found under results/; nothing to generate.")
        return

    total_sections = 0
    for year, rounds in discovered.items():
        for rnd in rounds:
            sections = build_results_sections(year, rnd)
            save_results_to_json(year, rnd, sections)
            total_sections += len(sections)
            print(f"Saved {len(sections)} sections for {year} round {rnd}")

    print(f"Done. Wrote sections for {len(discovered)} year(s); total sections: {total_sections}")


if __name__ == "__main__":
    main()




