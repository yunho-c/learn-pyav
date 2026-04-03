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
    assert "filesamples-1080p-h264" in fixture_keys
    assert "samplecat-1440p-h264" in fixture_keys
    assert "filesamples-4k-h264" in fixture_keys
    assert "pexels-sunset-sea" not in fixture_keys


def test_fixtures_resolutions_command_outputs_presets() -> None:
    result = runner.invoke(app, ["fixtures", "resolutions"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    resolution_keys = {resolution["key"] for resolution in payload["resolutions"]}
    assert "source" in resolution_keys
    assert "720p" in resolution_keys
    assert "2160p" in resolution_keys


def test_compare_decode_help_mentions_hwaccel_option() -> None:
    result = runner.invoke(app, ["benchmark", "compare-decode", "--help"])

    assert result.exit_code == 0
    assert "--hwaccel" in result.stdout
    assert "--min-duration-seconds" in result.stdout


def test_compare_encode_help_mentions_codec_options() -> None:
    result = runner.invoke(app, ["benchmark", "compare-encode", "--help"])

    assert result.exit_code == 0
    assert "--baseline-codec" in result.stdout
    assert "--candidate-codec" in result.stdout
    assert "--min-duration-seconds" in result.stdout


def test_compare_all_help_mentions_fixture_filter() -> None:
    result = runner.invoke(app, ["benchmark", "compare-all", "--help"])

    assert result.exit_code == 0
    assert "--fixture" in result.stdout
    assert "--min-duration-seconds" in result.stdout


def test_report_suite_table_help_mentions_format() -> None:
    result = runner.invoke(app, ["report", "suite-table", "--help"])

    assert result.exit_code == 0
    assert "--format" in result.stdout
