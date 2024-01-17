from os import environ as envvars
from pathlib import Path
from setuptools import find_packages, setup


setup(
    name='ucon',
    description='a tool for dimensional analysis: a "Unit CONverter"',
    long_description=Path(__file__).absolute().parent.joinpath('README.md').read_text(),
    long_description_content_type='text/markdown',
    use_scm_version={'local_scheme': 'no-local-version'} if envvars.get('LOCAL_VERSION_SCHEME') else True,
    license='MIT',
    setup_requires=[
        'setuptools_scm==6.3.2'
    ],
    packages=find_packages(exclude=['tests']),
    author='Emmanuel I. Obi',
    maintainer='Emmanuel I. Obi',
    maintainer_email='withtwoemms@gmail.com',
    url='https://github.com/withtwoemms/ucon',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ]
)
