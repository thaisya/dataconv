"""Grammar definitions for the Data Converter query language.

This module contains the Lark grammar for parsing data conversion queries.
The query language allows specifying source and destination files with optional
JSONPath expressions and conditional filters.

Grammar Syntax:
    from <source_file>[path.expression.*] to <dest_file> where field == value and ...

Examples:
    >>> # Basic conversion
    >>> "from input.json to output.yaml"

    >>> # With path extraction
    >>> "from data.json[users.*] to output.toml"

    >>> # With conditions
    >>> "from data.json to output.yaml where age > 25 and status == \"active\""
"""

from typing import Final

QUERY_GRAMMAR: Final[str] = r"""
%import common.SIGNED_NUMBER
%import common.ESCAPED_STRING
%import common.WS

?start: query

query: "from" file_path "to" file_path ("where" condition_list)?

file_path: (FILE | ESCAPED_STRING) path_bracket?

path_bracket: "[" path_expression "]" 

path_expression: NAME ("." NAME)* ("." array_wildcard)?
array_wildcard: "*"

condition_list: condition ("and" condition)*
condition: field OP value
field: NAME
OP: "==" | "!=" | ">" | "<" | ">=" | "<="

value: ESCAPED_STRING
     | SIGNED_NUMBER
     | TRUE
     | FALSE
     | NULL

FILE: /[a-zA-Z0-9_\-\/\.]+/ 
NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
TRUE: "true"
FALSE: "false"
NULL: "null"

%ignore WS
"""
