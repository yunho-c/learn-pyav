from pyav_hwaccel_autoresearch.fixtures import (
    fixture_local_path,
    get_fixture_asset,
    list_fixture_assets,
)


def test_fixture_catalog_contains_expected_keys() -> None:
    fixture_keys = {fixture.key for fixture in list_fixture_assets()}

    assert "pexels-night-sky" in fixture_keys
    assert "pexels-sunset-sea" in fixture_keys
    assert "filesamples-4k-h264" in fixture_keys
    assert "gpac-uhd-hevc-4k" in fixture_keys


def test_h264_4k_fixture_metadata_hints_are_present() -> None:
    asset = get_fixture_asset("filesamples-4k-h264")

    assert asset.width_hint == 3840
    assert asset.height_hint == 2160
    assert asset.codec_hint == "h264"
    assert asset.size_mb_hint == 126


def test_fixture_local_path_stays_under_fixture_cache() -> None:
    asset = get_fixture_asset("pexels-night-sky")

    assert "fixtures" in fixture_local_path(asset).parts
    assert fixture_local_path(asset).name.endswith(".mp4")
