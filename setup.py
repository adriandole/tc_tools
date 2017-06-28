from setuptools import setup, find_packages

setup(
    name='tc_tools',
    version='1.0a',
    packages=find_packages(),
    author='Donald Dole',
    author_email='donald.dole@nist.gov',
    description='Utilities for interfacing with thermometers and thermocouples',
    install_requires=['numpy', 'pyvisa']
)