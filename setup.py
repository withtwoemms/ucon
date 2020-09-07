from os import environ as envvars
from pathlib import Path
from setuptools import setup, find_packages


setup(
    name='ucon',
    description='a tool for dimensional analysis: a "Unit CONverter"',
    version_format=envvars.get('VERSION', '{tag}.dev{commitcount}+{gitsha}'),
    license='MIT',
    setup_requires=[
        'setuptools-git-version==1.0.3'
    ],
    packages=find_packages(exclude=['tests']),
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
    ]
)
