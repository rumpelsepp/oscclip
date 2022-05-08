# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added

- Automatic linter checks via Github Actions
- Automatic deployment to PyPi via Github Actions

### Fixed

- Correctly detect the end of OSC52 response and increase buffersize.

## [0.3.0] - 2022-01-14
#### Added

- support for GNU screen

### Changed

- poetry as a build system

### Fixed

- small bugfixes according to ctrl+c

## [0.2.1] - 2021-10-25
### Fixed

- Remove debugging invocation of the paste entry point
- Print the decoded data instead

## [0.2.0] - 2021-10-25
### Added

- Add --direct flag to bypass tmux

### Fixed

- Implement OSC52 correcly for non tmux scenarios

## [0.1.0] - 2021-10-24

Initial Release
