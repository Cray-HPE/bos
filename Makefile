# Copyright 2021 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# (MIT License)

NAME ?= cray-bos
CHART_PATH ?= kubernetes
VERSION := @DOCKER_VERSION@
SPEC_VERSION := @RPM_VERSION@
CHART_VERSION := @CHART_VERSION@

HELM_UNITTEST_IMAGE ?= quintush/helm-unittest:3.3.0-0.2.5

# Common RPM variables
BUILD_METADATA ?= "1~development~$(shell git rev-parse --short HEAD)"
BUILD_DIR ?= $(PWD)/dist/rpmbuild

# bos-reporter RPM variables
RPTR_SPEC_NAME ?= bos-reporter
RPTR_SPEC_FILE ?= ${RPTR_SPEC_NAME}.spec
RPTR_SOURCE_NAME ?= ${RPTR_SPEC_NAME}-${SPEC_VERSION}
RPTR_SOURCE_PATH := ${BUILD_DIR}/SOURCES/${RPTR_SOURCE_NAME}.tar.bz2

# Test RPM variables
TEST_SPEC_NAME ?= bos-crayctldeploy-test
TEST_SPEC_FILE ?= ${TEST_SPEC_NAME}.spec
TEST_SOURCE_NAME ?= ${TEST_SPEC_NAME}-${SPEC_VERSION}
TEST_SOURCE_PATH := ${BUILD_DIR}/SOURCES/${TEST_SOURCE_NAME}.tar.bz2

all : prepare image chart rptr_rpm test_rpm
chart: chart_setup chart_package chart_test
rptr_rpm: rptr_rpm_package_source rptr_rpm_build_source rptr_rpm_build
test_rpm: test_rpm_package_source test_rpm_build_source test_rpm_build

prepare:
		./runLint.sh
		rm -rf $(BUILD_DIR)
		mkdir -p $(BUILD_DIR)/SPECS $(BUILD_DIR)/SOURCES
		cp $(RPTR_SPEC_FILE) $(TEST_SPEC_FILE) $(BUILD_DIR)/SPECS/

image:
		docker build --pull ${DOCKER_ARGS} --tag '${NAME}:${VERSION}' .

chart_setup:
		mkdir -p ${CHART_PATH}/.packaged
		printf "\nglobal:\n  appVersion: ${VERSION}" >> ${CHART_PATH}/${NAME}/values.yaml

chart_package:
		helm dep up ${CHART_PATH}/${NAME}
		helm package ${CHART_PATH}/${NAME} -d ${CHART_PATH}/.packaged --app-version ${VERSION} --version ${CHART_VERSION}

chart_test:
		helm lint "${CHART_PATH}/${NAME}"
		docker run --rm -v ${PWD}/${CHART_PATH}:/apps ${HELM_UNITTEST_IMAGE} -3 ${NAME}

rptr_rpm_package_source:
		tar --transform 'flags=r;s,^,/$(RPTR_SOURCE_NAME)/,' \
			--exclude .git \
			--exclude ./dist \
			--exclude ./$(TEST_SPEC_FILE) \
			--exclude ./ct-tests \
			-cvjf $(RPTR_SOURCE_PATH) .

rptr_rpm_build_source:
		BUILD_METADATA=$(BUILD_METADATA) rpmbuild -ts $(RPTR_SOURCE_PATH) --define "_topdir $(BUILD_DIR)"

rptr_rpm_build:
		BUILD_METADATA=$(BUILD_METADATA) rpmbuild -ba $(RPTR_SPEC_FILE) --define "_topdir $(BUILD_DIR)"

test_rpm_package_source:
		tar --transform 'flags=r;s,^,/$(TEST_SOURCE_NAME)/,' \
			--exclude .git \
			--exclude ./dist \
			--exclude ./$(RPTR_SPEC_FILE) \
			--exclude ./api \
			--exclude ./api_tests \
			--exclude ./config \
			--exclude ./Dockerfile \
			--exclude ./kubernetes \
			--exclude ./lib \
			--exclude ./src \
			--exclude ./tools \
			-cvjf $(TEST_SOURCE_PATH) .

test_rpm_build_source:
		BUILD_METADATA=$(BUILD_METADATA) rpmbuild -ts $(TEST_SOURCE_PATH) --define "_topdir $(BUILD_DIR)"

test_rpm_build:
		BUILD_METADATA=$(BUILD_METADATA) rpmbuild -ba $(TEST_SPEC_FILE) --define "_topdir $(BUILD_DIR)"
