"""The registry distribution name must not rename the user interface/import."""

from importlib.metadata import distribution

from k_web import __version__


def test_distribution_identity_and_entry_point():
    package = distribution("kpihx-web")
    assert package.metadata["Name"] == "kpihx-web"
    assert package.version == __version__
    assert {entry.name: entry.value for entry in package.entry_points}[
        "web"
    ] == "k_web.cli:main"
