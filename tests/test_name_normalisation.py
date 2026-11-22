from __future__ import annotations

from app.participants.domain.name_normalisation import (
    LoadedRules,
    apply_stored_rules_to_results,
    build_stored_maps,
    new_suggestions,
)


def test_stored_rider_rule_applies():
    # Setup:
    rules = LoadedRules(
        rider_rows=[],
        club_rows=[],
    )
    from app.participants.data.models import RiderNameRule

    rules.rider_rows.append(
        RiderNameRule(
            raw_last_name="BRADFORD",
            raw_first_name="Ollie",
            canonical_last_name="BRADFORD",
            canonical_first_name="Oliver",
            category="",
            source="predefined",
        )
    )
    all_results = {
        "mens": {
            "1": [
                {
                    "round": "1",
                    "last_name": "BRADFORD",
                    "first_name": "Ollie",
                    "team": "VC Deal",
                    "position": 1,
                    "points": 100,
                    "dnf": False,
                    "category": "Ma40",
                    "gender": "M",
                }
            ]
        }
    }

    # Run:
    apply_stored_rules_to_results(all_results, rules)

    # Check:
    row = all_results["mens"]["1"][0]
    assert row["first_name"] == "Oliver"


def test_similarity_suggestions_do_not_auto_apply():
    # Setup:
    rules = LoadedRules(rider_rows=[], club_rows=[])
    all_results = {
        "mens": {
            "1": [
                {
                    "round": "1",
                    "last_name": "SMITH",
                    "first_name": "Mike",
                    "team": "A",
                    "position": 1,
                    "points": 100,
                    "dnf": False,
                    "category": "",
                    "gender": "M",
                }
            ],
            "2": [
                {
                    "round": "2",
                    "last_name": "SMITH",
                    "first_name": "Michael",
                    "team": "A",
                    "position": 2,
                    "points": 94,
                    "dnf": False,
                    "category": "",
                    "gender": "M",
                }
            ],
        }
    }

    # Run:
    suggestions = new_suggestions(all_results, rules)

    # Check:
    assert all_results["mens"]["1"][0]["first_name"] == "Mike"
    assert any(s.kind == "rider" for s in suggestions)