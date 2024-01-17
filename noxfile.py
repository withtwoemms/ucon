import nox
import re

from distutils.util import strtobool
from subprocess import check_output
from typing import List
from os import environ as envvar


PROJECT_NAME = 'ucon'
VENV = f'{PROJECT_NAME}-venv'
USEVENV = envvar.get('USEVENV', False)

if USEVENV:
    assert USEVENV in ('none', 'virtualenv', 'conda', 'mamba', 'venv')

OFFICIAL = bool(strtobool(envvar.get('OFFICIAL', 'False')))
COVERAGE = bool(strtobool(envvar.get('COVERAGE', 'True')))
TESTDIR = f'tests/'
TESTNAME = envvar.get('TESTNAME', '')


external = False if USEVENV else True
supported_python_versions = [
    '3.6',
    '3.7',
    '3.8',
    '3.9',
    '3.10',
]

nox.options.default_venv_backend = 'none' if not USEVENV else USEVENV

def session_name(suffix: str):
    return f'{VENV}-{suffix}' if USEVENV else suffix


def semver(version: str):
    unofficial_semver = r'^([0-9]|[1-9][0-9]*)\.([0-9]|[1-9][0-9]*)\.([0-9]|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+)?(.+)$'
    official_semver = r'^([0-9]|[1-9][0-9]*)\.([0-9]|[1-9][0-9]*)\.([0-9]|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+)?$'
    _semver = re.search(official_semver, version) or re.search(unofficial_semver, version)
    if _semver:
        return [val for val in _semver.groups() if val]


def is_official(semver: List[str]):
    """
    TODO (withtwoemms) -- create SemVer type to replace List[str]
    """
    if len(semver) > 3:
        return False
    else:
        return True


def latest_version(official: bool = False):
    output = check_output('git for-each-ref --sort=creatordate --format %(refname) refs/tags'.split())
    all_versions = (
        version.lstrip('refs/tags/')
        for version in reversed(output.decode().strip('\n').split('\n'))
    )

    if not official:
        return next(all_versions)

    for version in all_versions:
        if official and is_official(semver(version)):
            return version


@nox.session(name=session_name('version'), python=supported_python_versions)
def version(session):
    print(latest_version(official=OFFICIAL))


@nox.session(name=session_name('install'), python=supported_python_versions)
def install(session):
    session.run(
        'python', '-m',
        'pip', '--disable-pip-version-check', 'install', '.',
        external=external
    )


@nox.session(name=session_name('test'), python=supported_python_versions)
def test(session):
    if USEVENV:
        install(session)

    if COVERAGE:
        session.run(
            'python', '-m',
            'coverage', 'run', '--source', '.', '--branch',
            '--omit', '**tests/*,**/site-packages/*.py,noxfile.py,setup.py',
            '-m', 'unittest', TESTNAME if TESTNAME else f'discover',
            '--start-directory', TESTDIR,
            '--top-level-directory', '.',
            external=external
        )
        session.run('coverage', 'report', '-m', external=external)
        session.run('coverage', 'xml', external=external)
    else:
        session.run(
            'python', '-m',
            'unittest', TESTNAME if TESTNAME else f'discover',
            '--start-directory', TESTDIR,
            '--top-level-directory', '.',
            external=external
        )


@nox.session(name=f'build')
def build(session):
    session.run('python', 'setup.py', 'sdist')
