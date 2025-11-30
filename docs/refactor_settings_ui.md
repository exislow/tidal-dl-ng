# Settings Window Refactor

Date: 2025-11-30
Author: Automation (Copilot)

## Goal

Refactor the settings window to improve usability and maintainability:

- Category list on the left
- Settings content on the right via QStackedWidget
- Clear separation of pages (Flags, Quality, Numbers, Paths & Formats, Delimiters)
- Consistent dark styling and tuned spacing
- Add unit and integration tests (61 total)

## Key Changes

### 1. UI Architecture

- Navigation column: `QListWidget (lw_categories)`
- Pages container: `QStackedWidget (sw_categories)`
- Pages created:
  - `page_flags` (GroupBox: gb_flags)
  - `page_quality` (GroupBox: gb_choices)
  - `page_numbers` (GroupBox: gb_numbers)
  - `page_paths` (GroupBox: gb_path)
  - `page_delimiters` (GroupBox: gb_delimiters) — NEW

Impacted file: `tidal_dl_ng/ui/dialog_settings.ui` (auto-generated `dialog_settings.py`).

### 2. New Category: Delimiters

- "Delimiters" page with 4 `QLineEdit` fields to edit separators:
  - `metadata_delimiter_artist`
  - `metadata_delimiter_album_artist`
  - `filename_delimiter_artist`
  - `filename_delimiter_album_artist`
- Automatic integration with `DialogPreferences` through `parameters_line_edit`, `populate_line_edit()` and `to_settings()`.

Files touched:

- `tidal_dl_ng/ui/dialog_settings.ui` (new page)
- `tidal_dl_ng/ui/dialog_settings.py` (regenerated)
- `tidal_dl_ng/dialog.py` (added 4 parameters and new category in `_init_categories`).

### 3. Styles & Spacing

- Category list: dark style, blue selection, gray hover, light text.
- Vertical spacing: list item margin `2px 0px` (and optional view spacing).
- Settings area: dark background (QStackedWidget), styled GroupBoxes.

Files touched:

- `tidal_dl_ng/ui/dialog_settings.ui` (stylesheets on lw_categories and sw_categories)
- `tidal_dl_ng/ui/dialog_settings.py` (regenerated).

### 4. Tests

- New files:
  - `tests/test_settings_ui.py`: UI and basic integration (14)
  - `tests/test_settings_dialog_structure.py`: detailed structure (20)
  - `tests/test_dialog_preferences_integration.py`: DialogPreferences integration (14)
  - `tests/test_delimiters_category.py`: Delimiters page (13)
- Total: **61 tests**; ruff/black/pyupgrade applied via pre-commit.

### 5. Pre-commit & Quality

- Ruff fixes:
  - F841 (unused variable) in `test_dialog_preferences_integration.py`
  - S108 (using /tmp) replaced by `Path.home()` and safe values
- end-of-file-fixer and black reformatted automatically.

## Usage

### Launch the UI

- Via the app: `poetry run tidal-dl-ng-gui` (or `python -m tidal_dl_ng.gui`)

### Navigate

- Select a category in `lw_categories`
- The corresponding page shows in `sw_categories`.

### Edit separators

- Open the "Delimiters" category
- Edit fields `le_metadata_delimiter_*` and `le_filename_delimiter_*`
- Confirm via OK

## Known issue: poetry+dulwich KeyError b'HEAD

- Cause: dulwich cannot resolve HEAD in the Git repo when Poetry queries VCS info.
- Fix: ensure `.git/HEAD` points to an existing branch (e.g. `ref: refs/heads/main`) and the branch exists; then re-run `poetry install`. See commands below.

## Useful Commands (PowerShell)

```powershell
cd C:\Users\mathe\PycharmProjects\tidal-dl-ng
poetry check --lock
poetry run pre-commit run -a
pytest -q
```

To fix HEAD if needed:

```powershell
cd C:\Users\mathe\PycharmProjects\tidal-dl-ng
Get-Content .git\HEAD
# If empty/incorrect:
git init
git add .
git commit -m "Initialize repo for Poetry/Dulwich"
git branch -M main
Get-Content .git\HEAD
poetry install -vvv --no-interaction --all-extras --with dev,docs
```

## Impact

- Better UX: category navigation, improved readability
- Extensible: easy to add new pages/settings
- Quality: comprehensive tests ensure robustness

## Next Steps

- Add contextual help (tooltips) for new delimiter fields
- Optionally adjust list spacing (8–10) based on feedback
- Add a preview of resulting formatting (e.g., sample metadata)
