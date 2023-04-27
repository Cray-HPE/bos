# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased
### Fixed
- Fixed inconsistent indentation in Jenkinsfile.
- Linting of openapi spec (no content changes)
- Updated API spec for POST to `/v1/sessiontemplate` to reflect actual success status code (201)
- Updated API spec for POST to `/v1/session` to include possible 404 status response
- Updated API spec for POST to `/v1/session` to reflect actual success status code (201)
- Updated API spec for POST to `/v1/session/{session_id}/status` to reflect actual success status code (200) and
  possible failure status code (409)
- Updated API spec for DELETE to `/v1/session/{session_id}/status` to include possible 404 status response
- Updated API spec for POST to `/v1/session/{session_id}/status/{boot_set_name}` to include possible 409 status response
- Updated API spec for PATCH to `/v2/sessiontemplates/{session_template_id}` to include possible 404 status response
### Removed
- Remove obsolete non-functional test files and packaging. Remove references to same from Makefile and other build files.
- Remove now-unused remnants of the former dynamic versioning system used in the repository.

## [2.0.10] - 2023-05-08
### Added
- 'include_disabled' option to decide whether disabled nodes should be part of a BOS session 

## [2.0.9] - 2023-1-12
### Fixed
- Fixed the complete and in_progress fields for session status

## [2.0.7] - 2022-12-20
### Added
- Add Artifactory authentication to Jenkinsfile

## [2.0.6] - 2022-11-30
### Added
- Query CFS for all components' status, not select components
- Authenticate to CSM's artifactory
### Changed
- Allow users to omit rootfs=<value> so that they may specify the exact desired value in sessiontemplate parameters.

## [2.0.5] - 2022-10-14
### Fixed
- Fixed staged shutdowns for v2

## [2.0.4] - 2022-10-11
### Fixed
- Increased timeout values for v2

## [2.0.3] - 2022-10-08
### Fixed
- Added a retry when the BOS power-on operator records the BSS tokens

## [2.0.2] - 2022-10-05
### Fixed
- Fixed v2 extended status error reporting

## [2.0.1] - 2022-09-28
### Fixed
- Query CFS for all components' status, not select components

## [2.0.0] - 2022-08-17
### Added
- Support for Alpine3.16/python10
- Updated Build Sources
- Updated upstream build constraints
- Support for SLES SP4
- Build valid unstable charts
- Migration script for migrating V1 session templates to V2's schema
- Abstracting v1 and v2 healthz endpoint to be database agnostic
- Add overrides for pvc storage class
- Adds option for persisting component staged information via a new option 'clear_stage'

### Changed
- Changed to use the internal HPE network.
- Remove length restriction from v1 sessiontemplate names
- Updated v1/v2 migration of sessiontemplates to retain a v1 copy
- Spelling corrections.

## [1.2.6] - 2022-06-23
### Added
- Disable publishing of BOS test RPM (not currently used)
- Zero error state of components during session creation.
- Initial Gitflow/Changelog conversion of BOS repository.
- Fixes for BOS v2 error handling
