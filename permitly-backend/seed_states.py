
import json
from pathlib import Path

import db


DATA_DIR = Path(__file__).parent / "data" / "state_answer_keys"

STATE_NAMES = {
    "CA": "California",
    "DE": "Delaware",
    "FL": "Florida",
    "IL": "Illinois",
    "KY": "Kentucky",
    "TX": "Texas",
    "WA": "Washington",
}


def seed_states():
    client = db.get_client()
    total = 0

    for file in sorted(DATA_DIR.glob("*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        info = data["record_info"]
        code = info["state"]

        state_row = {
            "code": code,
            "name": STATE_NAMES[code],
            "license_type": info.get("license_type", "money_transmission"),
            "statute": info.get("statute"),
            "source_date": info.get("source_date"),
        }

        # Insert the state first, without updating an existing state.
        client.table("states").upsert(
            state_row,
            on_conflict="code",
            ignore_duplicates=True,
        ).execute()

        # Prepare the licensing requirements for this state.
        rows = []

        for field_name, field in data["fields"].items():
            rows.append({
                "state_code": code,
                "field_name": field_name,
                "value": field.get("value"),
                "section": field.get("section"),
                "quote": field.get("quote"),
                "note": field.get("note"),
            })

        # Insert new requirements without updating existing ones.
        client.table("state_requirements").upsert(
            rows,
            on_conflict="state_code,field_name",
            ignore_duplicates=True,
        ).execute()

        total += len(rows)
        print(f"{code}: {len(rows)} requirements")

    print(f"Finished: {total} requirements")


if __name__ == "__main__":
    seed_states()