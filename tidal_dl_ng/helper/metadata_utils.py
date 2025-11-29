"""Utilities for extracting and formatting metadata from TIDAL objects."""

from contextlib import suppress


def _convert_list_to_str(value: list | tuple) -> str:
    """Convert list/tuple to comma-separated string."""
    if not value:
        return "—"
    with suppress(Exception):
        return ", ".join([str(x) for x in value])
    return str(value)


def _convert_dict_to_str(value: dict) -> str:
    """Extract meaningful string from dict."""
    if "name" in value and value["name"]:
        return str(value["name"])
    for k in ("label", "title", "genre", "name"):
        if k in value and value[k]:
            return str(value[k])
    with suppress(Exception):
        vals = [str(v) for v in value.values() if v is not None]
        if vals:
            return ", ".join(vals)
    return str(value)


def safe_str(value: object) -> str:
    """Convert a potentially non-str value into a safe string for display.

    Args:
        value: The value to convert.

    Returns:
        str: Safe string representation, '—' for None/empty.
    """
    with suppress(Exception):
        if value is None:
            return "—"
        if isinstance(value, str):
            return value if value != "" else "—"
        if isinstance(value, list | tuple):
            return _convert_list_to_str(value)
        if isinstance(value, dict):
            return _convert_dict_to_str(value)
        return str(value)
    return "—"


def _find_in_dict_container(container: dict, names: tuple[str, ...]) -> object | None:
    """Search for names in a dict container."""
    for n in names:
        if n in container and container[n] is not None:
            return container[n]
    # Fuzzy key match
    keys = list(container.keys())
    for n in names:
        for k in keys:
            if n.lower() in str(k).lower():
                return container[k]
    return None


def _fuzzy_scan_attrs(obj: object, names: tuple[str, ...]) -> object | None:
    """Fuzzy scan object attributes for matching names."""
    with suppress(Exception):
        for k in dir(obj):
            kl = k.lower()
            for n in names:
                if n.lower() in kl:
                    with suppress(Exception):
                        val = getattr(obj, k)
                        if val is not None:
                            return val
    return None


def find_attr(obj: object, *names: str) -> object | None:
    """Attempt to find an attribute or data key from an object or its internals.

    Args:
        obj: The object to inspect.
        *names: Attribute/key names to search for.

    Returns:
        The found value or None.
    """
    # Direct attributes
    for n in names:
        with suppress(Exception):
            if hasattr(obj, n):
                val = getattr(obj, n)
                if val is not None:
                    return val

    # Inspect common dict-like internals
    for container_name in ("_data", "data", "__dict__"):
        with suppress(Exception):
            container = getattr(obj, container_name, None)
            if isinstance(container, dict):
                result = _find_in_dict_container(container, names)
                if result is not None:
                    return result

    # Fuzzy scan of attributes
    return _fuzzy_scan_attrs(obj, names)


def _scan_dict_recursive(container: dict, key_substrings: list[str]) -> object | None:
    """Recursively scan a dict for keys matching any substring."""
    for k, v in container.items():
        kl = str(k).lower()
        for s in key_substrings:
            if s.lower() in kl and v is not None:
                return v
        # recurse into nested structures
        if isinstance(v, dict):
            found = _scan_dict_recursive(v, key_substrings)
            if found is not None:
                return found
        if isinstance(v, list | tuple):
            for item in v:
                if isinstance(item, dict):
                    found = _scan_dict_recursive(item, key_substrings)
                    if found is not None:
                        return found
    return None


def search_in_data(obj: object, key_substrings: list[str]) -> object | None:
    """Recursively search dict-like internals for keys containing any substring.

    Args:
        obj: The object to search.
        key_substrings: List of key substrings to search for.

    Returns:
        The first matching value found, or None.
    """
    # check common containers
    for container_name in ("_data", "data", "__dict__"):
        with suppress(Exception):
            container = getattr(obj, container_name, None)
            if isinstance(container, dict):
                found = _scan_dict_recursive(container, key_substrings)
                if found is not None:
                    return found

    # as last resort, try obj.__dict__ if available
    with suppress(Exception):
        d = getattr(obj, "__dict__", None)
        if isinstance(d, dict):
            return _scan_dict_recursive(d, key_substrings)

    return None


def _extract_name_from_dict(item: dict, match_types: tuple[str, ...] | None) -> str | None:
    """Extract name from a dict if it matches type filters."""
    if "name" not in item or not item["name"]:
        return None
    if match_types:
        t = item.get("type") or item.get("role") or item.get("credit_type")
        if t and any(mt in str(t).lower() for mt in match_types):
            return str(item["name"])
        return None
    return str(item["name"])


def _extract_name_from_item(item: object) -> str | None:
    """Extract name from various item formats."""
    if item is None:
        return None
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        # Try common name keys
        for k in ("name", "artist", "person"):
            if k in item and item[k]:
                return str(item[k])
        return None
    # Try object attributes
    nm = getattr(item, "name", None) or getattr(item, "title", None)
    if nm:
        return str(nm)
    with suppress(Exception):
        return str(item)
    return None


def extract_names_from_mixed(value: object, match_types: tuple[str, ...] | None = None) -> list[str]:
    """Normalize various credit-like structures into a list of names.

    Accepts lists of dicts, dicts, strings, or objects.
    If match_types provided, only include entries where the type/role matches one of them.

    Args:
        value: The value to extract names from.
        match_types: Optional tuple of role types to filter by.

    Returns:
        List of extracted names.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        name = _extract_name_from_dict(value, match_types)
        if name:
            return [name]
        vals = [str(v) for v in value.values() if v is not None]
        return vals
    if isinstance(value, list | tuple):
        names: list[str] = []
        for item in value:
            if isinstance(item, dict):
                name = _extract_name_from_dict(item, match_types)
                if name:
                    names.append(name)
            else:
                name = _extract_name_from_item(item)
                if name:
                    names.append(name)
        return names
    return []
