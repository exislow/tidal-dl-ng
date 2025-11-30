# Created Tests and Results

## Test files

- `tests/test_settings_ui.py` (14 tests)
- `tests/test_settings_dialog_structure.py` (20 tests)
- `tests/test_dialog_preferences_integration.py` (14 tests)
- `tests/test_delimiters_category.py` (13 tests)

## Total

- **61 tests** (unit + integration)

## Coverage

- UI creation and structure
- Category navigation
- Widgets presence and accessibility
- New "Delimiters" page
- Quality: ruff/black/pyupgrade enforced by pre-commit

## Commands

```powershell
cd C:\Users\mathe\PycharmProjects\tidal-dl-ng
poetry run pre-commit run -a
pytest -q
```

## Note

If `poetry install` fails with KeyError b'HEAD, see "Settings Window Refactor" doc to fix the Git repo’s HEAD.
