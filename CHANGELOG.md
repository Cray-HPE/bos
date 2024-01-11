# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.14.0] 2024-01-10
### Added
- Scalable Boot Provisioning Service (SBPS) support

## [2.13.0] 2024-01-10
### Fixed
- Fix a broken build caused by PEP-668. Pin Alpine version to 3. This is less restrictive.

## [2.12.0] - 2024-01-02
### Changed
- Specify `~1.1.0` for the version of `cray-etcd-base` chart.
- Pin Alpine version to `3.18` (to avoid build failures with `3.19`)

## [2.11.0] - 2023-12-04
### Changed
- Sessions that specify nodes that aren't in the current tenant will fail

## [2.10.1] - 2023-10-31
### Fixed
- Update delete_v2_sessions function to use tenant-aware database keys (so that it actually
  deletes sessions)

## [2.10.0] - 2023-10-18
### Fixed
- Make the include_disabled option work as intended.
- Return the correct object from hsm's get_components call when there are no nodes in the session.
- Fixed session setup errors when there are no valid nodes before filtering for architecture.

## [2.9.0] - 2023-09-29
### Changed
- Update the spire-agent path

## [2.8.0] - 2023-09-18
### Changed
- Update the changes made for `2.7.0` below to include the deprecated sub-fields of the `cfs`
  field in v1 session templates.
- Update the API spec to explicitly state which fields are automatically removed from v1 session
  templates in this version of BOS.
- Remove the now-superfluous read-only `links` field from V1 session templates, since BOS no longer
  ever returns session templates using that schema; the schema is now only used to validate session
  templates being created by the user, and thus there is no purpose for read-only fields in it.
- Update the API spec to mark some v1-specific fields as deprecated that were not previously marked as
  such (`partition`, `boot_ordinal`, `network`, and `shutdown_ordinal`). These fields already had no
  effect and thus were effectively deprecated anyway.

## [2.7.0] - 2023-09-12
### Changed
- Removed non-v2 fields from v1 session template template
- Provide more useful example values in v1 and v2 session template templates
- Modify v1 session template create function to strip away v1-specific fields and create a v2-compatible
  session template.
- Update API spec to reflect that no v1-format session template will exist inside BOS, because the
  v1 session template creation endpoint will strip v1-specific fields and create a v2-format session template,
  and even the v1 session template template endpoint will return a v2-compatible example template.
- Update BOS migration code to properly convert v1 session templates to v2, both from old Etcd database and within
  current redis DB.

## [2.6.3] - 2023-08-22
### Changed
Updated `bos-reporter` spec file to reflect the fact that it should not be installed without `spire-agent` being present.

## [2.6.2] - 2023-08-14
### Fixed
Fixed HSM query handling to prevent errors from querying with an empty list nodes.

## [2.6.1] - 2023-08-10
### Fixed
Fixed database key migration when upgrading from newer versions of BOS.

## [2.6.0] - 2023-08-09
### Changed
- Build `bos-reporter` RPM as `noos`

## [2.5.6] - 2023-08-08
### Changed
- IsAlive attribute look-up.
### Added
- Global read timeout values for all objects and operations which leverage requests_retry handler.
- Heartbeat threads now exit when main thread is no longer alive.
### Dependencies
- Use `update_external_versions` to get latest patch version of `liveness` Python module.
- Bumped depndency patch versions
| Package                  | From    | To       |
|--------------------------|---------|----------|
| `boto3`                  | 1.26.92 | 1.26.165 |
| `cachetools`             | 5.3.0   | 5.3.1    |
| `click`                  | 8.1.3   | 8.1.6    |
| `google-auth`            | 2.16.2  | 2.16.3   |
| `MarkupSafe`             | 2.1.2   | 2.1.3    |
| `protobuf`               | 4.22.1  | 4.22.5   |
| `redis`                  | 4.5.1   | 4.5.5    |
| `retrying`               | 1.3.3   | 1.3.4    |
| `s3transfer`             | 0.6.0   | 0.6.1    |
| `urllib3`                | 1.26.15 | 1.26.16  |
| `websocket-client`       | 1.5.1   | 1.5.3    |

## [2.5.5] - 2023-08-07
### Fixed
- Updated API spec to reflect the fact that BOS sometimes populates the `tenant` field with a null value.
- Updated API spec to allow BOS session names to be empty strings in appropriate contexts (to indicate no
  session, or to clear a populated session field).

## [2.5.4] - 2023-07-18
### Dependencies
- Bump `PyYAML` from 6.0 to 6.0.1 to avoid build issue caused by https://github.com/yaml/pyyaml/issues/601

## [2.5.3] - 2023-06-29
### Added
- Marked BOS v2 session status `error` and `end_time` fields as `nullable` in API spec, because they begin
  populated with null values (rather than empty string values). Added comment to description text for these
  fields to explain this.

## [2.5.2] - 2023-6-26
### Changed
- Added etcd_disable_prestop value for the etcd chart

## [2.5.1] - 2023-06-23
### Fixed
- Update the API spec to reflect that node lists are permitted to be empty in some circumstances.

## [2.5.0] - 2023-06-22
### Added
- Support for SLES SP5 for bos-reporter RPM.
- Added arch support for boot set operations. Boot sets now filter effective nodes within their boot set to match HSM arch information.
- Updated the API spec to:
 - Document the header option required for tenant-specific operations.
 - Document which v1 endpoint operations reject tenanted requests, and how they reject them.
 - Make use of the OpenAPI `deprecated` tag in places where it previously was only indicated in the text description.
 - Add example values for some fields
 - Add recommendations for limits on user-submitted string fields (noting that they are not currently
   enforced, but will be enforced in a future BOS version).
### Changed
- Recfactored duplicated areas of API spec using references.
### Fixed
- Corrected many small errors and inconsistencies in the API spec description text fields.
- Updated API spec so that it accurately describes the actual implementation:
  - Successfully creating a V1 session template returns the name of that template.
### Removed
- `templateUrl` option when creating BOS v1 templates.

## [2.4.3] - 2023-06-20
### Fixed
- Fixed actual state clearup operation

## [2.4.2] - 2023-06-14
### Fixed
- Fixed python decorators to preserve function signatures

## [2.4.1] - 2023-06-06
### Fixed
- Fix bug that accidentally started enforcing restrictions on session template names.
  This fix updated the API spec in two ways:
  - Relaxed the stated restrictions on session template names.
  - Changed the restrictions to recommendations (noting that they are not currently
    enforced, but will be enforced in a future BOS version).

## [2.4.0] - 2023-05-24
### Changed
- Updated BOS server setup file from Python 3.6 to Python 3.11
- Updated from BOA 1.3 to 1.4
- For POST requests to `/v1/session` that include a `templateUuid` field, convert that field to a `templateName` field (if
  that field is not also specified) and delete the `templateUuid` field, before creating  a `V1Session` object.
- Updated to using v6.6.0 of `openapi-generator` (up from v6.4.0)
### Fixed
- Fixed a window during power-on operations which could lead to an incorrect status in larger systems
- Updated API spec so that it accurately describes the actual implementation:
  - Updated `Version` definition to reflect actual type of `major`, `minor`, and `patch` fields.
  - Created `V1SessionLink` definition to reflect that the `links` field for BOS v1 sessions can have
    two additional fields that don't show up in any other BOS link objects.
  - Specify that the BOS v1 session ID is in UUID format.
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
- Fixed minor errors and did minor linting of repository [`README.md`](README.md).
- Failed components are no longer reported in the session status phase percentages.
- Components requiring phase updates are no longer reported in the session status phase percentages.
- Fixed the "tenant" field so that all of the values for no tenant are represented by an empty string.
- Fixed the database key generation so that collisions between tenants can't occur
- Fixed component patching issues when patching actual_state during on-going changes to component state.

## [2.3.0] - 2023-05-10
### Changed
- v1 endpoints now thrown an error when a tenant is specified
- v2 calls to create resources now throw an error when the tenant is invalid
- Updated database keys to prevent collisions and added migration to the new database key format
- 'include_disabled' option to decide whether disabled nodes should be part of a BOS session
- Updating `x86_64` RPM builds to type `noarch` for ARM required work CASMCMS-8517

## [2.2.0] - 2023-05-10
### Added
- Multi-tenancy support for sessions, templates and components
- DisasterRecovery values for the etcd chart
### Fixed
- Fixed inconsistent indentation in Jenkinsfile.
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

## [2.1.0] - 2023-03-16
### Added
- Native PCS support
### Changed
- Updated chart to use new bitnami etcd base chart
### Removed
- CAPMC support
### Fixed
- Linting of openapi spec (no content changes)

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
