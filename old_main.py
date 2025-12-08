"""Old unused monolithic structure of dataconv project.

Not recommended to use and might not work as expected or not work at all.
Kept for reference after refactoring.

Usage:
    $ python old_main.py "from input.json to output.yaml"
    $ python old_main.py "from data.json[users.*] to output.toml where age > 25"
"""

import json
import toml
import yaml
import xmltodict
from jsonpath_ng import parse
import argparse
import sys
import os
from lark import Lark, Transformer

# syntax should be dataconv file.json (from) file.toml (to) where "author": "James Smith"

# 1 loading file
def smart_load_wrapper(filename) -> dict:
    with open(filename, "r", encoding="utf-8") as file:
        if filename.endswith(".json"):
            return json.load(file)
        elif filename.endswith(".toml"):
            return toml.load(file)
        elif filename.endswith(".yaml") or filename.endswith(".yml"):
            return yaml.safe_load(file)
        elif filename.endswith(".xml"):
            return xmltodict.parse(file.read())
        else:
            raise ValueError(f"Unsupported file format: {filename}")

# 2 saving file
def smart_save(data, filepath, *args, **kwargs):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            if filepath.endswith(".json"):
                json.dump(data, f, *args, **kwargs)
            
            elif filepath.endswith(".toml"):
                toml.dump(data, f)

            elif filepath.endswith(('.yaml', '.yml')):
                yaml.safe_dump(data, f, **kwargs)

            elif filepath.endswith(".xml"):
                xmltodict.unparse(data, output=f, **kwargs)

            else:
                raise ValueError(f"Unsupported file format: {filepath}")
    except Exception as e:
        print(f"There was an error while saving the file {filepath}: ", e)
        return None
    return filepath


# 3. verification
def validate_json(data, path="$") -> list:
    import math

    errors = []
    
    def _walk(v, p):
        nonlocal errors

        if v is None or isinstance(v, (int, str, bool)):
            return

        elif isinstance(v, float):
            if not math.isfinite(v):
                errors.append(f"{p}: non-finite float {v}")
            return

        elif isinstance(v, dict):
            for k, subv in v.items():
                if not isinstance(k, str):
                    errors.append(f"{p}: non-string key {k}")
                _walk(subv, f"{p}.{k}")
            return

        elif isinstance(v, list):
            for i, subv in enumerate(v):
                _walk(subv, f"{p}[{i}]")
            return
        else:
            errors.append(f"{p}: {v} is not a valid value")

    _walk(data, path)
    return errors

def validate_toml(data, path="$") -> list:
    import math
    from datetime import datetime, date, time

    warnings = []
    errors = []

    def _walk(v, p):
        nonlocal errors, warnings

        if v is None or isinstance(v, (int, str, bool, datetime, date, time)):
            return

        elif isinstance(v, float):
            if not math.isfinite(v):
                errors.append(f"{p}: non-finite float {v}")
            return

        elif isinstance(v, dict):
            for k, subv in v.items():
                if not isinstance(k, str):
                    errors.append(f"{p}: non-string key {k}")
                _walk(subv, f"{p}.{k}")
            return

        elif isinstance(v, list):
            if v:
                first_type = type(v[0])
                if not all(isinstance(elem, first_type) for elem in v):
                    warnings.append(f"{p}: all elements in list must be of the same type (TOML requirement)")
            for i, subv in enumerate(v):
                _walk(subv, f"{p}[{i}]")
            return
        else:
            errors.append(f"{p}: {v} is not a valid value")

    _walk(data, path)
    return errors, warnings

def validate_yaml(data, path="$") -> list:
    from datetime import datetime, date
    from decimal import Decimal
    import math

    errors = []
    warnings = []

    def _walk(v, p):
        nonlocal errors, warnings

        if v is None or isinstance(v, (int, str, bool, datetime, date, Decimal)):
            return

        elif isinstance(v, float):
            if not math.isfinite(v):
                errors.append(f"{p}: non-finite float {v}")
            return

        elif isinstance(v, dict):
            for k, subv in v.items():
                if not isinstance(k, str):
                    warnings.append(f"{p}: non-string key. Not recommended for YAML {k}")
                _walk(subv, f"{p}.{k}")
            return

        elif isinstance(v, list):
            for i, subv in enumerate(v):
                _walk(subv, f"{p}[{i}]")
            return
        else:
            errors.append(f"{p}: {v!r} (type {type(v).__name__}) is not a valid YAML value")

    _walk(data, path)
    return errors, warnings

def validate_xml(data, path="$") -> list:
    errors = []
    import math
    def _walk(v, p):
        nonlocal errors

        if isinstance(v, dict):
            for k, subv in v.items():
                if not isinstance(k, str):
                    errors.append(f"{p}: non-string key {k!r} (XML tag/attr must be str)")
                _walk(subv, f"{p}.{k}")
            return

        elif isinstance(v, list):
            for i, subv in enumerate(v):
                _walk(subv, f"{p}[{i}]")
            return
        
        try:
            _ = str(v)
        except Exception as e:
            errors.append(
                f"{p}: value {v!r} (type {type(v).__name__}) "
                f"is not convertible to string for XML: {e}"
            )
    _walk(data, path)
    return errors

def validate(data, target_format: str):
    fmt = target_format.lower()
    if fmt == "json":
        return validate_json(data), []
    elif fmt == "toml":
        return validate_toml(data)
    elif fmt == "yaml":
        return validate_yaml(data)
    elif fmt == "xml":
        return validate_xml(data), []
    else:
        raise ValueError(f"Unsupported file format: {target_format}")


# 4. conditioning
def smart_condition(data, expression: str):
    try:
        return [m.value for m in parse(expression).find(data)]
    except Exception as e:
        raise ValueError(f"Invalid expression: {expression}")

# 4.5 remake conditioning similarly to sql language

QUERY_GRAMMAR = r"""
?start: query

query: "from" file_path "to" file_path ("where" condition_list)?

file_path: FILE path_bracket?

path_bracket: "[" path_expression "]"

path_expression: NAME (="." NAME)* array_wildcard?
array_wildcard: "*"

condition_list: condition ("and" condition)* 
condition: field OP value
field: NAME
OP: "==" | "!=" | ">" | "<" | ">=" | "<="

value: STRING
     | SIGNED_NUMBER
     | TRUE
     | FALSE
     | NULL

FILE: /[a-zA-Z0-9_\-\/\.]+/
NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
TRUE: "true"
FALSE: "false"

%import common.SIGNED_NUMBER
%import common.STRING
%import common.WS
%ignore WS
"""


class QueryTransformer(Transformer):
    def NAME(self, token):
        return token.value
    
    def STRING(self, token):
        return token.value[1:-1]

    def SIGNED_NUMBER(self, token):
        return float(token.value)

    def TRUE(self, token):
        return True

    def FALSE(self, token):
        return False

    def NULL(self, token):
        return None

    def OP(self, token):
        return token.value

    def condition(self, children):
        return {
            'field': children[0],
            'op': children[1],
            'value': children[2],
        }

    def condition_list(self, children):
        return children

    def file_path(self, children):
        file = children[0]
        path = children[1] if len(children) > 1 else None
        return {'file': file, 'path': path}

    def path_bracket(self, children):
        return children[1]

    def path_expression(self, children):
        parts = [str(c) for c in children if str(c) != "."]

        if parts and parts[-1] == "*":
            parts[-2] += "*"
            parts.pop()

        return ".".join(parts)

    def query(self, children):
        return {
            'source': children[1],
            'dest': children[3],
            'conditions': children[4] if len(children) > 4 else [],
        }

# 5. misc
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data Converter CLI")
    parser.add_argument("input", help="Input file path")
    parser.add_argument("output", help="Output file path")
    parser.add_argument("condition", nargs="*", help="Optional condition starting with 'where'")

    args = parser.parse_args()

    # 1. Load
    print(f"Loading {args.input}...")
    try:
        data = smart_load_wrapper(args.input)
    except Exception as e:
        print(f"Error loading file: {e}")
        sys.exit(1)

    # 2. Condition
    if args.condition:
        if args.condition[0].lower() == "where":
            expression = " ".join(args.condition[1:])
            print(f"Applying condition: {expression}")
            try:
                data = smart_condition(data, expression)
            except Exception as e:
                print(f"Error applying condition: {e}")
                sys.exit(1)
        else:
             print("Warning: Condition arguments provided but 'where' keyword missing. Ignoring condition.")

    # 3. Validate
    target_format = os.path.splitext(args.output)[1][1:] # remove dot
    if not target_format:
        print("Error: Output file must have an extension.")
        sys.exit(1)

    print(f"Validating data for {target_format}...")
    try:
        errors, warnings = validate(data, target_format)
        for w in warnings:
            print(f"Warning: {w}")
        if errors:
            print("Validation Errors:")
            for e in errors:
                print(f"  - {e}")
            print("Aborting save due to validation errors.")
            sys.exit(1)
    except ValueError as e:
        print(f"Validation setup error: {e}")
        sys.exit(1)

    # 4. Save
    print(f"Saving to {args.output}...")
    # Handle list data for TOML/XML which require dict root
    if isinstance(data, list):
        if target_format.lower() == 'toml':
             print("Warning: Data is a list, wrapping in {'root': data} for TOML compatibility.")
             data = {"root": data}
        elif target_format.lower() == 'xml':
             print("Warning: Data is a list, wrapping in {'root': {'item': data}} for XML compatibility.")
             data = {"root": {"item": data}}

    res = smart_save(data, args.output)
    if res:
        print("Done.")
    else:
        print("Failed to save.")
        sys.exit(1)