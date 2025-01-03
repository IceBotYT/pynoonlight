# pynoonlight

[![Test](https://github.com/IceBotYT/pynoonlight/actions/workflows/test.yml/badge.svg)](https://github.com/IceBotYT/pynoonlight/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/pynoonlight?style=flat-square)](https://pypi.python.org/pypi/pynoonlight/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pynoonlight?style=flat-square)](https://pypi.python.org/pypi/pynoonlight/)
[![PyPI - License](https://img.shields.io/pypi/l/pynoonlight?style=flat-square)](https://pypi.python.org/pypi/pynoonlight/)
[![codecov](https://codecov.io/gh/IceBotYT/pynoonlight/branch/main/graph/badge.svg?token=C235MUQANU)](https://codecov.io/gh/IceBotYT/pynoonlight)
[![Coookiecutter - Wolt](https://img.shields.io/badge/cookiecutter-Wolt-00c2e8?style=flat-square&logo=cookiecutter&logoColor=D4AA00&link=https://github.com/woltapp/wolt-python-package-cookiecutter)](https://github.com/woltapp/wolt-python-package-cookiecutter)


---

**Documentation**: [https://IceBotYT.github.io/pynoonlight](https://IceBotYT.github.io/pynoonlight)

**Source Code**: [https://github.com/IceBotYT/pynoonlight](https://github.com/IceBotYT/pynoonlight)

**PyPI**: [https://pypi.org/project/pynoonlight/](https://pypi.org/project/pynoonlight/)

---

Create and update alarms for Noonlight

## Installation

```sh
pip install pynoonlight
```

## Development

* Clone this repository
* Requirements:
  * [Poetry](https://python-poetry.org/)
  * Python 3.10

* Setup virtual environments

> This will modify your `.bashrc` file to create two new aliases to point to the virtual environments.
> The two new aliases are:
> - noonlight_python3.10

```sh
cd pynoonlight
chmod +x setup_virtual_environments.sh
./setup_virtual_environments.sh
```

* Activate the virtual environment (Python 3.10)

```sh
noonlight_python3.10
```

### Testing

```sh
pytest
```

### Documentation

The documentation is automatically generated from the content of the [docs directory](./docs) and from the docstrings
 of the public signatures of the source code. The documentation is updated and published as a [Github project page
 ](https://pages.github.com/) automatically as part each release.

### Releasing

Trigger the [Draft release workflow](https://github.com/IceBotYT/pynoonlight/actions/workflows/draft_release.yml)
(press _Run workflow_). This will update the changelog & version and create a GitHub release which is in _Draft_ state.

Find the draft release from the
[GitHub releases](https://github.com/IceBotYT/pynoonlight/releases) and publish it. When
 a release is published, it'll trigger [release](https://github.com/IceBotYT/pynoonlight/blob/master/.github/workflows/release.yml) workflow which creates PyPI
 release and deploys updated documentation.

### Pre-commit

Pre-commit hooks run all the auto-formatters (e.g. `black`, `isort`), linters (e.g. `mypy`, `flake8`), and other quality
 checks to make sure the changeset is in good shape before a commit/push happens.

You can install the hooks with (runs for each commit):

```sh
pre-commit install
```

Or if you want them to run only for each push:

```sh
pre-commit install -t pre-push
```

Or if you want e.g. want to run all checks manually for all files:

```sh
pre-commit run --all-files
```

---

This project was generated using the [wolt-python-package-cookiecutter](https://github.com/woltapp/wolt-python-package-cookiecutter) template.
