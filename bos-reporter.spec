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
Name: bos-reporter
License: MIT
Summary: A program system service which reports BOS' Boot Artifact ID for a given node
Group: System/Management
Version: @RPM_VERSION@
Release: %(echo ${BUILD_METADATA})
Source: %{name}-%{version}.tar.bz2
Vendor: HPE
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}
Requires: python3-base
Requires: python3-requests
Requires: systemd
Requires: cray-auth-utils

# Death to Fascist build policies
%define _unpackaged_files_terminate_build 0
%define _systemdsvcdir /usr/lib/systemd/system
%define craydir /opt/cray
%define rpminfo %{craydir}/.rpm_info/%{name}/%{version}/%{release}

%description
Provides a systemd service and associated library that reports
BOS' Boot Artifact ID for a node throughout its booted life.

%{!?python3_sitelib: %define python3_sitelib %(/usr/bin/python3 -c "from distutils.sysconfig import get_python_lib ; print(get_python_lib())")}

%prep
%setup -q

%build
pushd ./src
/usr/bin/python3 setup.py build
popd

%install
rm -rf %{buildroot}

# Install RPM git build info file
install -m 755 -d %{buildroot}%{rpminfo}/
install gitInfo.txt %{buildroot}%{rpminfo}

pushd ./src
/usr/bin/python3 setup.py install -O1 --skip-build --root %{buildroot}
mkdir -p ${RPM_BUILD_ROOT}%{_systemdsvcdir}
cp bos/reporter/etc/bos-reporter.service %{buildroot}/%{_systemdsvcdir}/bos-reporter.service
chmod +x %{buildroot}/%{python3_sitelib}/bos/reporter/status_reporter/__main__.py
popd

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root)
%dir %{rpminfo}
%attr(644, root, root) %{rpminfo}/gitInfo.txt

%dir %{python3_sitelib}/bos
%{python3_sitelib}/bos/reporter
%dir %{_systemdsvcdir}
%{_systemdsvcdir}/bos-reporter.service

%pre
%if 0%{?suse_version}
%service_add_pre bos-reporter.service
%endif

%post
ln -f /usr/bin/spire-agent /usr/bin/bos-reporter-spire-agent
%if 0%{?suse_version}
%service_add_post bos-reporter.service
%else
%systemd_post bos-reporter.service
%endif

%preun
%if 0%{?suse_version}
%service_del_preun bos-reporter.service
%else
%systemd_preun bos-reporter.service
%endif

%postun
if [ $1 -eq 0 ];then
  rm -f /usr/bin/bos-reporter-spire-agent
fi
%if 0%{?suse_version}
%service_del_postun bos-reporter.service
%else
%systemd_postun_with_restart bos-reporter.service
%endif
