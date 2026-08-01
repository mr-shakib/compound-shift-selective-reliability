from pathlib import Path
import subprocess

from c3e.mimic_intake.contracts import GateStatus
from c3e.mimic_intake.inventory import InventoryResult
from c3e.mimic_intake.runner import check_gitignore, determine_status


def _init_repo(root: Path, ignore: str) -> None:
    subprocess.run(["git", "init", "--quiet"], cwd=root, check=True)
    (root / ".gitignore").write_text(ignore, encoding="utf-8")


def test_gitignored_data_directory_passes_ignore_check(tmp_path: Path):
    _init_repo(tmp_path, "/data/\n")
    assert check_gitignore(tmp_path)


def test_unignored_data_directory_produces_fail(tmp_path: Path, intake_config):
    _init_repo(tmp_path, "")
    assert not check_gitignore(tmp_path)
    inventory = InventoryResult((), {}, False, 0, ())
    status, missing, failures = determine_status(
        inventory, intake_config, git_ignored=False, protocol_valid=True
    )
    assert status is GateStatus.FAIL
    assert missing == []
    assert "not fully ignored" in failures[0]
