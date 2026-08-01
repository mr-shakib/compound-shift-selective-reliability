from pathlib import Path

from c3e.mimic_intake.inventory import build_inventory, classify_file


def test_image_extensions_are_classified_and_aggregated(empty_data_root: Path, intake_config):
    images = empty_data_root / "files"
    images.mkdir()
    for name in ("synthetic.dcm", "synthetic.JPG", "synthetic.png"):
        (images / name).write_bytes(b"must never be opened by inventory")
        assert classify_file(f"files/{name}", intake_config) == "image_file"
    result = build_inventory(empty_data_root, intake_config)
    image_record = next(record for record in result.records if record.category == "image_file")
    assert image_record.observed_count == 3
    assert image_record.relative_path is None
    assert image_record.sha256 is None
    assert image_record.content_access == "blocked_medical_image"


def test_image_files_are_never_opened_for_hashing(
    empty_data_root: Path, intake_config, monkeypatch
):
    image = empty_data_root / "forbidden.jpg"
    image.write_bytes(b"synthetic image bytes")

    def forbidden_open(self, *args, **kwargs):
        raise AssertionError(f"medical image was opened: {self}")

    monkeypatch.setattr(Path, "open", forbidden_open)
    result = build_inventory(empty_data_root, intake_config)
    assert result.category_counts == {"image_file": 1}
