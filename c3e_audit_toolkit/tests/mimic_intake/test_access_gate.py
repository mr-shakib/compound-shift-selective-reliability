from c3e.mimic_intake.contracts import GateStatus
from c3e.mimic_intake.inventory import InventoryRecord, InventoryResult
from c3e.mimic_intake.runner import determine_status


def _record(category: str) -> InventoryRecord:
    return InventoryRecord(
        resource_key=f"resource_{category}",
        relative_path=f"downloads/{category}.safe",
        category=category,
        file_type=".safe",
        byte_size=1,
        modification_time_utc="2026-07-22T00:00:00Z",
        sha256="0" * 64,
        availability="available_readable",
        content_access="checksum_only",
        observed_count=1,
        truncated=False,
    )


def test_required_resources_produce_pass(intake_config):
    records = tuple(_record(category) for category in intake_config.required_categories)
    inventory = InventoryResult(records, {}, False, len(records), ())
    status, missing, failures = determine_status(
        inventory, intake_config, git_ignored=True, protocol_valid=True
    )
    assert status is GateStatus.PASS
    assert missing == []
    assert failures == []


def test_missing_resources_produce_blocked_not_fabricated_pass(intake_config):
    inventory = InventoryResult((), {}, False, 0, ())
    status, missing, failures = determine_status(
        inventory, intake_config, git_ignored=True, protocol_valid=True
    )
    assert status is GateStatus.BLOCKED
    assert missing == sorted(intake_config.required_categories)
    assert failures == []
