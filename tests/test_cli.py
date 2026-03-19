import json

from typer.testing import CliRunner

from pyav_hwaccel_autoresearch.cli import app

runner = CliRunner()


def test_layout_command_outputs_repo_paths() -> None:
    result = runner.invoke(app, ["layout"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["project_root"].endswith("pyav-hwaccel-autoresearch")
    assert payload["pyav_checkout"].endswith("external/pyav")


def test_fixtures_list_command_outputs_catalog() -> None:
    result = runner.invoke(app, ["fixtures", "list"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    fixture_keys = {fixture["key"] for fixture in payload["fixtures"]}
    assert "pexels-night-sky" in fixture_keys


def test_fixtures_resolutions_command_outputs_presets() -> None:
    result = runner.invoke(app, ["fixtures", "resolutions"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    resolution_keys = {resolution["key"] for resolution in payload["resolutions"]}
    assert "source" in resolution_keys
    assert "720p" in resolution_keys
