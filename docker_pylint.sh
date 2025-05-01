#!/usr/bin/env sh
#
# MIT License
#
# (C) Copyright 2024-2025 Hewlett Packard Enterprise Development LP
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

if [[ $# -eq 1 && $1 == "mypy" ]]; then
  outfile=$(mktemp) || exit 1
  if mypy $(cat ./srclist.txt) > "${outfile}" 2>&1; then
    cat "${outfile}"
    rm "${outfile}"
    exit 0
  fi
  # Even if we pass in a list of source files to mypy, it will still report errors in other files
  # So we grep the results and only show the stuff in our source code
  grep_args=$(cat ./srclist.txt)
  grep_args=$(echo ${grep_args} | sed 's/^[[:space:]]\+//' | sed 's/[[:space:]]\+$//' | sed 's/[[:space:]]\+/|/g')
  grep -E "^(${grep_args}):" "${outfile}"
  rc=$?
  rm "${outfile}"
  # If rc = 0, it means there was at least one error about our own source files
  # If rc != 0, it means that the only errors were from other source files
  if [[ $rc -eq 0 ]]; then
    exit 1
  fi
  echo "No mypy errors for BOS source files"
  exit 0
else
  pylint "$@" $(cat ./srclist.txt)
fi
