"""Manual roundtrip check for Drive appDataFolder JSON CRUD."""
from __future__ import annotations

from subject_teacher.auth.google_oauth import get_credentials
from subject_teacher.drive.client import DriveAppDataClient


def main() -> None:
    credentials = get_credentials()
    client = DriveAppDataClient(credentials=credentials)

    sample = {"schemaVersion": 1, "hello": "world"}
    file_id = client.upsert_json("_roundtrip.json", sample)
    print(f"upserted: {file_id}")

    loaded = client.read_json("_roundtrip.json")
    assert loaded == sample, f"roundtrip mismatch: {loaded!r}"
    print("roundtrip OK")

    print(f"files in appDataFolder: {client.list_files()}")
    print(f"deleted: {client.delete('_roundtrip.json')}")


if __name__ == "__main__":
    main()
