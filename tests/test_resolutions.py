from pyav_hwaccel_autoresearch.fixtures import get_resolution_spec, list_resolution_specs


def test_resolution_catalog_contains_expected_presets() -> None:
    resolution_keys = {resolution.key for resolution in list_resolution_specs()}

    assert {"source", "480p", "720p", "1080p", "2160p"} <= resolution_keys


def test_source_resolution_has_no_target_height() -> None:
    assert get_resolution_spec("source").target_height is None
