"""Map CrossMgr export filenames to league category keys."""


def determine_category_from_filename(filename: str) -> str:
    """Round number comes from the event, not the filename."""
    filename_lower = filename.lower()

    if "try cx" in filename_lower or "trycx" in filename_lower:
        return "skip"

    if "elite female" in filename_lower or "women" in filename_lower:
        return "womens"
    if "under 12" in filename_lower or "u12" in filename_lower:
        return "u12"
    if "under 16" in filename_lower or "u16" in filename_lower:
        return "youth"
    if (
        "masters 50" in filename_lower
        or "masters50" in filename_lower
        or "v50" in filename_lower
        or "m50" in filename_lower
    ):
        return "v50"
    if (
        "masters 40" in filename_lower
        or "masters40" in filename_lower
        or "v40" in filename_lower
        or "m40" in filename_lower
    ):
        return "v40"
    if "elite open" in filename_lower or "senior open" in filename_lower or "senior" in filename_lower:
        return "mens"
    return "unknown"