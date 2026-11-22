from __future__ import annotations

from app.participants.domain.name_normalisation import (
    LoadedRules,
    NameSuggestion,
    _rider_context,
    apply_stored_rules_to_results,
    build_stored_maps,
    build_stored_maps_for_refresh,
    maps_for_accepted,
    new_suggestions,
)
from app.participants.data.models import RiderNameRule


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


def test_maps_for_accepted_skips_unchecked_stored():
    # Setup:
    stored = [
        NameSuggestion(
            id="stored-rider:BRADFORD:Ollie",
            kind="rider",
            reason="stored",
            source="BRADFORD, Ollie",
            target="BRADFORD, Oliver",
            rounds=["1"],
        )
    ]
    # Run:
    rider_map, _ = maps_for_accepted(stored, set())
    accepted_map, _ = maps_for_accepted(stored, {stored[0].id})
    # Check:
    assert rider_map == {}
    assert accepted_map[("BRADFORD", "Ollie")] == ("BRADFORD", "Oliver")


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


def test_unchecked_stored_rule_dropped_for_refresh():
    # Setup:
    rules = LoadedRules(
        rider_rows=[
            RiderNameRule(
                raw_last_name="MALPASS",
                raw_first_name="JO",
                canonical_last_name="MALPASS",
                canonical_first_name="Joanne",
                category="",
                source="predefined",
            )
        ],
        club_rows=[],
    )
    stored = [
        NameSuggestion(
            id="stored-rider:MALPASS:Jo",
            kind="rider",
            reason="stored",
            source="MALPASS, Jo",
            target="MALPASS, Joanne",
            rounds=["2"],
        )
    ]

    # Run:
    accepted, _ = build_stored_maps_for_refresh(rules, stored, stored[0].id)
    ignored, _ = build_stored_maps_for_refresh(rules, stored, set())

    # Check:
    assert ("MALPASS", "Jo") in accepted
    assert ("MALPASS", "Jo") not in ignored


def test_rider_context_clubs_include_rounds_per_club():
    # Setup:
    all_results = {
        "womens": {
            "1": [
                {
                    "round": "1",
                    "last_name": "MALPASS",
                    "first_name": "Joanne",
                    "team": "VC Deal",
                    "position": 1,
                    "points": 100,
                    "dnf": False,
                    "category": "",
                    "gender": "W",
                }
            ],
            "2": [
                {
                    "round": "2",
                    "last_name": "MALPASS",
                    "first_name": "Jo",
                    "team": "VC Deal",
                    "position": 3,
                    "points": 90,
                    "dnf": False,
                    "category": "",
                    "gender": "W",
                },
                {
                    "round": "2",
                    "last_name": "JO",
                    "first_name": "Jo",
                    "team": "Other CC",
                    "position": 4,
                    "points": 86,
                    "dnf": False,
                    "category": "",
                    "gender": "W",
                },
            ],
        }
    }

    # Run:
    _rounds, clubs = _rider_context(all_results, ("MALPASS", "Jo"))

    # Check:
    assert clubs == ["VC Deal (2)"]
    _rounds2, clubs2 = _rider_context(all_results, ("MALPASS", "Joanne"))
    assert clubs2 == ["VC Deal (1)"]