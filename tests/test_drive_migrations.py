import pytest

from subject_teacher.drive.migrations import (
    UnsupportedSchemaVersionError,
    migrate,
    register_upgrader,
)
from subject_teacher.drive.schemas import SCHEMA_VERSION


def test_same_version_is_noop():
    data = {"schemaVersion": SCHEMA_VERSION, "teacherName": "X"}

    assert migrate(data) == data


def test_higher_version_raises():
    data = {"schemaVersion": SCHEMA_VERSION + 1}

    with pytest.raises(UnsupportedSchemaVersionError):
        migrate(data)


def test_missing_version_treated_as_v1():
    data = {"teacherName": "X"}

    migrated = migrate(data)
    assert migrated["schemaVersion"] == SCHEMA_VERSION


def test_register_and_run_upgrader():
    def v0_to_v1(data: dict) -> dict:
        upgraded = dict(data)
        upgraded["_upgraded"] = True
        return upgraded

    register_upgrader(0, v0_to_v1)

    data = {"schemaVersion": 0, "teacherName": "X"}
    migrated = migrate(data)

    assert migrated["_upgraded"] is True
    assert migrated["schemaVersion"] == SCHEMA_VERSION
