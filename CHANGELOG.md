# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.4] - 2024-12-24
### Security
- Resolve Dependabot alert #5
- Resolve Depandabot alert #6

## [0.4.3] - 2023-02-18
### Fixed
- Fixed services typing
- Fixed create_events time parsing

### Changed
- Updated copyright year

## [0.4.2] - 2023-01-22
### Changed
- Updating dependencies, updating structure, etc.

## [0.4.1] - 2022-11-12
### Changed
- Chores: update dependencies and pin actionlint

## [0.4.0] - 2022-10-08
### Changed
- Use of `Location` object

## [0.3.2] - 2022-10-08
### Fixed
- Remove `None` values before creating alarm

## [0.3.1] - 2022-10-08
### Fixed
- Fixed JSON option in `_send_request`

## [0.3.0] - 2022-10-05
### Changed
- Removed the need to pass a production URL to create alarms/task

## [0.2.0] - 2022-10-05
### Fixed
- Improve readability of README

### Changed
- Migrate to `aiohttp` with the support of passing a session
- Disable socket use in tests

## [0.1.0] - 2022-08-22
### Added
- Setup initial project structure (thanks Wolt!)
- Implement dispatch API
- Add `codecov` to the test workflow
- Tweak workflow token names
- Add docstrings to `dispatch.py`
- Add the test badge to `README`
- Fix `mkdocs` by adding `show_submodules: true`
- Convert to Google docstrings
- Add `dependabot` version updates
- Optimize `test` workflow
- Move prod URL validation and request sending to `__init__.py`
- Implement tasks API
- Add tests for tasks API
- Make setting up virtual environments easier

[Unreleased]: https://github.com/IceBotYT/pynoonlight/compare/0.4.4...master
[0.4.4]: https://github.com/IceBotYT/pynoonlight/compare/0.4.3...0.4.4
[0.4.3]: https://github.com/IceBotYT/pynoonlight/compare/0.4.2...0.4.3
[0.4.2]: https://github.com/IceBotYT/pynoonlight/compare/0.4.1...0.4.2
[0.4.1]: https://github.com/IceBotYT/pynoonlight/compare/0.4.0...0.4.1
[0.4.0]: https://github.com/IceBotYT/pynoonlight/compare/0.3.2...0.4.0
[0.3.2]: https://github.com/IceBotYT/pynoonlight/compare/0.3.1...0.3.2
[0.3.1]: https://github.com/IceBotYT/pynoonlight/compare/0.3.0...0.3.1
[0.3.0]: https://github.com/IceBotYT/pynoonlight/compare/0.2.0...0.3.0
[0.2.0]: https://github.com/IceBotYT/pynoonlight/compare/0.1.0...0.2.0
[0.1.0]: https://github.com/IceBotYT/pynoonlight/tree/0.1.0

