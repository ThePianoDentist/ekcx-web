#!/usr/bin/env python3
"""
Script to update a round: mark as completed, add photos, generate results, and update standings.

This script handles:
1. Updating round status and photos URL in main.py
2. Updating round status in events.html
3. Generating results JSON for the round
4. Regenerating standings with the new round data
"""

from pathlib import Path
import sys
import subprocess


def update_main_py(year: int, round_num: int, photos_url: str) -> None:
    """Update main.py to mark round as completed and add photos URL."""
    main_py_path = Path(__file__).parent.parent / 'main.py'
    
    with open(main_py_path, 'r') as f:
        content = f.read()
    
    # Find the round entry and update it
    round_key = f'{round_num}: {{'
    if round_key not in content:
        print(f"Warning: Could not find round {round_num} in main.py")
        return
    
    # Replace status from "upcoming" to "completed" and add photos_url if not present
    import re
    
    # Pattern to match the round entry
    pattern = rf'({round_num}:\s*{{[^}}]*"status":\s*)"upcoming"'
    replacement = r'\1"completed"'
    content = re.sub(pattern, replacement, content)
    
    # Add photos_url if not present
    if photos_url and f'"photos_url": "{photos_url}"' not in content:
        # Find the round entry and add photos_url before status
        pattern = rf'({round_num}:\s*{{[^}}]*?)(\s*"status":)'
        replacement = rf'\1                "photos_url": "{photos_url}",\n                \2'
        content = re.sub(pattern, replacement, content)
    
    with open(main_py_path, 'w') as f:
        f.write(content)
    
    print(f"✓ Updated main.py for round {round_num}")


def update_events_html(year: int, round_num: int, photos_url: str) -> None:
    """Update events.html to mark round as completed and add photos link."""
    events_html_path = Path(__file__).parent.parent / 'templates' / 'events.html'
    
    with open(events_html_path, 'r') as f:
        content = f.read()
    
    # Find the round section and update status
    import re
    
    # Replace "Upcoming" status with "Completed"
    pattern = rf'(Round {round_num}:[^<]*?<strong>Status:</strong>\s*<span[^>]*>)(Upcoming)(</span>)'
    replacement = r'\1Completed\3'
    content = re.sub(pattern, replacement, content)
    
    # Replace color from green to gray
    pattern = rf'(Round {round_num}:[^<]*?<strong>Status:</strong>\s*<span style="color: #28a745; font-weight: bold;">)'
    replacement = r'<strong>Status:</strong> <span style="color: #666;">'
    content = re.sub(pattern, replacement, content)
    
    # Add photos link if not present
    if photos_url:
        # Check if photos link already exists
        if photos_url not in content:
            # Find the round section and add photos link before closing </p>
            pattern = rf'(Round {round_num}:[^<]*?</a>\s*</p>)'
            replacement = rf'\1\n            <a href="{photos_url}" target="_blank" style="color: #0066cc;">📸 View Photos →</a>'
            content = re.sub(pattern, replacement, content)
    
    with open(events_html_path, 'w') as f:
        f.write(content)
    
    print(f"✓ Updated events.html for round {round_num}")


def generate_results_json() -> None:
    """Generate results JSON for all rounds."""
    script_path = Path(__file__).parent / 'generate_results_json.py'
    result = subprocess.run(['python', str(script_path)], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error generating results JSON: {result.stderr}")
        sys.exit(1)
    
    print("✓ Generated results JSON")


def regenerate_standings() -> None:
    """Regenerate standings with updated round data."""
    script_path = Path(__file__).parent / 'generate_standings_2025.py'
    result = subprocess.run(['python', str(script_path)], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error regenerating standings: {result.stderr}")
        sys.exit(1)
    
    print("✓ Regenerated standings")


def update_round(year: int, round_num: int, photos_url: str) -> None:
    """
    Main function to update a round.
    
    Args:
        year: Year of the round (e.g., 2025)
        round_num: Round number (e.g., 5)
        photos_url: URL to photos gallery
    """
    print(f"Updating round {round_num} for year {year}...")
    print(f"Photos URL: {photos_url}\n")
    
    # Step 1: Update main.py
    update_main_py(year, round_num, photos_url)
    
    # Step 2: Update events.html
    update_events_html(year, round_num, photos_url)
    
    # Step 3: Generate results JSON
    generate_results_json()
    
    # Step 4: Regenerate standings
    regenerate_standings()
    
    print(f"\n✓ Successfully updated round {round_num}!")


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python update_round.py <year> <round_num> <photos_url>")
        print("Example: python update_round.py 2025 5 https://example.com/photos")
        sys.exit(1)
    
    year = int(sys.argv[1])
    round_num = int(sys.argv[2])
    photos_url = sys.argv[3]
    
    update_round(year, round_num, photos_url)

