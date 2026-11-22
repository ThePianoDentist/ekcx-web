"""Predefined rider/club normalisation rules seeded into the database."""

from __future__ import annotations

from typing import List, Tuple

# (raw_last, raw_first) -> (canonical_last, canonical_first), category (None = all)
PREDEFINED_RIDER_RULES: List[Tuple[Tuple[str, str], Tuple[str, str], str | None]] = [
    (("BRADFORD", "OLLIE"), ("BRADFORD", "Oliver"), None),
    (("MALPASS", "JO"), ("MALPASS", "Joanne"), None),
    (("SPURRIER", "BEN"), ("SPURRIER", "Benedict"), None),
    (("BURT", "RANDOLPOH"), ("BURT", "Randolph"), None),
    (("CALEIA-RAMOS", "NATASHA"), ("CALDAR-RAMOS", "Natasha"), None),
    (("DE WILDE", "ADAM"), ("DE WILDE-GREY", "Adam"), None),
    (("DEWILDE-GREY", "ADAM"), ("DE WILDE-GREY", "Adam"), None),
    (("DE WILDE-GRAY", "ADAM"), ("DE WILDE-GREY", "Adam"), None),
    (("NICHOLSON", "Hannah"), ("MERRINGTON", "Hannah"), None),
    (("MERINGTON", "Hannah"), ("MERRINGTON", "Hannah"), None),
    (("MERRINGTON", "Hannah"), ("MERRINGTON", "Hannah"), None),
    (("PETERSMAN", "Daniel"), ("PETERSMANN", "Danielle"), None),
    (("PETERSMANN", "Daniel"), ("PETERSMANN", "Danielle"), None),
    (("PETERSMAN", "Danielle"), ("PETERSMANN", "Danielle"), None),
]

PREDEFINED_CLUB_RULES: List[Tuple[str, str]] = [
    ("LEC", "Limited Edition Cycling"),
    ("lec", "Limited Edition Cycling"),
    ("Lec", "Limited Edition Cycling"),
    ("VCL", "VC Londres"),
    ("Vcl", "VC Londres"),
    ("vcl", "VC Londres"),
    ("SDW", "Southborough & District Whls"),
    ("Sdw", "Southborough & District Whls"),
    ("sdw", "Southborough & District Whls"),
    ("Morden CC", "Morden Cycle Racing Club"),
    ("SFA", "San Fairy Ann CC"),
    ("Sfa", "San Fairy Ann CC"),
    ("sfa", "San Fairy Ann CC"),
    ("Bigfoot Youth Cycle Club Ltd", "Bigfoot CC"),
    ("Kingston", "Kingston Wheelers CC"),
    ("Southborough", "Southborough & District Whls"),
]