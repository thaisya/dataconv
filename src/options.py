"""Configuration options for data conversion operations.

This module provides the OptionsConfig dataclass that centralizes all conversion
settings, eliminating scattered **kwargs throughout the codebase.
"""

from dataclasses import dataclass, asdict
from typing import Any, Literal


@dataclass(frozen=True)
class OptionsConfig:
    """Immutable configuration for data conversion operations.
    
    Attributes:
        atomic: Enable atomic writes (temp file + rename) for data safety
        allow_unicode: Allow Unicode characters in YAML output
        pretty: Enable pretty-printing for XML output
        indent: Indentation level for JSON output (when not using orjson)
        array_strategy: How to handle arrays in CSV ("json", "explode", or "skip")
        array_field: Field to explode when using array_strategy="explode" (auto-detects if None)
        ignore_nested: Skip nested dictionaries and arrays during CSV flattening
        preserve_dots: Escape dots in keys with backslash during CSV flattening
    
    Examples:
        >>> config = OptionsConfig()
        >>> config.atomic
        True
        >>> new_config = config.merge(atomic=False)
        >>> new_config.atomic
        False
    """
    # Global I/O options
    atomic: bool = True
    
    # Format-specific options
    allow_unicode: bool = True  # YAML
    pretty: bool = True         # XML
    indent: int = 2             # JSON (when not using orjson) NOT RECOMMENDED TO CHANGE
    
    # CSV-specific options
    array_strategy: Literal["json", "explode", "skip"] = "json"
    array_field: str | None = None
    ignore_nested: bool = False
    preserve_dots: bool = False

    def merge(self, **overrides: Any) -> 'OptionsConfig':
        """Create new OptionsConfig with specified overrides.
        
        Returns a new immutable instance with modified values while
        preserving unspecified options.
        
        Args:
            **overrides: Options to override (e.g., atomic=False)
        
        Returns:
            New OptionsConfig instance with merged values
        
        Raises:
            TypeError: If invalid field names are provided
        
        Examples:
            >>> config = OptionsConfig()
            >>> new_config = config.merge(atomic=False, array_strategy="explode")
            >>> new_config.atomic
            False
            >>> new_config.array_strategy
            'explode'
            >>> config.atomic  # Original unchanged
            True
        """
        try:
            # Convert dataclass to dict
            current = asdict(self)
            # Update with overrides
            current.update(overrides)
            # Create new frozen instance
            return OptionsConfig(**current)
        except TypeError as e:
            raise TypeError (
                f"Invalid field names provided: {set(overrides.keys()) - set(current.keys())}"
                ) from e