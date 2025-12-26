"""
Script to update round details when an event is completed.

This script automates the process of:
1. Updating the event status from "upcoming" to "completed" in main.py
2. Updating the status display in events.html
3. Generating results JSON from the results folder
4. Optionally adding/updating photos_url

Usage:
    python scripts/update_round_details.py <year> <round_num> [photos_url]

Example:
    python scripts/update_round_details.py 2025 4 https://mattbristow.photoshelter.com/gallery-collection/Round-4-Betteshanger-Park-07-12-2025/C00004TRC4XcNqG8
"""

import re
import sys
from pathlib import Path
from typing import Optional

from app.domain.results import build_results_sections, save_results_to_json


def update_main_py_status(year: int, round_num: int, photos_url: Optional[str] = None) -> bool:
    """Update the status in main.py from 'upcoming' to 'completed' and optionally add photos_url."""
    main_py_path = Path(__file__).resolve().parents[1] / "main.py"
    
    if not main_py_path.exists():
        print(f"Error: {main_py_path} not found")
        return False
    
    content = main_py_path.read_text(encoding='utf-8')
    
    # Find the event entry for this round
    # Pattern to match the round entry: round_num: { ... }
    # We need to find the matching closing brace
    pattern = rf'(\s+){round_num}:\s*\{{'
    match = re.search(pattern, content, re.MULTILINE)
    
    if not match:
        print(f"Error: Could not find round {round_num} in main.py")
        return False
    
    indent = match.group(1)
    start_pos = match.end()
    
    # Find the matching closing brace
    brace_count = 1
    pos = start_pos
    while pos < len(content) and brace_count > 0:
        if content[pos] == '{':
            brace_count += 1
        elif content[pos] == '}':
            brace_count -= 1
        pos += 1
    
    if brace_count != 0:
        print(f"Error: Could not find matching closing brace for round {round_num}")
        return False
    
    event_content = content[start_pos:pos-1]  # -1 to exclude the closing brace
    
    # Update status to "completed"
    if '"status": "upcoming"' in event_content:
        event_content = event_content.replace('"status": "upcoming"', '"status": "completed"')
    elif '"status": "completed"' in event_content:
        print(f"Round {round_num} already marked as completed in main.py")
    else:
        print(f"Warning: Could not find status field in round {round_num}")
    
    # Add or update photos_url
    if photos_url:
        if '"photos_url":' in event_content:
            # Update existing photos_url
            event_content = re.sub(
                r'"photos_url":\s*"[^"]*"',
                f'"photos_url": "{photos_url}"',
                event_content
            )
        else:
            # Add photos_url before status
            # Dictionary entries are indented 4 more spaces than the round number line
            entry_indent = indent + "    "
            if '"status":' in event_content:
                event_content = event_content.replace(
                    f'"status":',
                    f'{entry_indent}"photos_url": "{photos_url}",\n{entry_indent}"status":'
                )
            else:
                # Add at the end before closing brace
                event_content = event_content.rstrip()
                if not event_content.endswith(','):
                    event_content += ','
                event_content += f'\n{entry_indent}"photos_url": "{photos_url}"'
    
    # Replace the matched section
    new_content = content[:match.start()] + f'{indent}{round_num}: {{\n{event_content}\n{indent}}}' + content[pos:]
    
    main_py_path.write_text(new_content, encoding='utf-8')
    print(f"✓ Updated main.py for round {round_num}")
    return True


def update_events_html_status(year: int, round_num: int, photos_url: Optional[str] = None) -> bool:
    """Update the status display in events.html and optionally add photos link."""
    events_html_path = Path(__file__).resolve().parents[1] / "templates" / "events.html"
    
    if not events_html_path.exists():
        print(f"Error: {events_html_path} not found")
        return False
    
    content = events_html_path.read_text(encoding='utf-8')
    original_content = content
    
    # Find the round section - look for the div containing the round
    # Pattern to match the round div starting with the h2 link
    pattern = rf'(<div[^>]*>\s*<h2><a[^>]*>/events/{year}/{round_num}[^<]*</a></h2>.*?</div>\s*</div>)'
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    
    if not match:
        print(f"Error: Could not find round {round_num} section in events.html")
        return False
    
    round_section = match.group(1)
    original_section = round_section
    
    # Update status from "Upcoming" to "Completed"
    if '<span style="color: #28a745; font-weight: bold;">Upcoming</span>' in round_section:
        round_section = round_section.replace(
            '<span style="color: #28a745; font-weight: bold;">Upcoming</span>',
            '<span style="color: #666;">Completed</span>'
        )
    elif '<span style="color: #666;">Completed</span>' in round_section:
        print(f"Round {round_num} already marked as completed in events.html")
    else:
        print(f"Warning: Could not find status span in round {round_num} section")
    
    # Add or update photos link
    if photos_url:
        photos_link = f'<a href="{photos_url}" target="_blank" style="color: #0066cc;">📸 View Photos →</a>'
        
        # Check if photos link already exists
        if '📸 View Photos →' in round_section:
            # Update existing photos link
            round_section = re.sub(
                r'<a href="[^"]*" target="_blank" style="color: #0066cc;">📸 View Photos →</a>',
                photos_link,
                round_section
            )
        else:
            # Add photos link after British Cycling link
            # Find the British Cycling link and add photos link after it
            bc_pattern = r'(<a href="https://www\.britishcycling\.org\.uk[^"]*" target="_blank" style="color: #0066cc;">View on British Cycling →</a>)'
            bc_match = re.search(bc_pattern, round_section)
            if bc_match:
                # Add margin-right to BC link and add photos link
                bc_link = bc_match.group(1)
                bc_link_updated = bc_link.replace(
                    'style="color: #0066cc;">',
                    'style="color: #0066cc; margin-right: 15px;">'
                )
                round_section = round_section.replace(
                    bc_link,
                    f'{bc_link_updated}\n            {photos_link}'
                )
            else:
                # Add at the end of the links paragraph
                round_section = re.sub(
                    r'(</p>)',
                    f'            {photos_link}\n          \\1',
                    round_section,
                    count=1
                )
    
    if round_section != original_section:
        content = content[:match.start()] + round_section + content[match.end():]
        events_html_path.write_text(content, encoding='utf-8')
        print(f"✓ Updated events.html for round {round_num}")
        return True
    else:
        print(f"No changes needed in events.html for round {round_num}")
        return True


def generate_results_json(year: int, round_num: int) -> bool:
    """Generate results JSON from the results folder."""
    results_dir = Path(__file__).resolve().parents[1] / "results" / str(year) / str(round_num)
    
    if not results_dir.exists():
        print(f"Warning: Results directory {results_dir} does not exist")
        return False
    
    sections = build_results_sections(year, round_num)
    if not sections:
        print(f"Warning: No results sections generated for round {round_num}")
        return False
    
    save_results_to_json(year, round_num, sections)
    print(f"✓ Generated {len(sections)} results sections for round {round_num}")
    return True


def update_round_details(year: int, round_num: int, photos_url: Optional[str] = None) -> None:
    """Main function to update all round details."""
    print(f"Updating details for {year} Round {round_num}...")
    if photos_url:
        print(f"Photos URL: {photos_url}")
    print()
    
    success = True
    success &= update_main_py_status(year, round_num, photos_url)
    success &= update_events_html_status(year, round_num, photos_url)
    success &= generate_results_json(year, round_num)
    
    if success:
        print(f"\n✓ Successfully updated all details for {year} Round {round_num}")
    else:
        print(f"\n⚠ Some updates may have failed. Please review the output above.")


def main():
    """Command-line interface."""
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    try:
        year = int(sys.argv[1])
        round_num = int(sys.argv[2])
        photos_url = sys.argv[3] if len(sys.argv) > 3 else None
    except ValueError:
        print("Error: year and round_num must be integers")
        sys.exit(1)
    
    update_round_details(year, round_num, photos_url)


if __name__ == "__main__":
    main()

