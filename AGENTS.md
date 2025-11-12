---
applyTo: "**/*.py"
---

# Project General Coding Standards

## Python Version Support

- Target Python 3.12 and 3.13
- Use modern Python features supported by the minimum version (3.12)
- Avoid deprecated features and use future-proof syntax

## Naming Conventions

- Use snake_case for variable and function names
- Use CamelCase for class names
- Follow PEP 8 style guidelines strictly
- Prefix private class members with underscore (\_)
- Use ALL_CAPS for constants
- Use descriptive names that clearly indicate purpose and content
- Avoid single-letter variable names except for loop counters or mathematical contexts

## Type Annotations

- Use type annotations for ALL function and method parameters, return types, and variables (PEP 484)
- Use modern built-in generics: `list`, `dict`, `set`, `tuple` instead of `List`, `Dict`, `Set`, `Tuple` from `typing`
- Use `None` type for optional parameters: `str | None` instead of `Optional[str]`
- Use union types with `|` operator: `int | str` instead of `Union[int, str]`
- For complex types, import from `collections.abc`: `Callable`, `Iterable`, etc.
- Always specify generic types: use `list[str]` not just `list`
- Use `pathlib.Path` for file paths, not `str`

## Error Handling

- Use try/except blocks for operations that may fail
- Always log errors with contextual information using the project's logger
- Catch specific exceptions, avoid bare `except:` clauses
- Use `finally` blocks for cleanup operations
- For HTTP operations with requests library:
  - Use timeout parameter (default: `REQUESTS_TIMEOUT_SEC`)
  - Implement retry logic with `requests.adapters.Retry` for network operations
  - Always close response objects in `finally` blocks or use context managers
- For file operations:
  - Use context managers (`with` statement) for file handling
  - Use `pathlib.Path` methods for path operations
  - Handle `OSError` and its subclasses appropriately

## Code Style and Formatting

- Line length: maximum 120 characters (as configured in Black and Ruff)
- Use Black formatting style with preview features enabled
- Follow isort configuration for import ordering:
  1. FUTURE
  2. TYPING
  3. STDLIB
  4. THIRDPARTY
  5. FIRSTPARTY
  6. LOCALFOLDER
- Include trailing commas in multi-line constructs
- Use more blank lines to achieve better code organization and readability
- Use 4 spaces for indentation (no tabs)

## Modern Python Features

- Follow PEP 492 – Coroutines with async and await syntax (when applicable)
- Follow PEP 498 – Literal String Interpolation (f-strings)
- Follow PEP 572 – Assignment Expressions (walrus operator `:=` when it improves readability)
- Use structural pattern matching (match/case) for Python 3.10+ when appropriate
- Prefer pathlib.Path over os.path for file operations
- Use Enum and StrEnum for constants with related values
- Use dataclasses or dataclasses-json for structured data

## Concurrency and Threading

- Use `concurrent.futures.ThreadPoolExecutor` for I/O-bound parallel operations
- Always use context managers with executors
- Set appropriate `max_workers` based on operation type (use configuration values)
- Handle futures with `futures.as_completed()` for better responsiveness
- Implement abort/cancellation mechanisms using `threading.Event`
- Cancel pending futures when aborting operations
- Use thread-safe data structures when sharing data between threads
- Avoid blocking operations in GUI threads

## Resource Management

- Always use context managers (`with` statements) for:
  - File operations
  - Network connections
  - Thread pools and executors
  - Temporary directories and files
- Use `tempfile.TemporaryDirectory` with `ignore_cleanup_errors=True` for temp operations
- Close network responses explicitly in `finally` blocks or use context managers
- Clean up temporary files after processing
- Use `pathlib.Path.unlink(missing_ok=True)` for safe file deletion

## File and Path Handling

- Use `pathlib.Path` exclusively for path operations
- Sanitize file paths using `pathvalidate.sanitize_filename` and project's `path_file_sanitize`
- Use `.expanduser()` for paths that may contain `~`
- Use `.absolute()` to get absolute paths
- Use `.resolve()` to resolve symlinks
- Check file existence with `Path.exists()`, `Path.is_file()`, `Path.is_dir()`
- Use `os.makedirs(path, exist_ok=True)` or `Path.mkdir(parents=True, exist_ok=True)`
- Handle cross-platform path differences automatically with pathlib

## Code Documentation

- Write docstrings for ALL modules, classes, functions, and methods using Google docstring style
- Include type information in docstrings even when type hints are present
- Document all parameters with their types and descriptions
- Document return values with type and description
- Document raised exceptions
- Use line comments to explain complex logic, algorithms, or non-obvious decisions
- When refactoring code:
  - Update or add docstrings to reflect new behavior
  - Update existing line comments rather than removing them
  - Add TODO comments for known limitations or future improvements

## Logging

- Use the project's logger (via `fn_logger` or similar)
- Log levels:
  - `debug`: Detailed diagnostic information
  - `info`: General informational messages (e.g., download completion)
  - `error`: Error conditions with context
  - `exception`: Errors with full traceback
- Include relevant context in log messages (file names, IDs, URLs, etc.)
- Use f-strings for log message formatting

## GUI Development (PySide6/Qt)

- Follow Qt naming conventions for slots and signals
- Use type hints for signal parameters
- Emit signals for cross-thread communication (never call GUI methods directly from worker threads)
- Use Qt's threading mechanisms appropriately
- Handle GUI progress updates via signals
- Implement proper cleanup in close events
- Use `QThread` or `ThreadPoolExecutor` for background operations, never block the GUI thread

## API Integration (TIDAL)

- Always check if media is available before processing (`media.available`)
- Handle `tidalapi.exceptions.TooManyRequests` gracefully
- Implement retry logic for transient failures
- Use sessions appropriately
- Handle stream manifests and encryption properly
- Respect API rate limits and implement delays when configured

## Testing

- Place tests in the `tests/` directory
- Use pytest as the testing framework
- Use descriptive test function names: `test_<functionality_being_tested>`
- Test edge cases: empty lists, None values, invalid inputs
- Mock external dependencies (API calls, file system when appropriate)
- Use fixtures for common test setup
- Aim for meaningful test coverage, not just high percentages

## Security

- Never hardcode credentials (use configuration or environment variables)
- Use base64 encoding only for obfuscation, not security
- Handle sensitive data (tokens, keys) carefully
- Use secure temporary file creation
- Validate and sanitize all user inputs, especially file paths
- Handle decryption keys securely (don't log them)

## Performance

- Use generators for large datasets when possible
- Implement streaming for large file downloads
- Use appropriate chunk sizes for file I/O (use `CHUNK_SIZE` constant)
- Cache expensive computations when safe to do so
- Use batch operations where applicable
- Profile code before optimizing
- Consider memory usage for large collections

## Configuration and Settings

- Use the Settings class for all configuration
- Access settings via `self.settings.data.*`
- Validate configuration values
- Provide sensible defaults
- Use type-safe configuration access
- Document configuration options

## Code Quality Tools

- Run Ruff for linting before committing
- Run Black for formatting before committing
- Run mypy for type checking
- Use pre-commit hooks to automate checks
- Address all linting warnings and errors
- Keep code complexity low (avoid deep nesting, long functions)

## Best Practices Summary

1. **Type Safety**: Always use type hints, enable strict mypy checks
2. **Error Handling**: Catch specific exceptions, log with context, clean up resources
3. **Readability**: Write self-documenting code with clear names and structure
4. **Documentation**: Comprehensive docstrings and comments for complex logic
5. **Testing**: Test edge cases and error conditions
6. **Performance**: Use efficient algorithms and data structures
7. **Maintainability**: Keep functions focused, avoid code duplication
8. **Security**: Validate inputs, handle credentials safely
9. **Compatibility**: Support Python 3.12-3.13, handle cross-platform differences
10. **Standards**: Follow PEP 8, PEP 484, and project-specific configurations
