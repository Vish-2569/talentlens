"""Decision recording — validates and appends to the Decision table.

NOT under engine/ because it performs I/O through db.py.
Append-only: no updates or deletes.
"""
from __future__ import annotations

import hashlib
import json

from backend.db import Database

VALID_VERBS = {"Approve", "Modify", "Reject"}


def inputs_hash(parsed_json: dict, relaxed_mask: str,
                options_json: dict) -> str:
    """SHA-256 of canonical JSON of what the approver saw."""
    payload = {
        "parsed": parsed_json,
        "relaxed_mask": relaxed_mask,
        "options": options_json,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def record_decision(
    db: Database,
    req_id: str,
    option_id: str,
    verb: str,
    relaxed_mask: str,
    decided_by: str,
    reason: str,
    valid_options: list[str],
    parsed_json: dict,
    options_json: dict,
) -> dict:
    """Validate and record a human decision.

    Parameters
    ----------
    db : Database
        Open database connection.
    req_id : str
        Requisition ID; must exist in the Requisition table.
    option_id : str
        Chosen option; must be in *valid_options*.
    verb : str
        One of Approve / Modify / Reject.
    relaxed_mask : str
        Five-character string of 0s and 1s — which constraints were
        relaxed when the approver made the decision.
    decided_by : str
        Approver name (required; no auth in MVP).
    reason : str
        Non-empty reason for the decision.
    valid_options : list[str]
        Allowed option / mix IDs for this requisition.
    parsed_json : dict
        Parsed requisition from the Requisition table.
    options_json : dict
        Option table (five cards + mixes) from the Scenario table
        for the given relaxed_mask.

    Returns
    -------
    dict
        ``{status, req_id, option_id, verb, inputs_hash}``

    Raises
    ------
    ValueError
        On empty reason, empty approver, unknown req_id, invalid
        option_id, or invalid verb.
    """
    cleaned_reason = reason.strip()
    if not cleaned_reason:
        raise ValueError("Reason must not be empty")

    cleaned_by = decided_by.strip()
    if not cleaned_by:
        raise ValueError("Approver name must not be empty")

    if verb not in VALID_VERBS:
        raise ValueError(
            f"Invalid verb: {verb}. Must be one of {sorted(VALID_VERBS)}"
        )

    if db.get_requisition(req_id) is None:
        raise ValueError(f"Requisition {req_id} not found")

    if option_id not in valid_options:
        raise ValueError(f"Invalid option: {option_id}")

    h = inputs_hash(parsed_json, relaxed_mask, options_json)

    chosen = f"{verb} {option_id}"
    db.append_decision(req_id, chosen, cleaned_by, cleaned_reason, h)

    return {
        "status": "recorded",
        "req_id": req_id,
        "option_id": option_id,
        "verb": verb,
        "inputs_hash": h,
    }
