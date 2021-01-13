#!/bin/bash
# Copyright 2019, Cray Inc. All Rights Reserved.

# the scanner requires pylint
pip install pylint
ln -s /usr/bin/pylint /usr/local/bin/

# extract coverage.xml to replace container file paths
# with local ones
cd results
tar -ztvf buildResults.tar.gz
tar -xzf buildResults.tar.gz
rm -rf buildResults.tar.gz
cp testing/*.xml .

SOURCE="${WORKSPACE}/src/server"
sed -i "s|/app/lib|$SOURCE|" coverage.xml

# output coverage for troubleshooting if needed
cat coverage.xml
