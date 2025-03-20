#!/usr/bin/env python3
#
# MIT License
#
# (C) Copyright 2021-2024 Hewlett Packard Enterprise Development LP
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

import copy
import json
import re

#INFILE = "/app/openapi.json"
INFILE = "openapi.json"

ref_re = re.compile(r'^#/components/schemas/([a-zA-Z][a-zA-Z0-9]*)$')

with open(INFILE, "rt") as f:
    json_data = json.load(f)

schemas = json_data["components"]["schemas"]

completed_schemas = {}
remaining_schemas = list(schemas)

class RefNotAvailable(Exception):
    """
    Used to bubble up cases where a ref isn't done yet
    """

class SchemaError(Exception):
    def __init__(self, schema_name, schema, msg):
        super().__init__(f"Schema {schema_name}: {msg}: {schema}")

class Schema:
    def __init__(self, schema_name, schema_body=None):
        self.name = schema_name
        if schema_body is None:
            self.body = schemas[schema_name]
        else:
            self.body = schema_body

    def error(self, msg):
        return SchemaError(self.name, self.body, msg)

    @property
    def type(self):
        try:
            return self.body["type"]
        except KeyError as exc:
            raise self.error("Missing type field") from exc

    def __len__(self):
        return len(self.body)

class DataType:
    pass

class LiteralType:
    """
    Literal[val1, val2, val3...]
    """


class PrimitiveType:
    """
    int
    str
    ...
    """
    def __init__(self, mytype):
        self.mytype = mytype

    def __str__(self):
        return self.mytype.__name__


class UnionType:
    """
    a|b|c
    """
    def __init__(self, typelist):
        self.typelist = typelist

    def __str__(self):
        return '|'.join([str(t) for t in self.typelist])


class OptionalType:
    """
    Optional[type]
    """
    def __init__(self, typeclass):
        self.typeclass = typeclass

    def __str__(self):
        return f"Optional[{self.typeclass}]"


class ArrayType:
    """
    list[type]
    """
    def __init__(self, typeclass):
        self.typeclass = typeclass

    def __str__(self):
        return f"list[{self.typeclass}]"

class VagueDictType:
    def __init__(self, additional_properties):
        self.additional_properties = additional_properties

    def __str__(self):
        return f"dict[str, {self.additional_properties}]"

class SpecificDictType:
    def __init__(self, properties, required, additional_properties):
        self.additional_properties = additional_properties
        self.properties = properties
        self.required = required



def handle_ref_schema(schema: Schema):
    schema_type = "ref"
    re_match = ref_re.match(schema.body['$ref'])
    try:
        ref_target = re_match.group(1)
    except Exception as exc:
        raise schema.error(f"Invalid ref ({schema.body['$ref']})") from exc
    if ref_target not in completed_schemas:
        raise RefNotAvailable(ref_target)
    return schema_type, ref_target

def handle_not_schema(schema: Schema):
    raise schema.error("Unsupported ('not' currently unsupported by this tool)")

def handle_xof_schema(schema, key):
    # Currently this treats allOf, anyOf, and oneOf identically (that is, it maps to a Union in Python)
    subschemas = [ Schema(f"{schema.name}.{key}[{index}]", subschema_data) for index, subschema_data in enumerate(schema.body[key]) ]
    if not subschemas:
        raise schema.error(f"{key} list is empty")
    return union_schemas(*subschemas)

def handle_object_schema(schema: Schema):
    try:        
        # It is not required by the spec, but we want to be explicit, so we require this
        additional_properties = schema.body["additionalProperties"]
    except KeyError as exc:
        raise schema.error(f"Object schema missing {exc} field") from exc

    properties = schema.body.get("properties", None)
    property_info = { pname: get_schema_info(Schema(f"{schema.name}.{pname}", pinfo)) for pname, pinfo in properties.items() } if properties is not None else None
    required = schema.body.get("required", [])

    if not isinstance(additional_properties, bool):
        # Otherwise, additionalProperties specifies a schema for the additional properties to follow
        additional_properties = get_schema_info(Schema(f"{schema.name}.additionalProperties", additional_properties))

    if not property_info:
        if isinstance(additional_properties, bool) or not additional_properties:
            raise schema.error("Dict schema has no properties or additional properties")        
    elif not isinstance(additional_properties, bool) and additional_properties:
        raise schema.error("Tool does not support object schemas with both additionalProperties and properties")

    return "dict", { "properties": property_info, "required": required, "additional_properties": additional_properties }
    

def handle_array_schema(schema: Schema):
    try:
        items_schema_body = schema.body["items"]
    except KeyError as exc:
        raise schema.error("Array schema missing 'items' field") from exc
    return "list", get_schema_info(Schema(f"{schema.name}.items", items_schema_body))

schema_type_to_py_type = {
    "boolean": bool,
    "integer": int,
    "number": (float, int),
    "string": str
}

def handle_primitive_schema(schema: Schema):
    expected_type = schema_type_to_py_type[schema.type]
    enum = schema.body.get('enum', [])
    if not enum:
        if isinstance(tuple, expected_type):
            return expected_type[0]
        return expected_type

    for value in enum:
        if not isinstance(value, expected_type):
            raise schema.error(f"Enum value ({value}) does not match schema type ({schema.type})")

    if schema.type == "number":
        # Convert to float, in case the value was specified as an integer
        return "literal", [ float(value) for value in enum ]
    return "literal", enum

def union_schemas(*schemas):
    if len(schemas) == 1:
        return get_schema_info(schemas[0])
    if not schemas:
        raise Exception("union_schemas called on empty list")
    schema_info = [get_schema_info(schema) for schema in schemas]

    return "union", schema_info

def get_schema_info(schema: Schema):
    if not isinstance(schema.body, dict):
        raise schema.error("Schema not of type dict")

    if len(schema) == 1:
        key = list(schema.body.keys())[0]
        if key == '$ref':
            return handle_ref_schema(schema)
        if key == 'not':
            return handle_not_schema(schema)
        if key in { 'oneOf', 'anyOf', 'allOf' }:
            return handle_xof_schema(schema, key)

    def apply_nullable(info):
        # A nullable schema is just one where the type is a Union of None and the schema
        if schema.body.get('nullable', False):
            return "union", [info, None]
        return info

    if schema.type == 'object':
        return apply_nullable(handle_object_schema(schema))

    if schema.type == 'array':
        return apply_nullable(handle_array_schema(schema))

    if schema.type in schema_type_to_py_type:
        return apply_nullable(handle_primitive_schema(schema))

    raise schema.error(f"Unsupported type ({schema.type})")


while remaining_schemas:
    tmp_remaining_schemas = []
    for schema_name in remaining_schemas:
        try:
            completed_schemas[schema_name] = get_schema_info(Schema(schema_name))
        except RefNotAvailable:
            tmp_remaining_schemas.append(schema_name)
    remaining_schemas = tmp_remaining_schemas
