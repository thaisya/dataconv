"""dataconv - Universal data format converter.

Minimal API with 6 functions for programmatic data conversion:
    convert()      - Simple conversion with JSONPath support
    query()        - Full query language power
    load()         - Auto-detect and load any format
    save()         - Auto-detect and save any format
    filter()       - In-memory data filtering
    extract_path() - JSONPath extraction

Usage:
    from dataconv import convert, query, load, save
    
    # Simple conversion
    convert("data.json", "output.yaml")
    
    # With options as kwargs
    convert("data.json", "output.yaml", indent=4, encoding="utf-16")
    
    # Full query power
    query("from data.json[$.users[*]] to output.yaml where age > 25")
"""

from .api import convert, query, load, save, filter, extract_path

__version__ = "1.0.0"
__all__ = ["convert", "query", "load", "save", "filter", "extract_path"]
