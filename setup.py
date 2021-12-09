from pathlib import Path

import tomli
from setuptools import find_packages, setup

with open("pyproject.toml", "rb") as f:
    pyproject = tomli.load(f)

setup(
    name=pyproject["tool"]["poetry"]["name"],
    description=pyproject["tool"]["poetry"]["description"],
    long_description=(Path(__file__).parent / "README.md").read_text(),
    long_description_content_type="text/markdown",
    author="LordOfPolls",
    author_email="snekcord@gmail.com",
    url="https://github.com/Discord-Snake-Pit/Dis-Snek",
    version=pyproject["tool"]["poetry"]["version"],
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=(Path(__file__).parent / "requirements.txt").read_text().splitlines(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    project_urls={
        "Discord": "https://discord.gg/dis-snek",
        "Documentation": "https://dis-snek.readthedocs.io",
        "Trello Board": "https://trello.com/b/LVjnmYKt/dev-board",
    },
)
