# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.38] - 05-16-2024
### Fixed
- Fix bug where a single CAPMC operation reports multiple failing nodes, but only one of them
  has its status correctly updated in BOS v2.

### Changed
- Added more checks to avoid operating on empty lists
- Compact response bodies to single line before logging them
- Improve BOS logging of unexpected errors
- Improve scalability of how BOS v2 handles vague CAPMC operation failures

## [2.0.37] - 04-19-2024
### Fixed
- Corrected description of `disable_components_on_completion` in API spec.

## [2.0.36] - 04-19-2024
### Changed
- Reduced v2 default polling frequency from 60 seconds to 15 seconds, to improve performance
- Reconciled discrepancies in default v2 option values between `src/bos/operators/utils/clients/bos/options.py`
  and `src/bos/server/controllers/v2/options.py`

## [2.0.35] - 04-01-2024
### Fixed
- Updated API spec to reflect that BOA updates the boot set status by using the phase `boot_set`.

## [2.0.34] - 03-28-2024
### Changed
- Make BOS be more efficient when patching CFS components.

## [2.0.33] - 03-27-2024
### Added
- Add code to the beginning of some CFS functions to check if they have been called without
  necessary arguments, and if so, to log a warning and return immediately.

### Changed
- If the status operator `_run` method finds no enabled components, stop immediately, as there is
  nothing to do.

### Fixed
- If CAPMC `status` function is called with an empty node list, log a warning and return without
  calling CAPMC.

## [2.0.32] - 03-21-2024
### Fixed
- Failed components are no longer reported in the session status phase percentages.
- Components requiring phase updates are no longer reported in the session status phase percentages.
- Return the correct object from HSM's get_components call when there are no nodes in the session.
- Make the include_disabled option work as intended.

### Changed
- Improvements to BOS v2 debug logging.

## [2.0.31] - 03-12-2024
### Fixed
- Update base operator to handle case where all nodes to act on have exceeded their retry limit
- Fix return value of CAPMC client power function when no nodes specified

## [2.0.30] - 03-08-2024
### Changed
- Reduce superfluous S3 calls during BOSv2 session creation.

## [2.0.29] - 03-07-2024
### Fixed
- Break up large CFS component queries to avoid errors

## [2.0.28] - 03-04-2024
### Fixed
- Corrected minor errors in a couple description fields in API spec (no functional impact)

## [2.0.27] - 10-03-2023
### Changed
- Added error checking for errors returned by CAPMC. Where possible, nodes are disabled when they can be
  associated with an error. This error handling prevents the BOS V2 status operator from entering a
  live-lock when it is dealing with nodes that are MISSING ore disabled in the Hardware State Manager.

## [2.0.26] - 09-19-2023
### Fixed
- Fixed HSM query handling to prevent errors from querying with an empty list nodes.

## [2.0.25] - 2023-07-18
### Dependencies
- Bump `PyYAML` from 6.0 to 6.0.1 to avoid build issue caused by https://github.com/yaml/pyyaml/issues/601

## [2.0.24] - 2023-06-29
### Added
- Marked BOS v2 session status `error` and `end_time` fields as `nullable` in API spec, because they begin
  populated with null values (rather than empty string values). Added comment to description text for these
  fields to explain this.

## [2.0.23] - 2023-06-26
### Added
- Updated the API spec to:
  - Make use of the OpenAPI `deprecated` tag in places where it previously was
    only indicated in the text description.
 - Accurately reflect that successfully creating a V1 session template returns the name of that template.
 - Add example values for some fields
 - Add recommendations for limits on user-submitted string fields (noting that they are not currently
   enforced, but will be enforced in a future BOS version).
### Removed
- `templateUrl` option when creating BOS v1 templates.

## [2.0.22] - 2023-06-23
### Reverted
#### Added
- Updated the API spec to:
  - Add example values for some fields
  - Add recommendations for limits on user-submitted string fields (noting that they are not currently
    enforced, but will be enforced in a future BOS version).
- Updated the API spec to make use of the OpenAPI `deprecated` tag in places where it previously was
  only indicated in the text description.
#### Changed
- Recfactored duplicated areas of API spec using references.
#### Fixed
- Corrected many small errors and inconsistencies in the API spec description text fields.
- Updated API spec so that it accurately describes the actual implementation:
  - Successfully creating a V1 session template returns the name of that template.
#### Removed
- `templateUrl` option when creating BOS v1 templates.

## [2.0.21] - 2023-06-22
### Added
- Updated the API spec to:
  - Add example values for some fields
  - Add recommendations for limits on user-submitted string fields (noting that they are not currently
    enforced, but will be enforced in a future BOS version).
### Changed
- Recfactored duplicated areas of API spec using references.

## [2.0.20] - 2023-06-20
### Fixed
- Fixed actual state clearup operation

## [2.0.19] - 2023-06-15
### Added
- Updated the API spec to make use of the OpenAPI `deprecated` tag in places where it previously was
  only indicated in the text description.
### Fixed
- Corrected many small errors and inconsistencies in the API spec description text fields.
- Updated API spec so that it accurately describes the actual implementation:
  - Successfully creating a V1 session template returns the name of that template.
### Removed
- `templateUrl` option when creating BOS v1 templates.

## [2.0.18] - 2023-05-30
### Fixed
- Fix bug that accidentally started enforcing restrictions on session template names.
  This fix updated the API spec in two ways:
  - Relaxed the stated restrictions on session template names.
  - Changed the restrictions to recommendations (noting that they are not currently
    enforced, but will be enforced in a future BOS version).

## [2.0.17] - 2023-05-24
### Fixed
- Fixed minor errors and did minor linting of repository [`README.md`](README.md).
- Fixed component patching issues when patching actual_state during on-going changes to component state.

## [2.0.16] - 2023-05-19
### Fixed
- Merge definitions of `V1Session` and `V1SessionByTemplateName`, to avoid server error
  creating sessions using `templateUuid`.

## [2.0.15] - 2023-05-18
### Changed
- Pin Alpine version to 3.18 in Dockerfile
- Updated BOS server setup file from Python 3.6 to Python 3.11

## [2.0.14] - 2023-05-18
### Fixed
- Updated API spec so that it accurately describes the actual implementation:
  - Specify that a GET to `/v1/session` returns a list of session IDs, not sessions.
  - Specify that creating a BOS v1 session requires `operation` to be specified and one or both of
    `templateName` and `templateUuid` (although if both are specified, the latter is ignored).
  - Make the spec accurately reflect what is returned when creating a BOS v1 session and when doing a GET
    of a BOS v1 session.
  - Indicate that GET of a session template or list of session templates can return v1 or v2 templates,
    regardless of which endpoint is used.
- Return valid BOS v2 session template on GET request to `/v2/sessiontemplatetemplate`.
- Formatting and language linting of API spec to correct minor errors, omissions, and inconsistencies.
- Correct API spec to use valid ECMA 262 regular expression syntax, as dictated by the OpenAPI requirements.

## [2.0.13] - 2023-05-15
### Fixed
- Updated API spec so that it accurately describes the actual implementation:
  - Updated `Version` definition to reflect actual type of `major`, `minor`, and `patch` fields.
  - Created `V1SessionLink` definition to reflect that the `links` field for BOS v1 sessions can have
    two additional fields that don't show up in any other BOS link objects.
  - Specify that the BOS v1 session ID is in UUID format.

## [2.0.12] - 2023-05-12
### Fixed
- Fixed a window during power-on operations which could lead to an incorrect status in larger systems

## [2.0.11] - 2023-05-10
### Fixed
- Fixed inconsistent indentation in Jenkinsfile.
- Linting of openapi spec (no content changes)
- Updated API spec so that it accurately describes the actual implementation:
  - Updated POST to `/v1/sessiontemplate` to reflect actual success status code (201)
  - Updated POST to `/v1/session` to include possible 404 status response
  - Updated POST to `/v1/session` to reflect actual success status code (201)
  - Updated POST to `/v1/session/{session_id}/status` to reflect actual success status code (200) and
    possible failure status code (409)
  - Updated DELETE to `/v1/session/{session_id}/status` to include possible 404 status response
  - Updated POST to `/v1/session/{session_id}/status/{boot_set_name}` to include possible 409 status response
  - Updated PATCH to `/v2/sessiontemplates/{session_template_id}` to include possible 404 status response
  - Updated GET to `/` to reflect that a list of versions is returned
- Ensure that DELETE requests to `/v1/sessiontemplate/{session_template_id}` return a meaningful status code
### Removed
- Remove obsolete non-functional test files and packaging. Remove references to same from Makefile and other build files.
- Remove now-unused remnants of the former dynamic versioning system used in the repository.

## [2.0.10] - 2023-05-08
### Added
- 'include_disabled' option to decide whether disabled nodes should be part of a BOS session

## [2.0.9] - 2023-01-12
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
