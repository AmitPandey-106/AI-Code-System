"""Fixed local oracle transport; no model code. Child Python write/network guard."""
import os
from pathlib import Path
import sys
import tempfile

from phase8_2_1_controls import WritePolicy, canonical, file_sha


def main():
    if len(sys.argv) != 3:
        raise ValueError("Fixed fixture and test hash required")
    fixture = canonical(sys.argv[1])
    test = fixture / "tests/test_router.py"
    # Canonical test bytes are pinned in code as well as in the approved plan.
    expected = "1476656eefe48924bbe83ccc07d9d122e906ca7584f2f1aa77c6531fb9804838"
    if sys.argv[2] != expected or file_sha(test) != expected:
        raise ValueError("Oracle test hash mismatch")
    if any(fixture.rglob("conftest.py")):
        raise ValueError("Unexpected pytest hook")
    sys.dont_write_bytecode = True
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    os.environ.pop("PYTEST_ADDOPTS", None)
    # Temp/cache output stays in a dedicated owned workspace. Fixture is read-only
    # through this ordinary Python policy even after an approved repair.
    temp = canonical(fixture.parent / "tmp")
    if not temp.is_dir():
        raise ValueError("Owned temporary directory is missing")
    os.environ.update(TMP=str(temp), TEMP=str(temp))
    tempfile.tempdir = str(temp)
    policy = WritePolicy(temp)
    sys.addaudithook(policy.audit)
    os.chdir(fixture)
    sys.path.insert(0, str(fixture))
    import pytest
    return pytest.main(["tests/test_router.py", "-q", "-p", "no:cacheprovider",
                        "--confcutdir=" + str(fixture), "-c", os.devnull,
                        "--log-file=" + str(temp / "pytest.log")])


if __name__ == "__main__":
    raise SystemExit(main())
