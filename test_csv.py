from pathlib import Path

import pandas as pd


def validate_contacts(contact_file="contacts.csv"):
    path = Path(contact_file)
    if not path.exists():
        raise FileNotFoundError(f"Contacts file not found: {path}")

    df = pd.read_csv(path, dtype=str).fillna("")
    required = {"name", "email"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Columns missing: {sorted(missing)}")

    print(f"Loaded {len(df)} contacts from {path}")
    print(df.head())
    return df


if __name__ == "__main__":
    validate_contacts()
