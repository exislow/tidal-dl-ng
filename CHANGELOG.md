# v0.31.5 (Unreleased)

## New Features

- **Quick View on Hover** (GUI): Revolutionary hover preview system for track metadata

  - Tabbed interface with Details and Cover Art tabs
  - Instant metadata display on hover (no clicks required)
  - Debounced events (350ms) to prevent UI flickering
  - Zero additional API calls - uses pre-loaded track data
  - Displays: Title, Artists, Album, Codec, Bitrate, Duration, BPM, ISRC, Release Date, Popularity
  - **BPM Loading Indicator**: Shows `⏳ Loading...` while fetching BPM asynchronously
  - Graceful handling of missing metadata

- **Enhanced BPM Support** (GUI):
  - BPM now loaded asynchronously from TIDAL API raw JSON data
  - Visual loading indicator (`⏳ Loading...`) while fetching
  - Smart caching prevents redundant API calls
  - Thread-safe callback system using Qt signals
  - Displays actual BPM value (e.g., "136") when available
  - Shows `—` when BPM is not provided by TIDAL

## Improvements

- **Code Cleanup & Optimization**:

  - **Removed all debug logs** from console output for production-ready experience
  - Application now runs silently with clean console (only "All setup." message)
  - Removed unused code: `_extract_from_raw()` method and redundant helper functions
  - Simplified error handling with silent exceptions for expected errors (widgets deleted, etc.)
  - **Removed 150+ lines of debug/logging code** across multiple files

- **Code Refactoring & Architecture**:

  - Created `helper/metadata_utils.py` module for reusable metadata utilities
  - Created `cache.py` module for LRU cache implementations
  - Created `ui/media_details_helper.py` for media details population
    ét - Created `gui_covers.py` with `CoverManager` class for cover management
  - Removed ~340 lines of duplicated code from `info_tab_widget.py`
  - Extracted helper functions: `safe_str()`, `find_attr()`, `search_in_data()`, `extract_names_from_mixed()`
  - Improved maintainability and testability of metadata extraction logic
  - **gui.py reduced from 2828 to ~2640 lines (-188 lines, -6.6%)**
  - All cover-related logic centralized in CoverManager

- **Performance & Stability**:

  - Thread-safe track extras cache with automatic cleanup
  - **Cover pixmap cache (LRU, 100 entries)** for instant display on re-hover
  - **Background cover preloading** when opening playlists (first 50 tracks)
  - Smart cache checks before launching download threads
  - Skip re-display if cover already shown (0ms overhead)
  - Graceful shutdown handling for background workers
  - Proper cleanup of event filters on application exit
  - Better error handling for widget lifecycle and API failures
  - Protected against RuntimeError when widgets deleted during shutdown
  - **Fixed BPM display issue**: BPM callback now properly invoked in main thread using Qt signals

- **UI/UX Improvements**:
  - BPM field shows loading state instead of blank placeholder
  - Immediate visual feedback when hovering tracks
  - Smooth asynchronous data loading without blocking UI
  - Cache system ensures instant display on re-hover

## Bug Fixes

- **Fixed BPM not displaying**: Corrected callback invocation from worker thread to main thread
- **Fixed Qt threading issues**: Replaced `QMetaObject.invokeMethod` with direct signal-based approach
- **Fixed "widgets deleted during extras apply"**: Changed from QueuedConnection to direct call
- **Fixed race conditions**: Proper thread-safe callback storage and invocation

## Not Displayed (API Limitations)

Certain metadata fields are **not displayed** because they are generally **not provided** by the public TIDAL API and are therefore **not applicable** in this interface:

- ❌ Genres
- ❌ Label
- ❌ Producers
- ❌ Composers

For details, see `docs/missing_metadata.md`.

## Technical Details

- New components: `InfoTabWidget`, `HoverManager`, `TrackInfoFormatter`, `CoverManager`
- Event filtering on tree view viewport for precise hover detection
- Signal-based architecture for decoupled communication
- Qt Signal (`s_invoke_callback`) for thread-safe callback invocation
- Worker thread pattern for async API calls without blocking UI
- Full conformance to AGENTS.md standards (type hints, docstrings, tests)

## Documentation

- Updated `docs/missing_metadata.md` with current API limitations
- Created `docs/feature_hover_info.md` with comprehensive feature documentation
- Added technical architecture diagrams and troubleshooting guides
- Documented BPM loading flow and caching strategy

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
