from pyav_hwaccel_autoresearch.fixtures import (
    fixture_local_path,
    get_fixture_asset,
    list_fixture_assets,
    prepared_fixture_path,
    variant_key_for,
)


def test_fixture_catalog_contains_expected_keys() -> None:
    fixture_keys = {fixture.key for fixture in list_fixture_assets()}

    assert "pexels-night-sky" in fixture_keys
    assert "filesamples-1080p-h264" in fixture_keys
    assert "samplecat-1440p-h264" in fixture_keys
    assert "filesamples-4k-h264" in fixture_keys
    assert "gpac-uhd-hevc-4k" in fixture_keys
    assert "pexels-sunset-sea" not in fixture_keys


def test_h264_4k_fixture_metadata_hints_are_present() -> None:
    asset = get_fixture_asset("filesamples-4k-h264")

    assert asset.width_hint == 3840
    assert asset.height_hint == 2160
    assert asset.codec_hint == "h264"
    assert asset.size_mb_hint == 126


def test_native_1080p_fixture_metadata_hints_are_present() -> None:
    asset = get_fixture_asset("filesamples-1080p-h264")

    assert asset.width_hint == 1920
    assert asset.height_hint == 1080
    assert asset.codec_hint == "h264"
    assert asset.size_mb_hint == 36


def test_native_1440p_fixture_metadata_hints_are_present() -> None:
    asset = get_fixture_asset("samplecat-1440p-h264")

    assert asset.width_hint == 2560
    assert asset.height_hint == 1440
    assert asset.codec_hint == "h264"
    assert asset.size_mb_hint == 18


def test_fixture_local_path_stays_under_fixture_cache() -> None:
    asset = get_fixture_asset("pexels-night-sky")

    assert "fixtures" in fixture_local_path(asset).parts
    assert fixture_local_path(asset).name.endswith(".mp4")


def test_variant_key_for_includes_min_duration_suffix() -> None:
    assert variant_key_for("source") == "source"
    assert variant_key_for("720p", 30) == "720p-30s"


def test_prepared_fixture_path_uses_variant_key_directory() -> None:
    asset = get_fixture_asset("pexels-night-sky")
    path = prepared_fixture_path(asset, "720p-30s")

    assert "prepared" in path.parts
    assert "720p-30s" in path.parts
