from setuptools import setup, find_packages

setup(
    name="qse",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "networkx>=3.0",
        "scipy>=1.10",
        "numpy>=1.24",
        "tabulate>=0.9",
        'tomli>=2.0; python_version<"3.11"',
    ],
    entry_points={
        "console_scripts": [
            "qse=qse.cli:main",
            "qse-archtest=qse.archtest:main",
            "qse-gate=qse.gate.runner:main",
        ],
    },
    python_requires=">=3.10",
)
