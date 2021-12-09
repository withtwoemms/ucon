import nox

from os import environ as envvar


PROJECT_NAME = 'ucon'
VENV = f'{PROJECT_NAME}-venv'
TESTDIR = '.'
USEVENV = envvar.get('USEVENV', False)

external = False if USEVENV else True
supported_python_versions = [
    '3.6',
    '3.7',
    '3.8',
    '3.9',
    '3.10',
]

nox.options.default_venv_backend = 'none' if not USEVENV else USEVENV


@nox.session(name=VENV if USEVENV else PROJECT_NAME, python=supported_python_versions)
def tests(session):
    session.run(
        'python', '-m',
        'pip', '--disable-pip-version-check', 'install', '.',
        external=external
    )
    session.run(
        'python', '-m',
        'pip', '--disable-pip-version-check', 'install', '-r', 'requirements.txt',
        external=external
    )
    session.run(
        'python', '-m',
        'coverage', 'run', '--branch',
        '--omit', '.nox/*,noxfile.py,setup.py,test*',
        '--source', '.',
        '-m', 'unittest', 'discover',
        '-s', TESTDIR,
        external=external
    )
    session.run('coverage', 'report', '-m', external=external)
    session.run('coverage', 'xml', external=external)


@nox.session(name=f'build-{PROJECT_NAME}')
def build(session):
    session.run('python', 'setup.py', 'sdist')


# TODO (withtwoemms) -- leverage gitpython to show version on-demand

