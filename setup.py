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
    ],
    entry_points={
        "console_scripts": [
            "qse=qse.cli:main",
        ],
    },
    python_requires=">=3.10",
)
