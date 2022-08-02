import shutil

import tomli
import tomli_w
from duty import duty
from duty.context import Context

__all__ = ()


@duty
def docs(ctx: Context, host="127.0.0.1", port=8000, *, serve=False, clean=False) -> None:
    """
    Generate documentation for the project.

    Args:
        ctx: The context of this duty
        host: the host to use for serving
        port: the port to use for serving
        serve: whether to serve the documentation
        clean: whether to clean temporary files before building
    """
    if clean:

        def clean() -> None:
            shutil.rmtree("site")
            shutil.rmtree(".cache")

        ctx.run(clean, title="Cleaning temporary files")

    if serve:
        ctx.run(
            "mkdocs serve",
            args=["-a", f"{host}:{port}"],
            title="Serving docs...",
            capture=False,
        )

    else:
        ctx.run("mkdocs build", title="Building docs...", capture=False)


@duty
def bump(ctx: Context, bump_type: str, *labels) -> None:
    """
    Bump the version of the project.

    Args:
        ctx: The context of this duty
        bump_type: The type of bump, can be an explicit value, or "major", "minor", "patch", "label" or "strip"
    """
    old_labels: list[str] = []
    with open("pyproject.toml", "rb") as f:
        pyproject = tomli.load(f)
    version = pyproject["tool"]["poetry"]["version"]
    if not version:
        version = "0.0.0"

    if "-" in version:
        version, *old_labels = version.split("-")

    major, minor, patch = map(int, version.split("."))

    match bump_type.lower():
        case "major":
            # Bump the major version
            major += 1
        case "minor":
            # Bump the minor version
            minor += 1
        case "patch":
            # Bump the patch version
            patch += 1
        case "strip":
            # Strip the labels
            old_labels = []
        case "label":
            # Add a label
            pass
        case _:
            # Explicit version
            try:
                bump_type = list(map(int, bump_type.split(".")))
                major, minor, patch = bump_type + [0] * (3 - len(bump_type))
            except ValueError:
                raise ValueError("Invalid bump type. Expected values are 'major', 'minor' or 'patch'.") from None

    labels = [*old_labels, *labels]
    formatted_labels = "-".join(labels)
    new_version = f"{major}.{minor}.{patch}" + (f"-{formatted_labels}" if labels else "")

    def version_bump(_bump_type: str) -> None:
        # this didnt need to be a function, but i wanted the ctx output
        pyproject["tool"]["poetry"]["version"] = new_version
        with open("pyproject.toml", "wb") as f:
            tomli_w.dump(pyproject, f)

    ctx.run(
        version_bump,
        args=[bump_type],
        title=f"Bumping version {pyproject['tool']['poetry']['version']} -> {new_version}",
    )


@duty
def build(ctx: Context) -> None:
    ctx.run(shutil.rmtree, args=["dist", "ignore_errors=True"], title="Clearing dist directory...")
    ctx.run(shutil.rmtree, args=["build", "ignore_errors=True"], title="Clearing build directory...")

    ctx.run("python -m pip install --upgrade pip", title="Updating pip...")
    ctx.run("python -m pip install setuptools wheel twine tomli -U", title="Installing build tools...")
    ctx.run("python -m pip install -e .[all] -U", title="Updating dependencies...")

    ctx.run("python setup.py sdist bdist_wheel", title="Building distribution...")


@duty(pre=["build"])
def release(ctx: Context) -> None:
    with open("pyproject.toml", "rb") as f:
        pyproject = tomli.load(f)
    version = pyproject["tool"]["poetry"]["version"]
    ctx.run("python -m twine upload dist/*", title=f"Uploading {version} to PyPI...")
