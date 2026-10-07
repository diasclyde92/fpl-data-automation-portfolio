"""Deterministic tests for GitHub Actions workflow configuration and pipeline automation contracts."""

from pathlib import Path
import yaml


def test_workflow_file_exists_and_valid_yaml():
    """Verify .github/workflows/fpl_pipeline.yml exists and parses as valid YAML."""
    workflow_path = Path(".github/workflows/fpl_pipeline.yml")
    assert workflow_path.exists(), f"Workflow file not found at {workflow_path}"

    with open(workflow_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict)
    assert data["name"] == "Scheduled FPL Historical Pipeline"


def test_workflow_triggers_and_concurrency():
    """Verify scheduled cron, workflow_dispatch triggers, and concurrency protection."""
    workflow_path = Path(".github/workflows/fpl_pipeline.yml")
    with open(workflow_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    triggers = data.get("on", {})
    assert "schedule" in triggers, "Missing scheduled cron trigger"
    assert "workflow_dispatch" in triggers, "Missing manual workflow_dispatch trigger"

    cron_entries = triggers["schedule"]
    assert len(cron_entries) >= 1
    assert "cron" in cron_entries[0]
    assert cron_entries[0]["cron"] == "0 6 * * *"

    # Verify concurrency policy
    concurrency = data.get("concurrency", {})
    assert concurrency.get("group") == "fpl-pipeline-state"
    assert concurrency.get("cancel-in-progress") is False


def test_workflow_permissions():
    """Verify minimal permissions: contents: read, actions: read."""
    workflow_path = Path(".github/workflows/fpl_pipeline.yml")
    with open(workflow_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    permissions = data.get("permissions", {})
    assert permissions.get("contents") == "read"
    assert permissions.get("actions") == "read"
    # Ensure write permissions are NOT granted
    assert permissions.get("contents") != "write"


def test_workflow_cross_run_restoration_and_steps():
    """Verify cross-run artifact restoration, pipeline execution, and artifact upload contracts."""
    workflow_path = Path(".github/workflows/fpl_pipeline.yml")
    with open(workflow_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    jobs = data.get("jobs", {})
    assert "run-pipeline" in jobs
    job = jobs["run-pipeline"]
    assert job["runs-on"] == "ubuntu-latest"

    steps = job.get("steps", [])
    step_names = [s.get("name") for s in steps]

    assert "Checkout repository" in step_names
    assert "Set up Python 3.12" in step_names
    assert "Install dependencies" in step_names
    assert "Restore previous FPL database from latest successful workflow run" in step_names
    assert "Run FPL historical pipeline" in step_names
    assert "Upload updated FPL database artifact" in step_names
    assert "Upload raw FPL snapshot artifact" in step_names

    # Verify restore step uses gh CLI to find previous successful run excluding current run
    restore_step = next(s for s in steps if "Restore previous FPL database" in s.get("name"))
    restore_script = restore_step.get("run", "")
    assert "gh run list" in restore_script
    assert "--status success" in restore_script
    assert "fpl-database" in restore_script
    assert "CURRENT_RUN_ID" in restore_step.get("env", {})

    # Verify pipeline execution command
    run_step = next(s for s in steps if s.get("name") == "Run FPL historical pipeline")
    assert "python -m src.pipeline.fpl_pipeline --save-raw --verbose" in run_step.get("run", "")

    # Verify upload step retention and overwrite configuration
    upload_db_step = next(s for s in steps if s.get("name") == "Upload updated FPL database artifact")
    assert upload_db_step.get("with", {}).get("name") == "fpl-database"
    assert upload_db_step.get("with", {}).get("retention-days") == 30
    assert upload_db_step.get("with", {}).get("overwrite") is True

    upload_raw_step = next(s for s in steps if s.get("name") == "Upload raw FPL snapshot artifact")
    assert upload_raw_step.get("with", {}).get("name") == "fpl-raw-snapshot"
    assert upload_raw_step.get("with", {}).get("retention-days") == 30
