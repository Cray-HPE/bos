# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Support for Alpine3.16/python10
- Updated Build Sources
- Updated upstream build constraints
- Support for SLES SP4

### Changed
- Remove length restriction from v1 sessiontemplate names
- Updated v1/v2 migration of sessiontemplates to retain a v1 copy

## [1.2.6] - 2022-06-23
### Added
- Disable publishing of BOS test RPM (not currently used)
- Zero error state of components during session creation.
- Initial Gitflow/Changelog conversion of BOS repository.
- Fixes for BOS v2 error handling
