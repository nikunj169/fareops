from fareops_common.markers import get_marker, set_marker

EXAMPLE = """            image: ghcr.io/<GH_USER>/fareops-fare-api:abc1234 # fareops:fare-api-image
              - name: MODEL_VERSION
                value: "1" # fareops:model-version
"""


def test_set_marker_changes_only_the_target_line():
    new, n = set_marker(EXAMPLE, "model-version", "7", quote=True)
    assert n == 1
    lines = new.splitlines()
    assert lines[0] == EXAMPLE.splitlines()[0]                      # fare-api-image line untouched
    assert lines[2] == '                value: "7" # fareops:model-version'
    assert get_marker(new, "model-version") == "7"


def test_set_marker_on_image_line_without_quote():
    new, n = set_marker(EXAMPLE, "fare-api-image", "ghcr.io/u/fareops-fare-api:def5678")
    assert n == 1
    assert 'image: ghcr.io/u/fareops-fare-api:def5678 # fareops:fare-api-image' in new
    assert get_marker(new, "fare-api-image") == "ghcr.io/u/fareops-fare-api:def5678"


def test_unknown_key_matches_nothing():
    new, n = set_marker(EXAMPLE, "does-not-exist", "x")
    assert n == 0
    assert new == EXAMPLE
    assert get_marker(EXAMPLE, "does-not-exist") is None
