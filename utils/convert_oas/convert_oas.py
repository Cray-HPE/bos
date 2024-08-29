#
# MIT License
#
# (C) Copyright 2024 Hewlett Packard Enterprise Development LP
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

"""
Converts/cleanses the schemas in the BOS OpenAPI spec to be a valid json schema

This module uses the match construct, which means it requires Python 3.10+.
Currently, the only time any of the BOS code uses a lower Python version is BOS state reporter,
and that has no need to call this module. In fact, it is expected that this module is only
going to be called at build time from the Dockerfile.
"""

import argparse
import json
import sys
from typing import TextIO

import jsonref

class ConversionException(Exception):
    """
    Raised for some errors during the conversion process
    """

def _cleanse_schema(schema):
    if not isinstance(schema, dict):
        raise ConversionException(
            f"Expecting schema to be type dict, but found type {type(schema).__name__}: {schema}")
    if len(schema) == 1:
        key = list(schema.keys())[0]
        match key:
            case '$ref':
                # If this is a $ref, then we're done
                return
            case 'not':
                # If this is a not, then we just parse what it maps to
                _cleanse_schema(schema[key])
                return
            case 'oneOf' | 'anyOf' | 'allOf':
                # If this is oneOf, anyOf, or allOf, then it should map to a list, and we need to
                # parse each element of that list
                if not isinstance(schema[key], list):
                    raise ConversionException(
                        f"Expecting '{key}' to map to a list, but it does not: {schema}")
                for v in schema[key]:
                    _cleanse_schema(v)
                return

    try:
        schema_type = schema["type"]
    except KeyError as exc:
        raise ConversionException(f"Schema is missing 'type' field: {schema}") from exc

    match schema_type:
        case "array":
            _cleanse_array_schema(schema)
        case "boolean" | "string":
            _cleanse_generic_schema(schema)
        case "integer" | "number":
            _cleanse_numeric_schema(schema)
        case "object":
            _cleanse_object_schema(schema)
        case _:
            raise ConversionException(f"Schema has unknown type '{schema_type}': {schema}")


def _cleanse_generic_schema(schema):
    # The nullable keyword works for OAS 3.0 but not 3.1
    if schema.pop("nullable", False):
        schema["type"] = [ schema["type"], "null" ]

    # Remove keywords that are not part of JSON schema, as well as ones which are not needed for
    # validation, and have different meanings between OAS and JSON schema
    for k in ["deprecated", "discriminator", "example", "externalDocs", "readOnly", "writeOnly",
              "xml", "description"]:
        schema.pop(k, None)


def _cleanse_array_schema(schema):
    _cleanse_generic_schema(schema)
    try:
        items_schema = schema["items"]
    except KeyError as exc:
        raise ConversionException(
            f"Array schema is missing required 'items' field: {schema}") from exc
    _cleanse_schema(items_schema)


def _cleanse_numeric_schema(schema):
    _cleanse_generic_schema(schema)
    if any(field in schema for field in [ "exclusiveMinimum", "exclusiveMaximum" ]):
        # Rather than worry about dealing with this programmatically, we should just fail.
        # This is run at build time, so if it fails, the API spec can be fixed before this
        # gets checked in.
        raise ConversionException(
            f"Integer/Number schema has exclusiveMinimum/Maximum field. Schema: {schema}")


def _cleanse_object_schema(schema):
    _cleanse_generic_schema(schema)
    object_properties = schema.get("properties", {})
    if not isinstance(object_properties, dict):
        raise ConversionException(
            f"Object schema has non-dict 'properties' value. Schema: {schema}")
    for v in object_properties.values():
        _cleanse_schema(v)

    # additionalProperties is allowed to map to a schema dict. But it's also allowed to map
    # to a boolean. Or to be absent. If it is present and mapped to a non-empty dict, then we
    # need to cleanse it.
    try:
        additional_properties = schema['additionalProperties']
    except KeyError:
        return
    if not isinstance(additional_properties, dict):
        return
    if not additional_properties:
        return
    _cleanse_schema(additional_properties)


def convert_oas(input_file: TextIO, output_file: TextIO|None=None) -> dict:
    """
    Reads in the JSON OpenAPI 3.0.x spec file.
    Converts to OpenAPI 3.1 / JSON schema.
    * Replaces all 'nullable' fields to be compliant with JSON schemas.
    * Replaces all $refs with what they are referencing.
    * Removes keywords which are either invalid or have a different meaning in JSON schemas
      (and that we don't need for our purposes for this file: validating data against
      the schema)
    * Raises an exception in cases where we'd prefer to change the API spec rather than
      handle the conversion here. Since this runs at build time, we'll know quickly
      if a change to the API spec introduces this kind of problem.

    If an output file path is specified, the result is written there in JSON.
    Either way, the result is returned.
    """
    oas = json.load(input_file)

    for oas_schema_name, oas_schema in oas["components"]["schemas"].items():
        try:
            _cleanse_schema(oas_schema)
        except Exception as exc:
            raise ConversionException(f"Error parsing schema {oas_schema_name}") from exc

    # Parse the $refs
    oas_jsonref = jsonref.loads(json.dumps(oas))

    # Replace the $refs
    oas_json_norefs = jsonref.replace_refs(oas_jsonref)

    if output_file:
        # Write to file
        json.dump(oas_json_norefs, output_file)

    return oas_json_norefs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json_file", type=argparse.FileType('rt'),
                        help="Input JSON openapi file")
    parser.add_argument("output_json_file", type=argparse.FileType('wt'), default=sys.stdout,
                        nargs='?', help="Output jsonschema-compatible openapi JSON file "
                             "(outputs to stdout if not specified)")
    args = parser.parse_args()
    convert_oas(args.input_json_file, args.output_json_file)
