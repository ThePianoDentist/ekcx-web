#!/usr/bin/env python3
"""
Generate 2025 standings from race results.

This script reads Excel files from results/2025/ and generates standings HTML files.
"""

import pandas as pd
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any
import difflib

# Points system for Seniors/U23 and Veteran Open 40/50
POINTS = {
    1: 100,
    2: 94,
    3: 90,
    4: 86,
    5: 83,
    6: 80,
    7: 78,
    8: 76,
    9: 74,
    10: 72,
    11: 70,
    12: 69,
}


def calculate_points(position: int) -> int:
    """Calculate points for a given position."""
    if position in POINTS:
        return POINTS[position]
    elif position > 12:
        # After position 12, reduce by 1 point per place
        return max(0, 69 - (position - 12))
    return 0


def normalize_name(name: str) -> str:
    """Normalize a name by removing extra spaces and converting to uppercase."""
    if pd.isna(name) or name == "":
        return ""
    # Remove extra spaces, convert to uppercase
    name = re.sub(r'\s+', ' ', str(name).strip())
    return name.upper()


def normalize_first_name(name: str) -> str:
    """Normalize a first name by removing extra spaces and converting to titlecase."""
    if pd.isna(name) or name == "":
        return ""
    # Remove extra spaces, convert to titlecase
    name = re.sub(r'\s+', ' ', str(name).strip())
    return name.title()


def normalize_category(category: str) -> str:
    """Normalize category values: Masters 40/50/60 to Ma40/Ma50/Ma60."""
    if pd.isna(category) or category == "":
        return ""
    category = str(category).strip()
    # Match patterns like "Masters 40", "Masters 50", "Masters 60", etc.
    # Case-insensitive matching
    category_lower = category.lower()
    if re.match(r'^masters\s+(\d+)$', category_lower):
        match = re.match(r'^masters\s+(\d+)$', category_lower)
        age = match.group(1)
        return f'Ma{age}'
    # Also handle variations like "Masters40", "Masters 40 Open", etc.
    if re.match(r'^masters\s*(\d+)', category_lower):
        match = re.match(r'^masters\s*(\d+)', category_lower)
        age = match.group(1)
        return f'Ma{age}'
    return category


def normalize_team_name(team: str, team_normalizations: Dict[str, str]) -> str:
    """Normalize team name, checking against known normalizations."""
    if pd.isna(team) or team == "":
        return ""
    team = str(team).strip()
    # Check if we have a known normalization (case-insensitive exact match first)
    team_upper = team.upper()
    for original, normalized in team_normalizations.items():
        if team_upper == original.upper():
            return normalized
    # Then check for substring matches
    for original, normalized in team_normalizations.items():
        if team_upper in original.upper() or original.upper() in team_upper:
            return normalized
    return team


def find_similar_teams(teams: set, threshold: float = 0.8) -> List[Tuple[str, str]]:
    """Find similar team names that might need normalization."""
    teams_list = sorted(list(teams))
    similar = []
    for i, team1 in enumerate(teams_list):
        for team2 in teams_list[i+1:]:
            if team1 and team2:
                # Calculate similarity
                similarity = difflib.SequenceMatcher(None, team1.upper(), team2.upper()).ratio()
                if similarity >= threshold:
                    similar.append((team1, team2))
    return similar


def read_race_result(file_path: Path) -> pd.DataFrame:
    """Read a race result Excel file and return a cleaned DataFrame."""
    try:
        # Try reading with header at row 4 (0-indexed)
        df = pd.read_excel(file_path, header=4)
        
        # Find the actual column indices
        if 'Unnamed: 0' in df.columns:
            # Map unnamed columns to proper names based on position
            col_map = {}
            for i, col in enumerate(df.columns):
                if i == 0:
                    col_map[col] = 'Pos'
                elif i == 1:
                    col_map[col] = 'Bib'
                elif i == 2:
                    col_map[col] = 'Last Name'
                elif i == 3:
                    col_map[col] = 'First Name'
                elif i == 4:
                    col_map[col] = 'Team'
                elif i == 5:
                    col_map[col] = 'Category'
                elif i == 6:
                    col_map[col] = 'Gender'
                else:
                    # Skip extra columns
                    continue
            df = df[list(col_map.keys())].copy()
            df = df.rename(columns=col_map)
        else:
            # Already has proper column names
            required_cols = ['Pos', 'Bib', 'Last Name', 'First Name', 'Team', 'Category', 'Gender']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                print(f"Warning: Missing columns in {file_path}: {missing_cols}")
                return pd.DataFrame()
        
        # Filter out rows with invalid positions (DNF, DNS, etc.)
        df = df[df['Pos'].apply(lambda x: pd.notna(x) and str(x).isdigit())]
        if df.empty:
            return pd.DataFrame()
        
        df['Pos'] = df['Pos'].astype(int)
        
        # Clean up the data
        df['Last Name'] = df['Last Name'].fillna('').astype(str)
        df['First Name'] = df['First Name'].fillna('').astype(str)
        df['Team'] = df['Team'].fillna('').astype(str)
        df['Category'] = df['Category'].fillna('').astype(str)
        df['Gender'] = df['Gender'].fillna('').astype(str)
        
        return df
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return pd.DataFrame()


def determine_category_from_filename(filename: str) -> str:
    """Determine the category from the filename. Note: Round number is determined by directory, not filename."""
    filename_lower = filename.lower()
    
    # Map filenames to categories (ignoring R3, R4, R5, R6 in filename - round is determined by directory)
    if 'elite female' in filename_lower or 'elite women' in filename_lower:
        return 'womens'
    elif 'elite open' in filename_lower or 'senior open' in filename_lower or 'senior' in filename_lower:
        return 'mens'
    elif 'under 12' in filename_lower or 'u12' in filename_lower:
        return 'u12'
    elif 'under 16' in filename_lower or 'u16' in filename_lower:
        return 'youth'
    elif 'v40' in filename_lower or 'm40' in filename_lower:
        return 'v40'
    elif 'v50' in filename_lower or 'm50' in filename_lower:
        return 'v50'
    else:
        return 'unknown'


def collect_results(results_dir: Path) -> Dict[str, Dict[str, List[Dict]]]:
    """
    Collect all race results.
    Returns: {category: {round: [result_dict, ...]}}
    """
    all_results = defaultdict(lambda: defaultdict(list))
    
    # Process all round directories (any numeric directory name)
    round_dirs = []
    for item in results_dir.iterdir():
        if item.is_dir() and item.name.isdigit():
            round_dirs.append((int(item.name), item))
    
    # Sort by round number
    for round_num_int, round_dir in sorted(round_dirs):
        round_num = str(round_num_int)
        
        # Process each Excel file in the round directory
        for excel_file in sorted(round_dir.glob('*.xlsx')):
            category = determine_category_from_filename(excel_file.name)
            if category == 'unknown':
                print(f"Warning: Could not determine category for {excel_file.name}")
                continue
            
            df = read_race_result(excel_file)
            if df.empty:
                continue
            
            # Convert to list of dictionaries
            for _, row in df.iterrows():
                gender_val = str(row.get('Gender', '')).strip() if 'Gender' in row else ''
                result = {
                    'round': round_num,
                    'position': int(row['Pos']),
                    'points': calculate_points(int(row['Pos'])),
                    'last_name': normalize_name(row['Last Name']),
                    'first_name': normalize_first_name(row['First Name']),
                    'team': str(row['Team']).strip(),
                    'category': str(row['Category']).strip(),
                    'gender': gender_val,
                }
                all_results[category][round_num].append(result)
    
    return all_results


# Common name variations
NAME_VARIATIONS = {
    'MICHAEL': ['MIKE', 'MICHAE', 'MICHAELL', 'MICHAEAL'],
    'MIKE': ['MICHAEL'],
    'JAMES': ['JIM', 'JIMMY', 'JAME'],
    'JIM': ['JAMES', 'JIMMY'],
    'JIMMY': ['JAMES', 'JIM'],
    'WILLIAM': ['WILL', 'BILL', 'WILLI', 'WILLIAMM'],
    'WILL': ['WILLIAM', 'BILL'],
    'BILL': ['WILLIAM', 'WILL'],
    'ROBERT': ['BOB', 'ROB', 'ROBBERT', 'ROBERTT'],
    'BOB': ['ROBERT', 'ROB'],
    'ROB': ['ROBERT', 'BOB'],
    'RICHARD': ['RICH', 'DICK', 'RICHAR', 'RICHARD'],
    'RICH': ['RICHARD', 'DICK'],
    'DICK': ['RICHARD', 'RICH'],
    'CHRISTOPHER': ['CHRIS', 'CHRISS', 'CHRISTOPH'],
    'CHRIS': ['CHRISTOPHER'],
    'JOHN': ['JON', 'JOHNNY', 'JONNY', 'JOHNNE'],
    'JON': ['JOHN', 'JOHNNY'],
    'JOHNNY': ['JOHN', 'JON', 'JONNY'],
    'JONNY': ['JOHN', 'JON', 'JOHNNY'],
    'JOSEPH': ['JOE', 'JOESEPH'],
    'JOE': ['JOSEPH'],
    'DANIEL': ['DAN', 'DANNIEL'],
    'DAN': ['DANIEL'],
    'MATTHEW': ['MATT', 'MATTEW', 'MATTHE'],
    'MATT': ['MATTHEW'],
    'ANDREW': ['ANDY', 'ANDREW'],
    'ANDY': ['ANDREW'],
    'DAVID': ['DAVE', 'DAIVD'],
    'DAVE': ['DAVID'],
    'STEPHEN': ['STEVE', 'STEVEN', 'STEPHENN'],
    'STEVE': ['STEPHEN', 'STEVEN'],
    'STEVEN': ['STEPHEN', 'STEVE'],
    'ANTHONY': ['TONY', 'ANTHONY'],
    'TONY': ['ANTHONY'],
    'EDWARD': ['ED', 'EDDIE', 'TED'],
    'ED': ['EDWARD', 'EDDIE'],
    'EDDIE': ['EDWARD', 'ED'],
    'TED': ['EDWARD', 'ED'],
    'CHARLES': ['CHARLIE', 'CHUCK', 'CHARLS'],
    'CHARLIE': ['CHARLES', 'CHUCK'],
    'CHUCK': ['CHARLES', 'CHARLIE'],
    'THOMAS': ['TOM', 'THOMAS'],
    'TOM': ['THOMAS'],
    'NICHOLAS': ['NICK', 'NICHOLAS'],
    'NICK': ['NICHOLAS'],
}


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def are_names_similar(name1: str, name2: str, max_distance: int = 1, allow_typos: bool = True) -> bool:
    """Check if two names are similar (accounting for typos and variations)."""
    if not name1 or not name2:
        return False
    
    name1_upper = name1.upper().strip()
    name2_upper = name2.upper().strip()
    
    # Exact match after normalization
    if name1_upper == name2_upper:
        return True
    
    # Check if they're known variations (highest priority - these are definitely the same)
    if name1_upper in NAME_VARIATIONS:
        if name2_upper in NAME_VARIATIONS[name1_upper]:
            return True
    if name2_upper in NAME_VARIATIONS:
        if name1_upper in NAME_VARIATIONS[name2_upper]:
            return True
    
    # For typos, allow for names 4 chars or longer
    # This helps catch cases like HOPE/POPE or STEVENE/STEVEN
    if allow_typos and len(name1_upper) >= 4 and len(name2_upper) >= 4:
        distance = levenshtein_distance(name1_upper, name2_upper)
        # Only allow single character differences, and they must be in similar positions
        if distance == 1:
            # Check if it's a reasonable typo (same length, only one char different)
            if len(name1_upper) == len(name2_upper):
                # Count character differences
                diff_count = sum(c1 != c2 for c1, c2 in zip(name1_upper, name2_upper))
                if diff_count <= 2:  # Allow up to 2 character differences if total edit distance is 1
                    return True
    
    return False


def find_similar_riders(riders: List[Tuple[str, str]]) -> List[Tuple[Tuple[str, str], Tuple[str, str]]]:
    """Find similar rider names that might need normalization."""
    similar = []
    riders_list = sorted(list(riders))
    
    for i, (last1, first1) in enumerate(riders_list):
        for last2, first2 in riders_list[i+1:]:
            if not last1 or not last2 or not first1 or not first2:
                continue
            
            # Both names match exactly
            if last1.upper() == last2.upper() and first1.upper() == first2.upper():
                continue
            
            # Check if one name matches and the other is similar
            last_match = last1.upper() == last2.upper()
            first_match = first1.upper() == first2.upper()
            
            # If one matches exactly and the other is similar, they're likely the same person
            # This is the most reliable case - one name is exact, other has a variation/typo
            if last_match and are_names_similar(first1, first2, allow_typos=True):
                similar.append(((last1, first1), (last2, first2)))
            elif first_match and are_names_similar(last1, last2, allow_typos=True):
                similar.append(((last1, first1), (last2, first2)))
            # Both are similar - but be more conservative here to avoid false matches
            # Only match if both are known variations (not typos)
            elif (are_names_similar(last1, last2, allow_typos=False) and 
                  are_names_similar(first1, first2, allow_typos=False)):
                # Both are variations (not typos) - safe to match
                similar.append(((last1, first1), (last2, first2)))
            # Special case: both first and last names have one-letter differences
            # This catches cases like STEVENE HOPE vs STEVEN POPE
            elif (are_names_similar(last1, last2, allow_typos=True) and 
                  are_names_similar(first1, first2, allow_typos=True)):
                # Both names have typos - check if both have single character differences
                last_distance = levenshtein_distance(last1.upper(), last2.upper())
                first_distance = levenshtein_distance(first1.upper(), first2.upper())
                if last_distance == 1 and first_distance == 1:
                    # Both have exactly one character difference - flag as similar
                    similar.append(((last1, first1), (last2, first2)))
            elif (are_names_similar(last1, last2, allow_typos=True) and 
                  are_names_similar(first1, first2, allow_typos=True) and
                  len(last1) > 6 and len(last2) > 6 and  # Only allow typos in both if surnames are long enough
                  last1[0] == last2[0]):  # First letter must match to avoid false matches like PENYS/DENYS
                # Both have typos but surnames are long and start with same letter - less likely to be false match
                similar.append(((last1, first1), (last2, first2)))
    
    return similar


def resolve_canonical_name(name: Any, normalizations: Dict[Any, Any]) -> Any:
    """Resolve a name through the normalization chain to get the canonical name.
    
    Detects and breaks cycles to prevent infinite loops.
    """
    canonical = name
    visited = set()
    
    while canonical in normalizations:
        # Detect cycle - if we've seen this name before, break to prevent infinite loop
        if canonical in visited:
            break
        visited.add(canonical)
        canonical = normalizations[canonical]
    
    return canonical


def choose_rider_target(rider1: Tuple[str, str], rider2: Tuple[str, str], 
                        counts: Dict[Tuple[str, str], int]) -> Tuple[str, str]:
    """Choose target rider name: frequency > length > alphabetical."""
    count1 = counts.get(rider1, 0)
    count2 = counts.get(rider2, 0)
    
    if count1 > count2:
        return rider1
    elif count2 > count1:
        return rider2
    
    # Equal frequency - use total length (last + first)
    len1 = len(rider1[0]) + len(rider1[1])
    len2 = len(rider2[0]) + len(rider2[1])
    if len1 > len2:
        return rider1
    elif len2 > len1:
        return rider2
    
    # Equal length - use alphabetical (deterministic)
    return rider1 if rider1 > rider2 else rider2


def choose_team_target(team1: str, team2: str, counts: Dict[str, int]) -> str:
    """Choose target team name: frequency > length > alphabetical."""
    count1 = counts.get(team1, 0)
    count2 = counts.get(team2, 0)
    
    if count1 > count2:
        return team1
    elif count2 > count1:
        return team2
    
    # Equal frequency - use length
    if len(team1) > len(team2):
        return team1
    elif len(team2) > len(team1):
        return team2
    
    # Equal length - use alphabetical (deterministic)
    return team1 if team1 > team2 else team2


def normalize_rider_and_team_names(all_results: Dict[str, Dict[str, List[Dict]]]) -> Tuple[Dict, Dict]:
    """Normalize rider names and team names, printing where normalization occurred."""
    rider_normalizations = {}
    team_normalizations = {}
    
    # Predefined team name normalizations (abbreviations, known variations)
    predefined_team_normalizations = {
        'LEC': 'Limited Edition Cycling',
        'lec': 'Limited Edition Cycling',
        'Lec': 'Limited Edition Cycling',
    }
    
    # Collect all unique riders and teams, and count occurrences
    all_riders = set()
    all_teams = set()
    rider_counts = defaultdict(int)
    team_counts = defaultdict(int)
    
    for category_results in all_results.values():
        for round_results in category_results.values():
            for result in round_results:
                rider_key = (result['last_name'], result['first_name'])
                all_riders.add(rider_key)
                rider_counts[rider_key] += 1
                if result['team']:
                    team_name = result['team']
                    all_teams.add(team_name)
                    team_counts[team_name] += 1
    
    # Pass 1: Exact matches after uppercasing (case-insensitive duplicates)
    rider_map = {}
    for last_name, first_name in sorted(all_riders):
        key = (last_name.upper(), first_name.upper())
        original = (last_name, first_name)
        if key not in rider_map:
            rider_map[key] = original
        else:
            # Found exact match - choose target and normalize both
            existing = rider_map[key]
            target = choose_rider_target(original, existing, rider_counts)
            rider_map[key] = target  # Update map to use target
            if original != target:
                rider_normalizations[original] = target
                print(f"Rider normalized (exact match): {original} -> {target}")
            if existing != target:
                rider_normalizations[existing] = target
                print(f"Rider normalized (exact match): {existing} -> {target}")
    
    # Pass 2: Global similarity matching for riders
    riders_list = sorted(list(all_riders))
    similar_riders = find_similar_riders(riders_list)
    
    for (last1, first1), (last2, first2) in similar_riders:
        rider1 = (last1, first1)
        rider2 = (last2, first2)
        
        # Skip if already normalized
        if rider1 in rider_normalizations or rider2 in rider_normalizations:
            continue
        
        # Choose target based on frequency > length > alphabetical
        target = choose_rider_target(rider1, rider2, rider_counts)
        
        # Normalize both to target
        if rider1 != target:
            rider_normalizations[rider1] = target
            print(f"Rider normalized (similar): {rider1} -> {target}")
        if rider2 != target:
            rider_normalizations[rider2] = target
            print(f"Rider normalized (similar): {rider2} -> {target}")
    
    # Pass 3: Global similarity matching for teams
    similar_teams = find_similar_teams(all_teams)
    for team1, team2 in similar_teams:
        # Skip if already normalized
        if team1 in team_normalizations or team2 in team_normalizations:
            continue
        
        # Choose target based on frequency > length > alphabetical
        target = choose_team_target(team1, team2, team_counts)
        
        # Normalize both to target
        if team1 != target:
            team_normalizations[team1] = target
            print(f"Team normalized: '{team1}' -> '{target}'")
        if team2 != target:
            team_normalizations[team2] = target
            print(f"Team normalized: '{team2}' -> '{target}'")
    
    # Pass 4: Add predefined team normalizations
    for original, normalized in predefined_team_normalizations.items():
        if original not in team_normalizations:
            team_normalizations[original] = normalized
            print(f"Team normalized (predefined): '{original}' -> '{normalized}'")
    
    # Apply normalizations to results
    for category_results in all_results.values():
        for round_results in category_results.values():
            for result in round_results:
                # Normalize rider
                rider_key = (result['last_name'], result['first_name'])
                
                # Check exact match first
                normalized_key = (rider_key[0].upper(), rider_key[1].upper())
                if normalized_key in rider_map:
                    normalized_rider = resolve_canonical_name(rider_map[normalized_key], rider_normalizations)
                    if rider_key != normalized_rider:
                        result['last_name'] = normalized_rider[0]
                        result['first_name'] = normalized_rider[1]
                        continue
                
                # Then check similar matches
                if rider_key in rider_normalizations:
                    normalized_rider = resolve_canonical_name(rider_normalizations[rider_key], rider_normalizations)
                    result['last_name'] = normalized_rider[0]
                    result['first_name'] = normalized_rider[1]
                
                # Normalize team
                if result['team']:
                    original_team = result['team']
                    normalized_team = resolve_canonical_name(original_team, team_normalizations)
                    if normalized_team != original_team:
                        result['team'] = normalized_team
    
    return rider_normalizations, team_normalizations


def calculate_standings(all_results: Dict[str, Dict[str, List[Dict]]]) -> Dict[str, List[Dict]]:
    """Calculate standings for each category."""
    standings = {}
    
    for category, category_results in all_results.items():
        # Determine max rounds for this category
        max_rounds = max([int(r) for r in category_results.keys()] + [0], default=0)
        
        # Collect all results for this category
        rider_results = defaultdict(lambda: {'points': [], 'rounds': [], 'last_name': '', 
                                           'first_name': '', 'team': '', 'category': '', 'gender': ''})
        
        for round_num, round_results in sorted(category_results.items()):
            for result in round_results:
                rider_key = (result['last_name'], result['first_name'])
                
                if rider_key not in rider_results:
                    rider_results[rider_key] = {
                        'points': [],
                        'last_name': result['last_name'],
                        'first_name': result['first_name'],
                        'team': result['team'],
                        'category': result['category'],
                        'gender': result.get('gender', ''),
                    }
                
                rider_results[rider_key]['points'].append((round_num, result['points']))
        
        # Convert to standings list
        standings_list = []
        for rider_key, data in rider_results.items():
            # Sort points by round
            points_by_round = {int(r): p for r, p in data['points']}
            all_rounds = sorted([int(r) for r, _ in data['points']])
            
            # Calculate total points
            total_points = sum(p for _, p in data['points'])
            
            # Calculate points excluding lowest
            # If N rounds total, take N-1 highest scores (or all if person has fewer)
            points_list = sorted([p for _, p in data['points']], reverse=True)
            num_rounds_participated = len(points_list)
            
            if max_rounds >= 3:
                # Take (max_rounds - 1) highest scores, or all if person has fewer
                num_to_count = min(max_rounds - 1, num_rounds_participated)
                points_excl_lowest = sum(points_list[:num_to_count])
            else:
                # If less than 3 rounds, just use total points
                points_excl_lowest = total_points
            
            standings_list.append({
                'last_name': data['last_name'],
                'first_name': data['first_name'],
                'team': data['team'],
                'category': data['category'],
                'gender': data.get('gender', ''),
                'points_by_round': points_by_round,
                'all_rounds': all_rounds,
                'total_points': total_points,
                'points_excl_lowest': points_excl_lowest,
            })
        
        # Sort by points_excl_lowest first, then total_points
        standings_list.sort(key=lambda x: (-x['points_excl_lowest'], -x['total_points']))
        standings[category] = standings_list
    
    return standings
    
    return standings


def generate_html_table_row(position: int, rider: Dict, max_rounds: int, is_youth: bool = False) -> str:
    """Generate an HTML table row for a rider."""
    row_style = ' style="background: #CCCCCC;"' if position % 2 == 0 else ''
    
    # Determine if we should show "Points excluding lowest" column (when 3+ rounds)
    show_points_excl_lowest = max_rounds >= 3
    
    # Round columns
    round_cols = []
    for round_num in range(1, max_rounds + 1):
        points = rider['points_by_round'].get(round_num)
        if points is not None:
            round_cols.append(f'		<td align="center"{row_style} sdval="{points}" sdnum="2057;"><font face="Liberation Serif" size=3 color="#000000">{points}</font></td>')
        else:
            round_cols.append(f'		<td align="center"{row_style}><font face="Liberation Serif" size=3 color="#000000"><br></font></td>')
    
    round_cols_str = '\n'.join(round_cols)
    
    team_display = rider['team'] if rider['team'] else '<br>'
    category_display = normalize_category(rider['category']) if rider['category'] else ''
    
    # Points columns - regular points (non-bold), and points excluding lowest (bold) if applicable
    if show_points_excl_lowest:
        points_cols = f'''		<td align="center"{row_style} sdval="{rider['total_points']}" sdnum="2057;"><font face="Liberation Serif" size=3 color="#000000">{rider['total_points']}</font></td>
		<td align="center"{row_style} sdval="{rider['points_excl_lowest']}" sdnum="2057;"><b><font face="Liberation Serif" size=3 color="#000000">{rider['points_excl_lowest']}</font></b></td>'''
    else:
        points_cols = f'		<td align="center"{row_style} sdval="{rider['total_points']}" sdnum="2057;"><font face="Liberation Serif" size=3 color="#000000">{rider['total_points']}</font></td>'
    
    if is_youth:
        gender_display = rider.get('gender', '')
        return f'''	<tr>
		<td height="20" align="left"{row_style} sdval="{position}" sdnum="2057;0;@"><font face="Liberation Serif" size=3 color="#000000">{position}</font></td>
		<td align="left"{row_style}><font face="Liberation Serif" size=3 color="#000000">{rider['last_name']}</font></td>
		<td align="left"{row_style}><font face="Liberation Serif" size=3 color="#000000">{rider['first_name']}</font></td>
		<td align="left"{row_style}><font face="Liberation Serif" size=3 color="#000000">{team_display}</font></td>
		<td align="left"{row_style}><font face="Liberation Serif" size=3 color="#000000">{category_display}</font></td>
		<td align="left"{row_style}><font face="Liberation Serif" size=3 color="#000000">{gender_display}</font></td>
{round_cols_str}
{points_cols}
	</tr>'''
    else:
        return f'''	<tr>
		<td height="20" align="left"{row_style} sdval="{position}" sdnum="2057;0;@"><font face="Liberation Serif" size=3 color="#000000">{position}</font></td>
		<td align="left"{row_style}><font face="Liberation Serif" size=3 color="#000000">{rider['last_name']}</font></td>
		<td align="left"{row_style}><font face="Liberation Serif" size=3 color="#000000">{rider['first_name']}</font></td>
		<td align="left"{row_style}><font face="Liberation Serif" size=3 color="#000000">{team_display}</font></td>
		<td align="left"{row_style}><font face="Liberation Serif" size=3 color="#000000">{category_display}</font></td>
{round_cols_str}
{points_cols}
	</tr>'''


def calculate_max_team_width(standings: List[Dict]) -> int:
    """Calculate the maximum team name length to determine column width."""
    max_length = 0
    for rider in standings:
        if rider.get('team'):
            # Estimate width: roughly 8-10 pixels per character for typical font
            # Add some padding for safety
            team_length = len(rider['team'])
            if team_length > max_length:
                max_length = team_length
    
    # Calculate width: minimum 200px, but scale based on content
    # Use approximately 8-9 pixels per character, with minimum 200px
    if max_length == 0:
        return 200
    # Scale: 8px per char, minimum 200px, but cap at reasonable max
    calculated_width = max(200, min(max_length * 8, 400))
    return calculated_width


def generate_category_html(category: str, standings: List[Dict], max_rounds: int, title: str) -> str:
    """Generate HTML for a category standings table."""
    is_youth = category == 'youth'
    
    # Calculate dynamic team column width
    team_width = calculate_max_team_width(standings)
    
    # Header row
    round_headers = '\n'.join([f'		<td align="center" style="background: #000000; color: white" sdval="{i}" sdnum="2057;0;@"><font face="Liberation Serif" size=3>{i}</font></td>' 
                              for i in range(1, max_rounds + 1)])
    
    # Determine if we should show "Points excluding lowest" column (when 3+ rounds)
    show_points_excl_lowest = max_rounds >= 3
    
    if is_youth:
        points_cols = '<colgroup width="55"></colgroup>' if not show_points_excl_lowest else '<colgroup width="55"></colgroup>\n	<colgroup width="70"></colgroup>'
        points_headers = '<td align="center" style="background: #000000; color: white;" sdnum="2057;0;@"><font face="Liberation Serif" size=3>Points</font></td>' if not show_points_excl_lowest else '<td align="center" style="background: #000000; color: white;" sdnum="2057;0;@"><font face="Liberation Serif" size=3>Points</font></td>\n		<td align="center" style="background: #000000; color: white;" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Points excluding lowest</font></b></td>'
        header = f'''<div>
<h1 class="western">{title}</h1>
<table cellspacing="0" border="0" style="width: 100%;">
	<colgroup width="67"></colgroup>
	<colgroup width="116"></colgroup>
	<colgroup width="90"></colgroup>
	<colgroup width="{team_width}"></colgroup>
	<colgroup width="84"></colgroup>
	<colgroup width="62"></colgroup>
	<colgroup span="{max_rounds}" width="36"></colgroup>
	{points_cols}
	<tr>
		<td height="20" align="left" style="background: #000000; color: white;" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Position</font></b></td>
		<td align="left" style="background: #000000; color: white;" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Last Name</font></b></td>
		<td align="left" style="background: #000000; color: white;" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>First Name</font></b></td>
		<td align="left" style="background: #000000; color: white;" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Team</font></b></td>
		<td align="left" style="background: #000000; color: white;" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Category</font></b></td>
		<td align="left" style="background: #000000; color: white;" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Gender</font></b></td>
{round_headers}
		{points_headers}
	</tr>'''
    else:
        points_cols = '<colgroup width="55"></colgroup>' if not show_points_excl_lowest else '<colgroup width="55"></colgroup>\n	<colgroup width="70"></colgroup>'
        points_headers = '<td align="center" style="background: #000000; color: white" sdnum="2057;0;@"><font face="Liberation Serif" size=3>Points</font></td>' if not show_points_excl_lowest else '<td align="center" style="background: #000000; color: white" sdnum="2057;0;@"><font face="Liberation Serif" size=3>Points</font></td>\n		<td align="center" style="background: #000000; color: white" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Points excluding lowest</font></b></td>'
        header = f'''<div><h1 class="western">{title}</h1>
<table cellspacing="0" border="0" style="width: 100%;">
	<colgroup width="67"></colgroup>
	<colgroup width="116"></colgroup>
	<colgroup width="90"></colgroup>
	<colgroup width="{team_width}"></colgroup>
	<colgroup width="76"></colgroup>
	<colgroup span="{max_rounds}" width="36"></colgroup>
	{points_cols}
	<tr>
		<td height="20" align="left" style="background: #000000; color: white" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Position</font></b></td>
		<td align="left" style="background: #000000; color: white" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Last Name</font></b></td>
		<td align="left" style="background: #000000; color: white" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>First Name</font></b></td>
		<td align="left" style="background: #000000; color: white" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Team</font></b></td>
		<td align="left" style="background: #000000; color: white" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Category</font></b></td>
{round_headers}
		{points_headers}
	</tr>'''
    
    # Rows
    rows = []
    for position, rider in enumerate(standings, 1):
        rows.append(generate_html_table_row(position, rider, max_rounds, is_youth))
    
    footer = '''</table>
'''
    
    return header + '\n'.join(rows) + footer


def calculate_team_standings(all_results: Dict[str, Dict[str, List[Dict]]], 
                            category_standings: Dict[str, List[Dict]]) -> List[Dict]:
    """Calculate team standings across all categories."""
    team_points = defaultdict(lambda: {
        'womens': 0,
        'mens': 0,
        'u12': 0,
        'youth': 0,
        'v40': 0,
        'v50': 0,
        'total': 0,
    })
    
    # Sum up points by team for each category
    category_mapping = {
        'womens': 'womens',
        'mens': 'mens',
        'u12': 'u12',
        'youth': 'youth',
        'v40': 'v40',
        'v50': 'v50',
    }
    
    for category, standings_list in category_standings.items():
        mapped_category = category_mapping.get(category)
        if not mapped_category:
            continue
        
        for rider in standings_list:
            team = rider['team']
            if not team:
                continue
            
            # Use points excluding lowest
            points = rider['points_excl_lowest']
            team_points[team][mapped_category] += points
            team_points[team]['total'] += points
    
    # Convert to list and sort
    team_standings = []
    for team, points_dict in team_points.items():
        team_standings.append({
            'team': team,
            **points_dict,
        })
    
    team_standings.sort(key=lambda x: -x['total'])
    
    return team_standings


def generate_teams_html(team_standings: List[Dict]) -> str:
    """Generate HTML for team standings table."""
    # Calculate dynamic team column width
    max_length = 0
    for team_data in team_standings:
        if team_data.get('team'):
            team_length = len(team_data['team'])
            if team_length > max_length:
                max_length = team_length
    
    # Calculate width: minimum 200px, but scale based on content
    if max_length == 0:
        team_width = 200
    else:
        team_width = max(200, min(max_length * 8, 400))
    
    header = f'''<div><h2>Teams</h2></div>
<table cellspacing="0" border="0" style="width: 100%;">
	<colgroup width="67"></colgroup>
	<colgroup width="{team_width}"></colgroup>
	<colgroup width="98"></colgroup>
	<colgroup width="86"></colgroup>
	<colgroup span="2" width="77"></colgroup>
	<colgroup span="2" width="45"></colgroup>
	<colgroup width="55"></colgroup>
	<tr>
		<td height="20" align="left" style="background: #000000; color: white" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Position</font></b></td>
		<td align="left" style="background: #000000; color: white" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Team</font></b></td>
		<td align="center" style="background: #000000; color: white" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Women</font></b></td>
		<td align="center" style="background: #000000; color: white" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Senior Open</font></b></td>
		<td align="center" style="background: #000000; color: white" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Under 12</font></b></td>
		<td align="center" style="background: #000000; color: white" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Under 16</font></b></td>
		<td align="center" style="background: #000000; color: white" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>V40</font></b></td>
		<td align="center" style="background: #000000; color: white" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>V50</font></b></td>
		<td align="center" style="background: #000000; color: white" sdnum="2057;0;@"><b><font face="Liberation Serif" size=3>Points</font></b></td>
	</tr>'''
    
    rows = []
    for position, team_data in enumerate(team_standings, 1):
        row_style = ' style="background: #CCCCCC;"' if position % 2 == 0 else ''
        
        def format_cell(value):
            if value == 0:
                return f'<font face="Liberation Serif" size=3 color="#000000"><br></font>'
            else:
                return f'<font face="Liberation Serif" size=3 color="#000000">{value}</font>'
        
        rows.append(f'''	<tr>
		<td height="20" align="left"{row_style} sdnum="2057;0;@"><font face="Liberation Serif" size=3 color="#000000">{position}</font></td>
		<td align="left"{row_style}><font face="Liberation Serif" size=3 color="#000000">{team_data['team']}</font></td>
		<td align="center"{row_style} sdval="{team_data['womens']}" sdnum="2057;">{format_cell(team_data['womens'])}</td>
		<td align="center"{row_style} sdval="{team_data['mens']}" sdnum="2057;">{format_cell(team_data['mens'])}</td>
		<td align="center"{row_style} sdval="{team_data['u12']}" sdnum="2057;">{format_cell(team_data['u12'])}</td>
		<td align="center"{row_style} sdval="{team_data['youth']}" sdnum="2057;">{format_cell(team_data['youth'])}</td>
		<td align="center"{row_style} sdval="{team_data['v40']}" sdnum="2057;">{format_cell(team_data['v40'])}</td>
		<td align="center"{row_style} sdval="{team_data['v50']}" sdnum="2057;">{format_cell(team_data['v50'])}</td>
		<td align="center"{row_style} sdval="{team_data['total']}" sdnum="2057;"><b><font face="Liberation Serif" size=3 color="#000000">{team_data['total']}</font></b></td>
	</tr>''')
    
    footer = '''</table>
'''
    
    return header + '\n'.join(rows) + footer


def main():
    """Main function to generate standings."""
    # Get project root (parent of scripts directory)
    project_root = Path(__file__).parent.parent
    results_dir = project_root / 'results' / '2025'
    output_dir = project_root / 'templates' / 'standings' / '2025'
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Collecting race results...")
    all_results = collect_results(results_dir)
    
    print("\nNormalizing rider and team names...")
    rider_normalizations, team_normalizations = normalize_rider_and_team_names(all_results)
    
    print("\nCalculating standings...")
    category_standings = calculate_standings(all_results)
    
    # Determine max rounds
    max_rounds = max((max([int(r) for r in rounds.keys()] + [0]) 
                     for rounds in all_results.values()), default=2)
    
    # Category titles
    category_titles = {
        'mens': 'Senior Open',
        'womens': 'Women',
        'youth': 'Youth U16/U14',
        'u12': 'Under 12',
        'v40': 'Veteran 40 Open',
        'v50': 'Veteran 50 Open',
    }
    
    # Generate HTML files for each category
    print("\nGenerating HTML files...")
    for category, standings_list in category_standings.items():
        title = category_titles.get(category, category)
        html_content = generate_category_html(category, standings_list, max_rounds, title)
        
        output_file = output_dir / f'{category}.html'
        output_file.write_text(html_content)
        print(f"Generated {output_file}")
    
    # Generate team standings
    print("\nCalculating team standings...")
    team_standings = calculate_team_standings(all_results, category_standings)
    
    teams_html = generate_teams_html(team_standings)
    teams_file = output_dir / 'teams.html'
    teams_file.write_text(teams_html)
    print(f"Generated {teams_file}")
    
    print("\nDone!")
    print(f"\nSummary:")
    print(f"  Categories processed: {len(category_standings)}")
    print(f"  Total riders: {sum(len(s) for s in category_standings.values())}")
    print(f"  Total teams: {len(team_standings)}")
    if rider_normalizations:
        print(f"  Rider normalizations: {len(rider_normalizations)}")
    if team_normalizations:
        print(f"  Team normalizations: {len(team_normalizations)}")


if __name__ == '__main__':
    main()

