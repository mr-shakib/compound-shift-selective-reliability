from pathlib import Path

from c3e.mimic_intake.inventory import build_inventory, classify_file


def test_expected_and_unknown_resources_are_classified(intake_config):
    expected = {
        "downloads/release-report.zip": "report_resource",
        "downloads/release-metadata.csv.gz": "image_metadata",
        "downloads/release-split.csv.gz": "official_split_definition",
        "downloads/release-chexpert.csv.gz": "official_auxiliary_labels",
        "checksums/release-manifest.sha256": "checksum_or_manifest",
        "downloads/unmapped.bin": "unknown",
        "downloads/unmapped.tar": "archive",
    }
    assert {name: classify_file(name, intake_config) for name in expected} == expected


def test_inventory_is_deterministic_and_reports_unknown(
    empty_data_root: Path, intake_config
):
    downloads = empty_data_root / "downloads"
    downloads.mkdir()
    (downloads / "z-unknown.bin").write_bytes(b"synthetic unknown")
    (downloads / "release-metadata.csv.gz").write_bytes(b"synthetic metadata")
    (downloads / "release-split.csv.gz").write_bytes(b"synthetic split")
    first = build_inventory(empty_data_root, intake_config)
    second = build_inventory(empty_data_root, intake_config)
    assert first == second
    assert first.category_counts["unknown"] == 1
    assert [record.relative_path for record in first.records] == [
        record.relative_path for record in sorted(
            first.records,
            key=lambda item: (item.category, item.relative_path or "", item.resource_key),
        )
    ]
