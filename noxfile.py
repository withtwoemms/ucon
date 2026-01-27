# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

import nox
import re
from subprocess import check_output
from os import environ as env
from typing import List


@nox.session(name="build")
def build(session):
    """Build a source and wheel distribution."""
    session.install("build")
    session.run("python", "-m", "build")


def strtobool(value: str) -> bool:
    """
    Converts a string representation of truth to bool.
    True values are 'y', 'yes', 't', 'true', 'on', and '1';
    false values are 'n', 'no', 'f', 'false', 'off', and '0'.
    Raises ValueError if val isn't in one of the aforementioned true or false values.
    """
    value = value.lower()
    if value in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif value in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError(f"Invalid truth value: '{value}'")


PROJECT_NAME = "ucon"
TESTDIR = "tests/"
TESTNAME = env.get("TESTNAME", "")
OFFICIAL = bool(strtobool(env.get("OFFICIAL", "False")))
COVERAGE = bool(strtobool(env.get("COVERAGE", "True")))

supported_python_versions = [
    "3.7",
    "3.8",
    "3.9",
    "3.10",
    "3.11",
    "3.12",
    "3.13",
    "3.14",
]

nox.options.sessions = ["test"]
nox.options.reuse_existing_virtualenvs = True
nox.options.stop_on_first_error = False


# ------------------------------
# Helpers
# ------------------------------

def semver(version: str):
    pattern = (
        r"^([0-9]+)\.([0-9]+)\.([0-9]+)"
        r"(?:-([0-9A-Za-z.-]+))?"
        r"(?:\+[0-9A-Za-z.-]+)?$"
    )
    match = re.search(pattern, version)
    return [val for val in match.groups() if val] if match else None


def is_official(parts: List[str]) -> bool:
    return len(parts or []) == 3


def latest_version(official: bool = False) -> str:
    """Get the latest tagged version from git."""
    output = check_output(
        ["git", "for-each-ref", "--sort=creatordate", "--format", "%(refname)", "refs/tags"]
    )
    tags = [
        v.lstrip("refs/tags/")
        for v in reversed(output.decode().strip().splitlines())
        if v.strip()
    ]
    if not official:
        return tags[0] if tags else "0.0.0"
    for v in tags:
        if is_official(semver(v)):
            return v
    return "0.0.0"


# ------------------------------
# Sessions
# ------------------------------

@nox.session(name="version", python=supported_python_versions)
def version(session):
    """Print latest git tag (official or all)."""
    session.log(f"Latest version: {latest_version(official=OFFICIAL)}")


@nox.session(name="install", python=supported_python_versions)
def install(session):
    """Install the current package."""
    session.install(".")
    session.log("Installed project into virtualenv.")


@nox.session(name="test", python=supported_python_versions)
def test(session):
    """Run the test suite (with coverage if enabled)."""
    #session.install(".")
    session.install("coverage")

    args = [
        "-m", "unittest",
        TESTNAME or "discover",
        "--start-directory", TESTDIR,
        "--top-level-directory", ".",
    ]

    if COVERAGE:
        session.run(
            "coverage", "run", "--source=.", "--branch",
            "--omit=**/tests/*,**/site-packages/*.py,noxfile.py,setup.py",
            *args
        )
        session.run("coverage", "report", "-m")
        session.run("coverage", "xml")
    else:
        session.run("python", *args)
