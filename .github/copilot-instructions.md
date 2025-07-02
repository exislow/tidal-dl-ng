---
applyTo: "**/*.py"
---

# Project general coding standards

## Naming Conventions

- Use snake_case for variable and function names.
- Use CamelCase for class names.
- Follow PEP 8 style guidelines.
- Prefix private class members with underscore (\_).
- Use ALL_CAPS for constants.

## Error Handling

- Use try/except blocks for async operations.
- Always log errors with contextual information.

## Coding Guidelines

- Use type annotations / hints for function and method parameters, return types and variables. Follow PEP 484.
- Use the modern built-in generics from the `typing` module, such as `list`, `dict`, and `set`, instead of the older `List`, `Dict`, and `Set` from `typing`.
- Use newest coding style which is supported by the used Python version.
- Use more blank lines to achieve better code organization and readability.
- Follow PEP 492 – Coroutines with async and await syntax
- Follow PEP 498 – Literal String Interpolation
- Follow PEP 572 – Assignment Expressions

## Code Documentation

- Always write doc strings for all modules, classes, functions, and methods using google docstring style.
- Use typing in doc strings.
- Use line comments to explain complex logic.
- If refactoring code, ensure to update or add doc strings accordingly.
- If refactoring code to not remove existing line comments, but to update them to reflect the new code logic.
