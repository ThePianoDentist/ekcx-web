# PRD: Ingest name review gate

## Problem

Uploading a result file immediately rebuilt standings with silent rider/team merges.

## Outcome

- Upload → `pending_review` → review screen → Confirm (Apply checkboxes default on) or re-upload and confirm.
- Cross-season `rider_name_rules` / `club_name_rules` (seeded predefined merges). Unchecked **Known** rows skip that rule for this confirm’s season rebuild only (rule stays in DB).
- Re-upload of ingested file: CSV diff + overwrite checkbox on review.
- Admin list links original CSV (v1) and latest CSV (vN). Confirm appends a version when accepted name changes alter the file.
- Rule delete UI: later.

## Flow

Only `ingest_status=ingested` exports feed standings; the file under review is included for similarity context via `extra_export_ids`.