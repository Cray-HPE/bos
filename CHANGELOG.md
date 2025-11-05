# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Include process ID, thread ID, file name, line number, and function name in BOS logging messages.

### Dependencies
- Use `v7.17` of `openapi-generator-cli`
- Bumped versions of several Python dependencies

## [2.48.2] - 2025-07-03

### Changed
- Use `redis` `RESP3` protocol

### Dependencies
- CASMCMS-9479: Update `redis` module

## [2.48.1] - 2025-07-02

### Dependencies

- CASMCMS-9468: Specify different `requests-retry-session` version based on Python version

## [2.48.0] - 2025-06-13

### Removed
- CASMCMS-8131: Removed `disable_components_on_completion` option due to lack of use and lack of testing.

## [2.47.0] - 2025-06-11

### Changed
- CASMCMS-8843: Filter out locked nodes when starting a session; improve logging around node lists in same

## [2.46.1] - 2025-06-06

### Dependencies
- CASMCMS-9453: Pinned Alpine version to 3.22
- CASMCMS-9453: Bumped versions of several Python dependencies

## [2.46.0] - 2025-06-05

### Fixed
- CASMCMS-9452: Cleanup of leftover Cluster/RoleBindings under CMS

## [2.45.0] - 2025-05-19

### Added

- CASMCMS-9421: Add rootfs provider validation to session template validation endpoint

### Changed

- Improve performance of BOS component queries that specify IDs or a tenant
- CASMCMS-9432: Update API spec examples to use SBPS instead of CPS/DVS
- CASMCMS-9433: Update `sessiontemplatetemplate` endpoint to use SBPS instead of CPS/DVS

### Removed

- CASMCMS-9421: Remove CPS/DVS rootfs support

## [2.44.1] - 2025-05-19

### Fixed
- Make operators Timestamp class thread-safe

## [2.44.0] - 2025-05-16

### Changed
= Refactor a couple huge methods in the status operator to make the code more digestible
- Minor refactoring of power on operator to resolve pylint complexity complaints
- CASMCMS-9426: Allow session template patches to omit the `boot_sets` field
- CASMCMS-9428: Change component `phase` and `action` fields to enumerated string types; refactor
  operators to take advantage of the changed `action` field type.
- CASMCMS-9429: Refactor `_get_v2_session_status` logic into its own module
- CASMCMS-9430: Modify select `@property` decorators into `@cached_property`, for improved performance.

## [2.43.0] - 2025-05-07

### Changed
- CASMCMS-9407: Refactored session setup operator to resolve type annotation issues
- CASMCMS-9412:
  - Enable more thorough `mypy` checks at build time
  - CASMCMS-9413: Add explicit annotations for S3 methods
  - CASMCMS-9414: Create helper types for sessions and component type annotation
  - CASMCMS-9415: Refactor `dbwrapper` to resolve type annotation issues
  - CASMCMS-9416: Resolve type annotation issues in `server/options.py`
  - CASMCMS-9417: Resolve type annotation issues in session status operator
  - CASMCMS-9418: Resolve type annotation issues in BOS client, HSM client, and filters
  - Update Jenkinsfile to make failed `mypy` checks fail the build

### Dependencies
- Updated to openapi-generator-cli v7.13.0

## [2.42.0] - 2025-05-01

### Changed
- CASMCMS-9392: Change type annotation of `BootImageMetaDataFactory` to reflect the only actual
  type it can current return, to resolve `mypy` concerns.
- CASMCMS-9391: Clean up type annotations in BOS server migration code (and fix minor bugs identified by mypy).
- CASMCMS-9393: Fix type annotations for sessiontemplatetemplate endpoint controller
- CASMCMS-9395: Fix type annotations for sessions controller
- CASMCMS-9390: Fix type annotations for server options
- CASMCMS-9394: Fix type annotations for operators
- CASMCMS-9402: CFS client: Simplify and add type annotations
- CASMCMS-9403: BSS & PCS clients: Add type annotations
- CASMCMS-9405: Consolidate S3 client and boot_image_metadata into single module
- CASMCMS-9406: Fix type annotations in discovery and status operators

## [2.41.0] - 2025-04-28

### Changed
- CASMCMS-9382: Resolve mypy type complaints
  - CASMCMS-9383: tenant_utils
  - CASMCMS-9385: HSM and IMS clients

## [2.40.0] - 2025-04-23

### Added
- CASMCMS-9381: Add `skip_bad_ids` parameter to bulk components patch endpoint.

### Changed
- CASMCMS-9346: Improved type annotations for BOS components controller
- CASMCMS-9362: Refactor components bulk patch functions
- CASMCMS-9355: Use new `skip_bad_ids` parameter in session setup operator, to gracefully
  handle the case where bad IDs are included in the session.

## [2.39.0] - 2025-04-14

### Changed
- CASMCMS-9357: Made compact_response_text more memory efficient by using iterators. Made
  it more processor efficient by converting it into a class with a __str__ method, so that
  when it is used with logging functions, its code does not get executed unless the associated
  log entry is actually going to be recorded.
- CASMCMS-9353: Improve exception logging

## [2.38.1] - 2025-04-11

### Fixed
- CASMCMS-9356: Fix how OptionsData class handles initialization when the DB is unavailable

## [2.38.0] - 2025-04-10

### Changed
- CASMCMS-8666: Remove `name` field from `/sessiontemplatetemplate` response.
- CASMCMS-7902: Check size before loading image manifest to avoid OOM issues.

### Fixed
- CASMCMS-9351: Fixed two logging bugs:
  - When updating log level, BOS operators were logging the new log level as its
    integer value, rather than its string value.
  - The server was not properly updating its log level when it changed, because it
    runs in separate processes.

## [2.37.2] - 2025-04-09

### Fixed
- Fix bug preventing correct option patching.

## [2.37.1] - 2025-04-09

### Fixed
- Fix bug with type alias definition causing BOS options endpoint to return no values

## [2.37.0] - 2025-04-07

### Added
- CASMCMS-9340: Created Redis DB wrapper methods to allow reading/writing multiple entries in
  a single call; updated components controller to make use of this.

### Changes
- CASMCMS-9331: When a requested item is missing from a BOS DB, signal this by raising an
  exception instead of returning None.
- CASMCMS-9339: Make more precise type annotations for session create and patch requests

### Dependencies
- Bump redis Python client version from 5.0 to 5.2

## [2.36.0] - 2025-03-26

### Changed
- CASMCMS-9294: Improve Python type annotations, focused on DB modules
- CASMCMS-9295: Improve Python type annotations in `boot_image_metadata` modules
- CASMCMS-9296: Improve Python type annotations in `rootfs` modules
- CASMCMS-9297: Improve Python type annotations in `filters` modules
- CASMCMS-9320: Add "app.kubernetes.io/instance: cray-bos" label to cray-bos-db pod

## [2.35.1] - 2025-03-20

### Fixed
- CASMCMS-9330: Print new logging level as string rather than integer

## [2.35.0] - 2025-03-13

### Changed
- CASMCMS-9286: Reworked some of the API client implementation to resolve intractable mypy complaints
- Improve session/sessiontemplate controller error responses by including tenant
- CASMSEC-433: cray-bos-db container now uses the `nobody` user instead of `root`
- CASMCMS-9291
  - Updated API spec to define the format of the `error_summary` field
  - Created additional type-hinting definitions in bos.common.types

## [2.34.2] - 2025-02-19

### Fixed
- CASMCMS-9289: Remove extra `/` from HSM URLs to prevent request failures
- CASMCMS-9290
  - Remove no-longer-necessary call to `raise_for_status` in BOS power on operator
  - Catch all exceptions arising from API call
  - Update power on operator to reflect fact that the BSS API client returns the
    `bss-referral-token` itself, not an API response object.

## [2.34.1] - 2025-02-18

### Fixed
- CASMCMS-9288: Fix session setup operator attempting to use uninitialized API client

## [2.34.0] - 2025-02-18

### Changed
- CASMCMS-9287: Addressed some non-fatal `pylint` code complaints

### Fixed
- CASMCMS-9285: Convert `bos.common.types` into a submodule; begin creating type definitions for BOS structures;
  select minor type annotation improvements
- CASMCMS-9284: Correct some errors identified by `mypy`

## [2.33.0] - 2025-02-12

### Added
- CASMCMS-9277: Added `mypy` into the build pipeline as a non-gating step

### Changed
- CASMCMS-9274: Prevent [`SNYK-PYTHON-WERKZEUG-6808933`](https://security.snyk.io/vuln/SNYK-PYTHON-WERKZEUG-6808933) from causing builds to fail.
- CASMCMS-9265: Improve Python type annotations in sessions controller code
- CASMCMS-9269: Improve Python type annotations in session templates controller code
- CASMCMS-9271: Improve Python type annotations in components controller code
- CASMCMS-9272: Improve Python type annotations in controller code for options, health, versions, and base/utility modules
- CASMCMS-9273: Improve Python type annotations in `boot_set` controller submodule
- CASMCMS-9275: Improve Python type annotations in `bos.common` module
- CASMCMS-9276: Improve Python type annotations in remaining `bos.server` files

### Fixed
- CASMCMS-8965: Update sessions controller to provide error responses consistently and correctly

### Dependencies
- Bumped Python dependency versions.

## [2.32.2] - 2025-02-05
### Fixed
- CASMCMS-9270: Properly handle being asked to validate nonexistent session template; correct
  nonexistent template error message

## [2.32.1] - 2025-01-16
### Fixed
- CASMCMS-9255: Improved parsing of kernel paths to extract IMS IDs
- Correct bug that could result in some BOS components not having their error fields
  updated if the IMS image tag failed.

## [2.32.0] - 2025-01-13
### Added
- Added basic paging ability for `GET` requests for `components`.
- BOS options: bss_read_timeout, hsm_read_timeout, ims_read_timeout, pcs_read_timeout.
  Allow the amount of time BOS waits for a response from these services before
  timing out to be configurable

### Fixed
- Fixed bug causing no components to be listed when no tenant specified.

### Changed
- Have BOS migration job wait for databases to be ready before proceeding
- Modified operators to use paging when requesting BOS components, using a page size equal to the `max_components_batch_size` option.
- Put all requests code into context managers -- this includes the HTTP adapters, the sessions, and the request responses.
- Update autoscaling `apiVersion` to support updated Kubernetes in CSM 1.7

## [2.31.1] - 2024-12-18
### Fixed
- When renaming session templates during migration, use correct database key to store renamed template.

## [2.31.0] - 2024-11-01
### Removed
- Moved BOS reporter to https://github.com/Cray-HPE/bos-reporter

## [2.30.5] - 2024-10-15
### Fixed
- Fix per-bootset CFS setting

## [2.30.4] - 2024-10-15
### Added
#### BOS option
- cfs_read_timeout: Allow the amount of time BOS waits for a response from CFS before
  timing out to be configurable

## [2.30.3] - 2024-10-10
### Changed
- Changed `BootSetStatus` type from Enum to IntEnum, to allow inequality comparisons
- Reverted change in `2.30.1` now that inequalities work as expected

### Fixed
- Fixed type hint for `validate_boot_sets` function

## [2.30.2] - 2024-10-09
### Changed
- If an image artifact lacks `boot_parameters`, log this as informational instead of a warning.

## [2.30.1] - 2024-10-09
### Fixed
- Fix bug in sessions controller, attempting >= comparison with enumerated types.

## [2.30.0] - 2024-10-07
### Added
#### BOS options
- `ims_errors_fatal`: This determines whether or not an IMS failure
  is considered fatal even when BOS could continue despite the failure. Specifically,
  this comes up when validating image architecture in a boot set. By default
  this is false. Note that this has no effect for boot sets that:
  - Have non-IMS images
  - Have IMS images but the image does not exist in IMS
  - Have `Other` architecture
- `ims_images_must_exist`: This determines whether or not BOS considers it a fatal error if
  a boot set has an IMS boot image which does not exist in IMS. If false (the default), then
  BOS will only log warnings about these. If true, then these will cause boot set validations
  to fail. Note that if `ims_images_must_exist` is true but `ims_errors_fatal` is false, then
  a failure to determine whether or not an image is in IMS will NOT result in a fatal error.

### Changed
- Refactored some BOS Options code to use abstract base classes, to avoid code duplication.
- Alphabetized options in API spec
- Refactored `controllers/v2/boot_sets.py` into its own module, for clarity

## [2.29.0] - 2024-10-01
### Added
- Run `pylint` during builds
- When validating boot sets, if a boot artifact is missing from a manifest, include the manifest S3 URL
  in the associated message.
- Add check that at least one hardware-specifier field is non-empty to `validate_sanitize_boot_sets`
- When validating boot sets (at session template patch/creation/validation or session creation),
  attempt to validate that the specified architecture matches that of the corresponding IMS image.
  Mismatches are fatal errors.

### Changed
- Marked PATCH session status endpoint to be ignored by the CLI.
- Eliminate redundancies in API spec by defining `V2SessionNameOrEmpty` schema.
- Refactor `validate_boot_sets` function into multiple functions to make it easier to understand.
- During migration to this BOS version, for boot sets with no `arch` field, add the field with its
  default value.

### Fixed
- When validating boot sets, check all boot sets for severe errors before returning only warnings

## [2.28.0] - 2024-09-11
### Added
- Added `reject_nids` BOS option, to reject Sessions and Session Template which appear to reference NIDs.

### Changed
- Sanitize BOS data during migration to this BOS version, to ensure it complies with the API specification.
  - For components and sessions, only validate the fields used to identify them (name, id, tenant). Delete them
    from the database if these fields have problems.
  - For templates, validate all fields, but do a more complete attempt to automatically clean them up,
    only deleting them as a last resort.
- Do not delete migration job after it completes; instead, set a TTL value for it, to allow time for its logs to be
  collected after it completes.

## [2.27.0] - 2024-09-05
### Changed
- Improve server code that validates incoming data
- Relax session naming restrictions to match template naming restrictions, removing unnecessary constraints

### Fixed
- Added missing required Python modules to `requirements.txt`

### Dependencies
- Move to `openapi-generator-cli` v7.8.0
- Move to `cray-service` base chart version v11.0

## [2.26.3] - 2024-08-28
### Fixed
- Update TAPMS endpoint for CSM 1.6.

## [2.26.2] - 2024-08-23
### Dependencies
- Simplify how latest patch version of `liveness` is determined
- Use `requests_retry_session` Python package instead of duplicating its content

## [2.26.1] - 2024-08-22
### Fixed
- Fix boot set schema validation bug preventing valid session templates from being created

## [2.26.0] - 2024-08-20
### Added
- BOS automatically tags IMS images with the 'sbps-project: true' tag when using SBPS as the rootfs provider.

## [2.25.0] - 2024-08-15
### Changed
- Modified API spec to enforce previously-recommended limits
- Make `BootSetName` a write-only property in a boot set, and require it to be equal to the name mapping to that
  boot set inside the session template that contains it
- Modified session template creation and patching to validate boot set names
- Require boot sets to have some form of node/group/role list specified

### Dependencies
- Move to `openapi-generator-cli` v7.7.0

## [2.24.0] - 2024-08-09
### Fixed
- Added the authorization token back into the bos-reporter.

### Dependencies
- Move to `redis` Python library version 5.0
- Move Redis container from 5.0-alpine3.12 to 7.2-alpine3.18

## [2.23.0] - 2024-07-30
### Added
- New BOS v2 option `session_limit_required`
  - If set, new sessions must have a limit specified
  - When creating a BOS session, specifying a limit value of `*` has the effect of not limiting
    the session, which is one way to create a non-limited session if `session_limit_required` is set.

### Changed
- List Python packages after installing, for build log purposes

### Removed
- Removed unused `BootSetNamePathParam` schema from the API spec (a vestige of BOS v1)
- Removed inaccurate docstring from `_sanitize_xnames`; removed unnecessary return value

### Dependencies
- Pin major/minor versions for Python packages, but use latest patch version

## [2.22.0] - 2024-07-23
### Added
- Add request timeouts to BOS reporter API calls
- Create new BOS v2 `max_component_batch_size` option to limit number of components a BOS operator
  will work on at once.

### Changed
- Code linting (no functional changes)

### Fixed
- Handle case where no path value is set in boot set in `boot_image_metadata/factory.py`
- Raise exception when there is an error getting the service version

### Removed
- Removed redundant `duration_to_timedelta` function definition from BOS reporter source.

## [2.21.0] - 2024-07-12

### Fixed
- The applystage operation works again. It was broken when multi-tenancy support was added.
- Fix incorrect exception instantiation arguments in `boot_image_metadata/factory.py`

### Removed
- Remove vestigial `BASEKEY` definition from sessions and templates server controller source files
- Remove unnecessary (and invalid) `__all__` assignment from `__init__.py` in filters module

## [2.20.0] - 2024-06-05
### Fixed
- Some schemas in the API used the `format` keyword to mean `pattern`, and thus the patterns they specified were not being
  interpreted or enforced. This fixes that.

## [2.19.0] - 2024-06-05
### Dependencies
- Bumped `certifi` from 2022.12.7 to 2023.7.22 to resolve [SNYK-PYTHON-CERTIFI-5805047 CVE](https://security.snyk.io/vuln/SNYK-PYTHON-CERTIFI-5805047)
- Bumped `Flask` from 2.1.1 to 2.2.5 to resolve [SNYK-PYTHON-FLASK-5490129 CVE](https://snyk.io/vuln/SNYK-PYTHON-FLASK-5490129)

## [2.18.2] - 2024-05-31
### Fixed
- Instantiate S3 client in a thread-safe manner.

## [2.18.1] - 2024-05-30
### Changed
- Remove `__pycache__` directories from BOS reporter RPM

### Fixed
- Include `bos.common` dependency in BOS reporter RPM

## [2.18.0] - 2024-05-22
### Changed
- Increase memory requests and limits for BOS pods, to prevent OOM kill issues seen at scale.
- Set UWSGI `max-requests` and `harakiri` options to help avoid OOM and scaling issues.

### Dependencies
- Bumped `openapi-generator-cli` from v6.6.0 to v7.6.0

### Fixed
- Addressed linter complaints

## [2.17.7] - 2024-05-16
### Changed
- Added more checks to avoid operating on empty lists
- Compact response bodies to single line before logging them
- Improve BOS logging of unexpected errors

## [2.17.6] - 2024-04-19
### Fixed
- Corrected description of `disable_components_on_completion` in API spec.

## [2.17.5] - 2024-04-19
### Changed
- Reduced v2 default polling frequency from 60 seconds to 15 seconds, to improve performance
- Reconciled discrepancies in default v2 option values between `src/bos/operators/utils/clients/bos/options.py`
  and `src/bos/server/controllers/v2/options.py`

## [2.17.4] - 2024-03-29
### Changed
- Make BOS be more efficient when patching CFS components.

### Fixed
- Switch from CFS v2 to v3 to avoid running afoul of page size limitations

## [2.17.3] - 2024-03-28
### Changed
- Use POST instead of GET when requesting node power status from PCS, to avoid
  size limitations on the GET parameters.

## [2.17.2] - 2024-03-27
### Added
- Add code to the beginning of some CFS functions to check if they have been called without
  necessary arguments, and if so, to log a warning and return immediately.
- Added similar code to some PCS functions.
- Created `PowerControlComponentsEmptyException`; raise it when some PCS functions receive
  empty component list arguments.

### Changed
- If the status operator `_run` method finds no enabled components, stop immediately, as there is
  nothing to do.

## [2.17.1] - 2024-03-21
### Changed
- Improvements to BOS v2 debug logging.

## [2.17.0] - 2024-03-15
### Dependencies
- Use appropriate version of `kubernetes` Python module to match CSM 1.6 Kubernetes version

### Removed
- BOS v1

## [2.16.0] - 2024-03-15
### Changed
- Install uWSGI using `apk` instead of `pip`; update uWSGI config file to point to Python virtualenv

## [2.15.4] - 2024-03-12
### Fixed
- Update base operator to handle case where all nodes to act on have exceeded their retry limit

## [2.15.3] - 2024-03-08
### Changed
- Reduce superfluous S3 calls during BOSv2 session creation.

## [2.15.2] - 2024-03-07
### Fixed
- Break up large CFS component queries to avoid errors

## [2.15.1] - 2024-03-04
### Fixed
- Corrected minor errors in a couple description fields in API spec (no functional impact)

## [2.15.0] - 2024-02-13
### Changed
- Updated API spec to reflect the actual API behavior: a component filter must have exactly one
  property specified (`session` or `ids`), but not both.
- Modified API server for `v2/components`:
  - Add minor debug logging to match what is done in `v2/sessions` methods
  - Validate incoming component put/patch requests against the schema
  - Gracefully handle the case where a components filter includes nonexistent component IDs
    (instead of returning with a 500 internal server error)

## [2.14.0] - 2024-02-06
### Added
- Scalable Boot Provisioning Service (SBPS) support

### Changed
- Removed unintended ability to update v2 session fields other than `status` and `components`.

## [2.13.0] - 2024-01-10
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
