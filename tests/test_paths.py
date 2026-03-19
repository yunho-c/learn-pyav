from pyav_hwaccel_autoresearch.paths import project_root, pyav_checkout_dir


def test_project_root_has_manifest() -> None:
    assert (project_root() / "pyproject.toml").is_file()


def test_pyav_checkout_path_points_to_external_submodule() -> None:
    assert pyav_checkout_dir().name == "pyav"
