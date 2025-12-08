"""Data processing with JSONPath extraction and conditional filtering.

This module provides functionality to extract data using JSONPath expressions
and filter results based on conditional expressions.

Example:
    >>> from src.processor import apply_path, apply_conditions
    >>>
    >>> data = {'users': [{'name': 'John', 'age': 30}, {'name': 'Jane', 'age': 25}]}
    >>> result = apply_path(data, "users.*")
    >>> # result = [{'name': 'John', 'age': 30}, {'name': 'Jane', 'age': 25}]
    >>>
    >>> conditions = [{'field': 'age', 'op': '>', 'value': 26}]
    >>> filtered = apply_conditions(result, conditions)
    >>> # filtered = [{'name': 'John', 'age': 30}]
"""

import logging
from dataclasses import dataclass
from typing import Any

from jsonpath_ng import parse  # type: ignore
from jsonpath_ng.exceptions import JsonPathParserError  # type: ignore

from src.parser import Condition

logger = logging.getLogger(__name__)


class ProcessorError(Exception):
    """Exception raised when data processing fails."""

    pass


@dataclass
class ProcessorConfig:
    """Configuration for data processor.

    Attributes:
        strict_mode: If True, raise errors on type mismatches in comparisons
    """

    strict_mode: bool = False


def apply_path(data: dict[str, Any], path: str | None) -> Any:
    """Extract data using JSONPath expression.

    Args:
        data: Source data dictionary
        path: JSONPath expression (e.g., "users.*", "config.database.host")
              If None or empty, returns original data

    Returns:
        Extracted data. If path matches multiple items, returns list of values.
        If single match, returns the matched value.

    Raises:
        ProcessorError: If JSONPath expression is invalid

    Example:
        >>> data = {'users': [{'name': 'John'}, {'name': 'Jane'}]}
        >>> apply_path(data, "users[*].name")
        ['John', 'Jane']
    """
    if not path:
        logger.debug("No path specified, returning original data")
        return data

    try:
        logger.debug(f"Applying JSONPath: {path}")
        jsonpath_expr = parse(f"$.{path}")
        matches = jsonpath_expr.find(data)

        if not matches:
            logger.warning(f"JSONPath expression '{path}' matched no results")
            return []

        results = [match.value for match in matches]

        # Return single value if only one match, otherwise return list
        if len(results) == 1:
            logger.info(f"JSONPath '{path}' matched 1 result")
            return results[0]
        else:
            logger.info(f"JSONPath '{path}' matched {len(results)} results")
            return results

    except JsonPathParserError as e:
        logger.error(f"Invalid JSONPath expression '{path}': {e}")
        raise ProcessorError(f"Invalid JSONPath expression '{path}': {e}") from e
    except Exception as e:
        logger.error(f"Error applying JSONPath '{path}': {e}")
        raise ProcessorError(f"Error applying path '{path}': {e}") from e


def evaluate_condition(value: Any, op: str, expected: Any) -> bool:
    """Evaluate a single condition.

    Performs type-safe comparison with basic type coercion for numbers.

    Args:
        value: The actual value to check
        op: Comparison operator (==, !=, >, <, >=, <=)
        expected: The expected value to compare against

    Returns:
        Boolean result of the comparison

    Raises:
        ProcessorError: If operator is not supported

    Example:
        >>> evaluate_condition(30, '>', 25)
        True
        >>> evaluate_condition('John', '==', 'John')
        True
    """
    # Handle None comparisons
    if value is None or expected is None:
        if op == "==":
            return value == expected
        elif op == "!=":
            return value != expected
        else:
            return False

    # Type coercion for numeric comparisons
    try:
        if isinstance(value, (int, float)) and isinstance(expected, (int, float)):
            value_num = float(value)
            expected_num = float(expected)
        else:
            value_num = value
            expected_num = expected

        # Perform comparison
        if op == "==":
            return value_num == expected_num
        elif op == "!=":
            return value_num != expected_num
        elif op == ">":
            return value_num > expected_num  # type: ignore
        elif op == "<":
            return value_num < expected_num  # type: ignore
        elif op == ">=":
            return value_num >= expected_num  # type: ignore
        elif op == "<=":
            return value_num <= expected_num  # type: ignore
        else:
            raise ProcessorError(f"Unsupported operator: {op}")

    except TypeError as e:
        logger.warning(
            f"Type error in condition evaluation: {value} {op} {expected}: {e}"
        )
        return False


def apply_conditions(
    data: list[dict[str, Any]], conditions: list[Condition]
) -> list[dict[str, Any]]:
    """Filter list of dictionaries based on conditions.

    All conditions must be satisfied (AND logic).

    Args:
        data: List of dictionaries to filter
        conditions: List of conditions (each has field, op, value)

    Returns:
        Filtered list containing only items matching all conditions

    Example:
        >>> data = [{'name': 'John', 'age': 30}, {'name': 'Jane', 'age': 25}]
        >>> conditions = [{'field': 'age', 'op': '>=', 'value': 26}]
        >>> apply_conditions(data, conditions)
        [{'name': 'John', 'age': 30}]
    """
    if not conditions:
        logger.debug("No conditions specified, returning all data")
        return data

    if not isinstance(data, list):
        logger.warning(f"Expected list for filtering, got {type(data).__name__}")
        # Wrap single items in a list
        data = [data] if isinstance(data, dict) else []

    logger.debug(f"Applying {len(conditions)} condition(s) to {len(data)} items")

    filtered_results: list[dict[str, Any]] = []

    for item in data:
        if not isinstance(item, dict):
            logger.warning(f"Skipping non-dict item: {type(item).__name__}")
            continue

        # Check all conditions (AND logic)
        matches_all = True
        for cond in conditions:
            field = cond["field"]
            op = cond["op"]
            expected = cond["value"]

            # Get field value from item
            value = item.get(field)

            if not evaluate_condition(value, op, expected):
                matches_all = False
                break

        if matches_all:
            filtered_results.append(item)

    logger.info(
        f"Filtered {len(data)} items to {len(filtered_results)} "
        f"matching all {len(conditions)} condition(s)"
    )

    return filtered_results


def process_data(
    data: dict[str, Any],
    path: str | None,
    conditions: list[Condition],
) -> Any:
    """Process data by applying path extraction and conditions.

    This is a convenience function that combines path extraction and filtering.

    Args:
        data: Source data dictionary
        path: Optional JSONPath expression
        conditions: Optional list of filter conditions

    Returns:
        Processed data (extracted and filtered)

    Example:
        >>> data = {'users': [{'name': 'John', 'age': 30}, {'name': 'Jane', 'age': 25}]}
        >>> conditions = [{'field': 'age', 'op': '>', 'value': 26}]
        >>> result = process_data(data, "users.*", conditions)
        >>> # result = [{'name': 'John', 'age': 30}]
    """
    logger.debug(
        f"Processing data with path='{path}' and {len(conditions)} condition(s)"
    )

    # Step 1: Apply path extraction
    extracted = apply_path(data, path)

    # Step 2: Apply conditions if any
    if conditions:
        # Ensure data is a list for filtering
        if not isinstance(extracted, list):
            extracted = [extracted] if isinstance(extracted, dict) else []

        extracted = apply_conditions(extracted, conditions)

    return extracted
