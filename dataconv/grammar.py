"""Grammar definitions for the Data Converter query language.

This module contains the Lark grammar for parsing data conversion queries.
The query language allows specifying source and destination files with optional
JSONPath expressions and conditional filters.

Grammar Syntax:
    from <source_file>[jsonpath_expression] to <dest_file> where field == value and ...

Examples:
    >>> # Basic conversion
    >>> "from input.json to output.yaml"

    >>> # With JSONPath extraction
    >>> "from data.json[users[*]] to output.toml"
    >>> "from data.json[users[0].name] to output.yaml"

    >>> # With conditions
    >>> "from data.json to output.yaml where age > 25 and status == \"active\""
"""

from typing import Final

QUERY_GRAMMAR: Final[str] = r"""
%import common.SIGNED_NUMBER
%import common.ESCAPED_STRING
%import common.WS

?start: query

query: "from" file_path ("to" file_path)? ("where" condition_list)?

file_path: (FILE | ESCAPED_STRING) path_bracket?

path_bracket: "[" path_content "]"

path_content: (path_segment | nested_bracket | quoted_string)+

nested_bracket: "[" path_content "]"

quoted_string: ESCAPED_STRING | SINGLE_QUOTED_STRING

path_segment: /[^\[\]"]+/

condition_list: xor_expr

xor_expr: or_expr ("xor" or_expr)*

or_expr: and_expr ("or" and_expr)*

and_expr: not_expr ("and" not_expr)*

not_expr: negation
        | atom

negation: "!" not_expr

atom: "(" xor_expr ")"
    | comparison
    | field_check

comparison: field OP field_value

field: NAME
field_value: "!"? value
field_check: field

OP: "==" | "!=" | ">" | "<" | ">=" | "<="

value: ESCAPED_STRING
     | SINGLE_QUOTED_STRING
     | SIGNED_NUMBER

     | SIGNED_NUMBER
     | TRUE
     | FALSE
     | NULL
     | NAME

FILE: /[a-zA-Z0-9_\-\/\.]+/ 
NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
TRUE: "true"
FALSE: "false"
NULL: "null"
SINGLE_QUOTED_STRING: /'([^'\\\\]|\\\\.)*'/

%ignore WS
"""
