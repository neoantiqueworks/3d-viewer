"""Fails if any tracked file contains a Google API key.

The repository is public and a committed key was suspended by Google, so no
key may exist in any tracked file, ever. Run from anywhere inside the repo:

    python tests/check-no-keys.py

Exit status 0 means clean, 1 means a key-shaped string was found. Matches are
printed masked, so running the check never displays a key in full.
"""
import re
import subprocess
import sys

# AIza followed by 35 key characters: the shape of every Google API key.
KEY_PATTERN = re.compile(rb"AIza[0-9A-Za-z_\-]{35}")


def mask(key: bytes) -> str:
    text = key.decode("ascii", "replace")
    return text[:4] + "..." + text[-4:]


def main() -> int:
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          capture_output=True, check=True).stdout.decode().strip()
    files = subprocess.run(["git", "ls-files", "-z"], cwd=root,
                           capture_output=True, check=True).stdout.split(b"\0")
    found = 0
    scanned = 0
    for name in filter(None, files):
        path = root + "/" + name.decode()
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except OSError:
            continue  # deleted in the working tree but still in the index
        scanned += 1
        for match in KEY_PATTERN.finditer(data):
            line = data.count(b"\n", 0, match.start()) + 1
            print(f"FAIL {name.decode()}:{line}: API key {mask(match.group())}")
            found += 1
    if found:
        print(f"FAIL {found} API key(s) in tracked files")
        return 1
    print(f"PASS no API key in {scanned} tracked files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
