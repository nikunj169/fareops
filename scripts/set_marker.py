#!/usr/bin/env python3
"""Usage: set_marker.py FILE KEY VALUE [--quote]. Exit 1 if KEY not found."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "services" / "common"))
from fareops_common.markers import set_marker  # noqa: E402

if len(sys.argv) < 4:
    sys.exit(__doc__)
path, key, value = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
new, n = set_marker(path.read_text(), key, value, quote="--quote" in sys.argv)
if n == 0:
    sys.exit(f"marker fareops:{key} not found in {path}")
path.write_text(new)
print(f"updated {n} line(s) for {key} in {path}")
