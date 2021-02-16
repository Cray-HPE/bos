# Copyright 2020-2021 Hewlett Packard Enterprise Development LP

Name: bos-crayctldeploy-test
License: Cray Software License Agreement
Summary: Cray post-install tests for Boot Orchestration Services (BOS)
Group: System/Management
Version: %(cat .rpm_version_bos-crayctldeploy-test)
Release: %(echo ${BUILD_METADATA})
Source: %{name}-%{version}.tar.bz2
Vendor: Cray Inc.
Requires: cray-cmstools-crayctldeploy-test >= 0.2.8
Requires: python3-requests

# Test defines. These may make sense to put in a central location
%define tests /opt/cray/tests
%define smsfunc %{tests}/sms-functional
%define smslong %{tests}/sms-long
%define testdat %{tests}/dat
%define testlib %{tests}/lib

# CMS test defines
%define smsfunccms %{smsfunc}/cms
%define smslongcms %{smslong}/cms
%define cmsdat %{testdat}/cms
%define cmslib %{testlib}/cms
%define cmscommon %{cmslib}/common

# BOS test defines
%define bosfunctestdat %{cmsdat}/bos_functional_test
%define bosfunctestlib %{cmslib}/bos_functional_test
%define boslimittestlib %{cmslib}/bos_limit_test

%description
This is a collection of post-install tests for Boot Orchestration Services (BOS).

%prep
%setup -q

%build

%install
# Install test wrapper scripts
install -m 755 -d %{buildroot}%{smsfunccms}/
install ct-tests/bos_api_functional_test.sh %{buildroot}%{smsfunccms}
install ct-tests/bos_cli_functional_test.sh %{buildroot}%{smsfunccms}

install -m 755 -d %{buildroot}%{smslongcms}/
install ct-tests/bos_limit_api_test.sh %{buildroot}%{smslongcms}
install ct-tests/bos_limit_cli_test.sh %{buildroot}%{smslongcms}

# Install shared test libraries
# The cmscommon directory should already exist, since we have
# cray-cmstools-crayctldeploy-test as a prerequisite, but just in
# case...
install -m 755 -d %{buildroot}%{cmscommon}/
install -m 644 ct-tests/lib/common/bos.py %{buildroot}%{cmscommon}

# Install BOS functional test
install -m 755 ct-tests/lib/bos_functional_test.py %{buildroot}%{cmslib}
install -m 755 -d %{buildroot}%{bosfunctestdat}/
install -m 644 ct-tests/dat/bos_functional_test/bos_session_template.json %{buildroot}%{bosfunctestdat}
install -m 755 -d %{buildroot}%{bosfunctestlib}/
install -m 644 ct-tests/lib/bos_functional_test/__init__.py %{buildroot}%{bosfunctestlib}
install -m 644 ct-tests/lib/bos_functional_test/argparse.py %{buildroot}%{bosfunctestlib}
install -m 644 ct-tests/lib/bos_functional_test/helpers.py %{buildroot}%{bosfunctestlib}

# Install BOS limit test
install -m 755 ct-tests/lib/bos_limit_test.py %{buildroot}%{cmslib}
install -m 755 -d %{buildroot}%{boslimittestlib}/
install -m 644 ct-tests/lib/bos_limit_test/__init__.py %{buildroot}%{boslimittestlib}
install -m 644 ct-tests/lib/bos_limit_test/argparse.py %{buildroot}%{boslimittestlib}
install -m 644 ct-tests/lib/bos_limit_test/bos.py %{buildroot}%{boslimittestlib}
install -m 644 ct-tests/lib/bos_limit_test/hsm.py %{buildroot}%{boslimittestlib}
install -m 644 ct-tests/lib/bos_limit_test/utils.py %{buildroot}%{boslimittestlib}

# Install BOS loop test
install -m 755 ct-tests/lib/bos_loop.py %{buildroot}%{cmslib}

%clean
rm -f %{buildroot}%{smsfunccms}/bos_api_functional_test.sh
rm -f %{buildroot}%{smsfunccms}/bos_cli_functional_test.sh

rm -f %{buildroot}%{smslongcms}/bos_limit_api_test.sh
rm -f %{buildroot}%{smslongcms}/bos_limit_cli_test.sh

rm -f %{buildroot}%{cmscommon}/bos.py

rm -f %{buildroot}%{cmslib}/bos_functional_test.py
rm -f %{buildroot}%{bosfunctestdat}/bos_session_template.json
rm -f %{buildroot}%{bosfunctestlib}/__init__.py
rm -f %{buildroot}%{bosfunctestlib}/argparse.py
rm -f %{buildroot}%{bosfunctestlib}/helpers.py

rm -f %{buildroot}%{cmslib}/bos_limit_test.py
rm -f %{buildroot}%{boslimittestlib}/__init__.py
rm -f %{buildroot}%{boslimittestlib}/argparse.py
rm -f %{buildroot}%{boslimittestlib}/bos.py
rm -f %{buildroot}%{boslimittestlib}/hsm.py
rm -f %{buildroot}%{boslimittestlib}/utils.py

rm -f %{buildroot}%{cmslib}/bos_loop.py

rmdir %{buildroot}%{boslimittestlib}
rmdir %{buildroot}%{bosfunctestdat}
rmdir %{buildroot}%{bosfunctestlib}

%files
%defattr(755, root, root)
%dir %{bosfunctestdat}
%dir %{bosfunctestlib}
%dir %{boslimittestlib}

%attr(755, root, root) %{smsfunccms}/bos_api_functional_test.sh
%attr(755, root, root) %{smsfunccms}/bos_cli_functional_test.sh
%attr(755, root, root) %{smslongcms}/bos_limit_api_test.sh
%attr(755, root, root) %{smslongcms}/bos_limit_cli_test.sh

%attr(644, root, root) %{cmscommon}/bos.py

%attr(755, root, root) %{cmslib}/bos_functional_test.py
%attr(644, root, root) %{bosfunctestdat}/bos_session_template.json
%attr(644, root, root) %{bosfunctestlib}/__init__.py
%attr(644, root, root) %{bosfunctestlib}/argparse.py
%attr(644, root, root) %{bosfunctestlib}/helpers.py

%attr(755, root, root) %{cmslib}/bos_limit_test.py
%attr(644, root, root) %{boslimittestlib}/__init__.py
%attr(644, root, root) %{boslimittestlib}/argparse.py
%attr(644, root, root) %{boslimittestlib}/bos.py
%attr(644, root, root) %{boslimittestlib}/hsm.py
%attr(644, root, root) %{boslimittestlib}/utils.py

%attr(755, root, root) %{cmslib}/bos_loop.py

%changelog
