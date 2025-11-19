# v0.31.5 (unreleased)

## Enhancement of issue #640

- **Customizable Artist Separators**: Full control over how multiple artists are displayed in metadata tags and filenames.
  - Choose from 6 OS-safe whitelisted separators: comma (`,`), semicolon (`;`), ampersand (`&`), plus (`+`), hyphen (`-`), or bullet (`•`)
  - Independently configure spacing before and after each separator
  - Separate configurations for:
    - Metadata artist tags (e.g., for ID3/FLAC)
    - Metadata album artist tags
    - Filename artist display
    - Filename album artist display
  - Perfect for Jellyfin/Emby users who prefer semicolon separators (`;`) for proper artist linking
  - Backward compatible with existing configurations (defaults to legacy `, ` format)
  - Accessible through GUI settings dialog under "Artist Delimiters" section

## Technical Improvements

- Refactored delimiter logic from hardcoded strings to atomic configuration parameters
- Added comprehensive test suite (39 tests) covering all delimiter combinations and edge cases
- Implemented automatic migration from legacy delimiter format to new atomic parameters
- Added validation to prevent injection of invalid characters into filenames and metadata

# v0.4.11

- Fixes regarding empty metadata tags (also fixes #1).
- CLI downloader extended to handle playlists and mixes.
- `Download.track()` now handles logger functions.
- GUI build for macOS and asset upload.

# v0.4.9

- Fixed: Exception on missing file read (config, token) instead of creation.

# v0.4.8

- Fixed: GUI dependencies are treated as extra now (pip).

# v0.4.7

- Fixed: GUI dependencies are treated as extra now (pip).

# v0.4.6

- GUI dependencies are treated as extra now (pip).

# v0.4.5

- Fixed "Mix" download.
- Fixed relative imports.
- Fixed PyPi build.
- Fixed crash on lyrics error.

# v0.4.2

- Added more basic features.

# v0.4.1

- Initial featured running version.
