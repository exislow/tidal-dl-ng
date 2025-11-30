# "Delimiters" Category

## Goal

Allow users to customize separators used for artists and album artists, both in metadata and filenames.

## Parameters

- `metadata_delimiter_artist`: artists separator (metadata)
- `metadata_delimiter_album_artist`: album artists separator (metadata)
- `filename_delimiter_artist`: artists separator (filename)
- `filename_delimiter_album_artist`: album artists separator (filename)

## UI

- Page `page_delimiters` inside `sw_categories`
- GroupBox `gb_delimiters`
- 4 `QLineEdit` entries (`le_*`) with max width 100px

## Integration

- Add the 4 fields to `DialogPreferences.parameters_line_edit`
- Load values via `populate_line_edit()`
- Save via `to_settings()`

## Tests

- `tests/test_delimiters_category.py`: 13 tests
  - Page existence
  - Widgets accessibility
  - Navigation to the page
  - Width constraints

## Examples

- Semicolon: `"; "` → `Artist1; Artist2`
- Ampersand: `" & "` → `Artist1 & Artist2`
- Slash: `" / "` → `Artist1 / Artist2`

## Notes

- Default values are `", "` (comma + space)
- Fields are kept short (max 100px) to avoid breaking the layout
