import itertools
from pathlib import Path

import tomli
from setuptools import find_packages, setup

with open("pyproject.toml", "rb") as f:
    pyproject = tomli.load(f)

extras_require = {"voice": ["PyNaCl>=1.5.0,<1.6"], "speedup": ["cchardet", "aiodns", "orjson", "Brotli"]}
extras_require["all"] = list(itertools.chain.from_iterable(extras_require.values()))
extras_require["docs"] = extras_require["all"] + [
    "pytkdocs @ git+https://github.com/LordOfPolls/pytkdocs.git",
    "mkdocs-autorefs",
    "mkdocs-awesome-pages-plugin",
    "mkdocs-material",
    "mkdocstrings==0.18",
]

setup(
    name="naff",
    description=pyproject["tool"]["poetry"]["description"],
    long_description=(Path(__file__).parent / "README.md").read_text(),
    long_description_content_type="text/markdown",
    author="LordOfPolls",
    author_email="lordofpolls.dev@gmail.com",
    url="https://github.com/Discord-Snake-Pit/NAFF",
    version=pyproject["tool"]["poetry"]["version"],
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=(Path(__file__).parent / "requirements.txt").read_text().splitlines(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: AsyncIO",
        "Framework :: aiohttp",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Documentation",
        "Typing :: Typed",
    ],
    project_urls={
        "Discord": "https://discord.gg/naff",
        "Documentation": "https://naff-docs.readthedocs.io/en/latest/",
    },
    extras_require=extras_require,
)
