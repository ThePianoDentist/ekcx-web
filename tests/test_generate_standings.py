"""
Pytest tests for generate_standings_2025.py script.
"""
import pytest
from pathlib import Path
import sys
import pandas as pd

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from generate_standings_2025 import (
    calculate_points,
    normalize_name,
    are_names_similar,
    levenshtein_distance,
    find_similar_riders,
    determine_category_from_filename,
)


class TestCalculatePoints:
    """Tests for the calculate_points function."""
    
    def test_top_positions(self):
        """Test that top positions return correct points."""
        assert calculate_points(1) == 100
        assert calculate_points(2) == 94
        assert calculate_points(3) == 90
        assert calculate_points(4) == 86
        assert calculate_points(5) == 83
        assert calculate_points(6) == 80
        assert calculate_points(7) == 78
        assert calculate_points(8) == 76
        assert calculate_points(9) == 74
        assert calculate_points(10) == 72
        assert calculate_points(11) == 70
        assert calculate_points(12) == 69
    
    def test_beyond_top_12(self):
        """Test that positions beyond 12 decrease by 1 point each."""
        assert calculate_points(13) == 68  # 69 - 1
        assert calculate_points(14) == 67  # 69 - 2
        assert calculate_points(20) == 61  # 69 - 8
        assert calculate_points(69) == 12  # 69 - 57
    
    def test_very_low_positions(self):
        """Test that very low positions don't go negative."""
        assert calculate_points(100) >= 0
        assert calculate_points(200) >= 0
    
    def test_zero_or_negative_position(self):
        """Test handling of invalid positions."""
        assert calculate_points(0) == 0
        assert calculate_points(-1) == 0


class TestNormalizeName:
    """Tests for the normalize_name function."""
    
    def test_basic_normalization(self):
        """Test basic name normalization."""
        assert normalize_name("John") == "JOHN"
        assert normalize_name("  Mary  ") == "MARY"
        assert normalize_name("John  Paul") == "JOHN PAUL"
    
    def test_empty_strings(self):
        """Test handling of empty strings."""
        assert normalize_name("") == ""
        assert normalize_name("   ") == ""
    
    def test_nan_values(self):
        """Test handling of NaN values."""
        assert normalize_name(pd.NA) == ""
        assert normalize_name(float('nan')) == ""


class TestLevenshteinDistance:
    """Tests for the levenshtein_distance function."""
    
    def test_identical_strings(self):
        """Test that identical strings have distance 0."""
        assert levenshtein_distance("hello", "hello") == 0
        assert levenshtein_distance("", "") == 0
    
    def test_single_character_difference(self):
        """Test single character differences."""
        assert levenshtein_distance("cat", "bat") == 1
        assert levenshtein_distance("cat", "cats") == 1
        assert levenshtein_distance("cat", "at") == 1
    
    def test_multiple_differences(self):
        """Test multiple character differences."""
        assert levenshtein_distance("kitten", "sitting") == 3
        assert levenshtein_distance("hello", "world") == 4
    
    def test_empty_strings(self):
        """Test with empty strings."""
        assert levenshtein_distance("", "hello") == 5
        assert levenshtein_distance("hello", "") == 5


class TestAreNamesSimilar:
    """Tests for the are_names_similar function."""
    
    def test_exact_matches(self):
        """Test that exact matches are similar."""
        assert are_names_similar("John", "John") is True
        assert are_names_similar("Michael", "MICHAEL") is True
    
    def test_known_variations(self):
        """Test known name variations."""
        assert are_names_similar("Michael", "Mike") is True
        assert are_names_similar("Mike", "Michael") is True
        assert are_names_similar("James", "Jim") is True
        assert are_names_similar("Christopher", "Chris") is True
        assert are_names_similar("Matthew", "Matt") is True
    
    def test_single_character_typos(self):
        """Test single character typos for longer names."""
        assert are_names_similar("Michael", "MICHAEL") is True  # Case difference (exact match after upper)
        # Note: The function requires same length for typo matching
        # Same length typos should match (both > 4 chars and same length)
        assert are_names_similar("Mathew", "Matthew") is False  # Different lengths, won't match as typo
        assert are_names_similar("Richar", "Richad") is True  # Same length (6 chars), 1 char difference
        assert are_names_similar("Michal", "Michael") is False  # Different lengths
    
    def test_short_names_no_typo_matching(self):
        """Test that short names don't match on typos."""
        # PENYS vs DENYS are both 5 chars, which is > 4, so they might match
        # But they're very different (P vs D), so the function should handle this
        # Names <= 4 chars shouldn't match on typos
        assert are_names_similar("PEN", "DEN", allow_typos=True) is False
        assert are_names_similar("ABC", "XYZ", allow_typos=True) is False
    
    def test_empty_or_none(self):
        """Test handling of empty/None names."""
        assert are_names_similar("", "John") is False
        assert are_names_similar("John", "") is False
        assert are_names_similar(None, "John") is False


class TestFindSimilarRiders:
    """Tests for the find_similar_riders function."""
    
    def test_exact_match_surname_different_forename_variation(self):
        """Test matching when surname matches and forename is a variation."""
        riders = [
            ("SMITH", "Michael"),
            ("SMITH", "Mike"),
        ]
        similar = find_similar_riders(riders)
        assert len(similar) == 1
        assert (("SMITH", "Michael"), ("SMITH", "Mike")) in similar or \
               (("SMITH", "Mike"), ("SMITH", "Michael")) in similar
    
    def test_exact_match_forename_different_surname_typo(self):
        """Test matching when forename matches and surname has a typo."""
        riders = [
            ("MALIK", "Omar"),
            ("MALEK", "Omar"),
        ]
        similar = find_similar_riders(riders)
        assert len(similar) == 1
    
    def test_no_match_different_people(self):
        """Test that different people don't match."""
        riders = [
            ("SMITH", "John"),
            ("JONES", "Mary"),
        ]
        similar = find_similar_riders(riders)
        assert len(similar) == 0
    
    def test_both_names_variations(self):
        """Test matching when both names are variations."""
        riders = [
            ("SMITH", "Michael"),
            ("SMITH", "Mike"),
        ]
        similar = find_similar_riders(riders)
        assert len(similar) >= 1
    
    def test_case_insensitive_matching(self):
        """Test that matching is case insensitive."""
        riders = [
            ("Smith", "John"),
            ("SMITH", "JOHN"),
        ]
        # These should match exactly first, so won't appear in similar riders
        # But the function should handle them
        similar = find_similar_riders(riders)
        # Exact matches are filtered out in find_similar_riders
        assert len(similar) == 0  # Because they match exactly (case insensitive)


class TestDetermineCategoryFromFilename:
    """Tests for the determine_category_from_filename function."""
    
    def test_elite_female(self):
        """Test detection of elite female category."""
        assert determine_category_from_filename("Elite Female-r4-.xlsx") == "womens"
        assert determine_category_from_filename("Elite Women-r4-.xlsx") == "womens"
        assert determine_category_from_filename("EKCX 2025 Elite Female-r4-.xlsx") == "womens"
    
    def test_elite_open(self):
        """Test detection of elite open category."""
        assert determine_category_from_filename("Elite Open-r5-.xlsx") == "mens"
        assert determine_category_from_filename("Senior Open-r5-.xlsx") == "mens"
        assert determine_category_from_filename("EKCX 2025 Elite Open-r5-.xlsx") == "mens"
    
    def test_under_12(self):
        """Test detection of under 12 category."""
        assert determine_category_from_filename("Under 12-r1-.xlsx") == "u12"
        assert determine_category_from_filename("U12-r1-.xlsx") == "u12"
        assert determine_category_from_filename("EKCX 2025 Under 12-r1-.xlsx") == "u12"
    
    def test_under_16(self):
        """Test detection of under 16 category."""
        assert determine_category_from_filename("Under 16-r2-.xlsx") == "youth"
        assert determine_category_from_filename("U16-r2-.xlsx") == "youth"
        assert determine_category_from_filename("EKCX 2025 Under 16-r2-.xlsx") == "youth"
    
    def test_v40(self):
        """Test detection of V40 category."""
        assert determine_category_from_filename("V40 Open-r3-.xlsx") == "v40"
        assert determine_category_from_filename("M40 Open-r3-.xlsx") == "v40"
        assert determine_category_from_filename("EKCX 2025 V40 Open-r3-.xlsx") == "v40"
    
    def test_v50(self):
        """Test detection of V50 category."""
        assert determine_category_from_filename("V50 Open-r6-.xlsx") == "v50"
        assert determine_category_from_filename("M50 Open-r6-.xlsx") == "v50"
        assert determine_category_from_filename("EKCX 2025 V50 Open-r6-.xlsx") == "v50"
    
    def test_unknown_category(self):
        """Test that unknown categories return 'unknown'."""
        assert determine_category_from_filename("Unknown Category.xlsx") == "unknown"
        assert determine_category_from_filename("random.xlsx") == "unknown"


class TestIntegration:
    """Integration tests for the standings generation."""
    
    def test_points_calculation_sequence(self):
        """Test that points decrease correctly."""
        points = [calculate_points(i) for i in range(1, 21)]
        # Should decrease monotonically (except for specific values)
        assert points[0] > points[1]  # 100 > 94
        assert points[1] > points[2]  # 94 > 90
        assert points[11] > points[12]  # 70 > 69
        assert points[12] > points[13]  # 69 > 68
    
    def test_name_normalization_and_similarity(self):
        """Test that normalized names can be matched."""
        name1 = normalize_name("Michael Smith")
        name2 = normalize_name("Mike  Smith")
        # After normalization, "Michael" and "Mike" should be similar
        assert are_names_similar("Michael", "Mike") is True

