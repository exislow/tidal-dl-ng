# Hover Info Feature

## Quick Preview on Hover

TIDAL Downloader NG includes a revolutionary hover preview system that displays track metadata instantly when you hover over tracks in the results list.

### Features

- **Instant Display**: Track information appears immediately on hover (no clicks required)
- **Tabbed Interface**:
  - **Details Tab**: Shows comprehensive track metadata
  - **Cover Art Tab**: Displays album artwork
- **Smart Debouncing**: 350ms delay prevents UI flickering when moving the mouse
- **Zero Extra API Calls**: Uses pre-loaded track data from search results
- **Efficient Caching**: Previously viewed tracks display instantly

### Displayed Information

#### Basic Information (Instant)

- **Title**: Track name
- **Version**: Track version/remix info (if available)
- **Artists**: Track artists
- **Track #**: Track number in album
- **Album**: Album name
- **Duration**: Track length (mm:ss)
- **Codec**: Audio quality (LOSSLESS, AAC, etc.)
- **Bitrate**: Audio bitrate (or N/A for variable bitrate)
- **Release Date**: Album release date
- **Popularity**: Track popularity score
- **ISRC**: International Standard Recording Code

#### Enhanced Information (Async)

- **BPM**: Beats per minute ⏳ (loaded asynchronously from API)
  - Shows `⏳ Loading...` while fetching (~100-500ms)
  - Displays actual BPM value when available
  - Shows `—` if not available

### Cover Art Display

- **Automatic Loading**: Album covers are loaded in the background
- **Smart Caching**: Covers are cached for instant display on re-hover
- **Preloading**: First 50 tracks in playlists are preloaded for better UX
- **Fallback**: Default album image shown if cover is unavailable

### Technical Details

#### Architecture

```
User hovers over track
    ↓
HoverManager detects hover (debounced 350ms)
    ↓
InfoTabWidget receives update signal
    ↓
_populate_track_details() displays basic info instantly
    ↓
_request_track_extras_if_needed() triggers async fetch
    ↓
Worker thread fetches BPM from TIDAL API
    ↓
Qt Signal invokes callback in main thread
    ↓
_update_extras_ui() updates BPM label
```

#### Performance Optimizations

1. **LRU Cache**: 256-entry cache for track extras
2. **Cover Cache**: 100-entry cache for album covers
3. **Thread-Safe**: All background operations are thread-safe
4. **Event Filtering**: Precise hover detection on tree view viewport
5. **Graceful Degradation**: Handles missing metadata gracefully

### User Experience

#### On First Hover

```
Title:        Fortuna       ✅ Instant
Artists:      Asco          ✅ Instant
Duration:     03:40         ✅ Instant
Codec:        LOSSLESS      ✅ Instant
BPM:          ⏳ Loading... ⏱️ Loading indicator (~200ms)
              ↓
BPM:          136           ✅ Loaded!
```

#### On Subsequent Hover (Same Track)

```
Title:        Fortuna       ✅ Instant
Artists:      Asco          ✅ Instant
Duration:     03:40         ✅ Instant
BPM:          136           ✅ Instant (from cache)
```

### Limitations

Due to TIDAL API limitations, the following fields are **not applicable** in this hover view (they are generally not provided by the public API and thus not displayed):

- ❌ Genres
- ❌ Label
- ❌ Producers
- ❌ Composers

See [missing_metadata.md](missing_metadata.md) for detailed information about API limitations.

### Code Components

- **`InfoTabWidget`**: Main widget for displaying track information
- **`HoverManager`**: Manages hover events on tree view
- **`CoverManager`**: Handles cover art loading and caching
- **`TrackInfoFormatter`**: Formats track metadata for display
- **`TrackExtrasCache`**: LRU cache for async-loaded metadata

### Configuration

The hover delay is configurable in the code:

```python
# In hover_manager.py
self.hover_delay = 350  # milliseconds
```

Lower values = more responsive but may flicker
Higher values = more stable but less responsive

### Troubleshooting

**BPM not displaying?**

- Check console for API errors
- Verify track has BPM in TIDAL (not all tracks do)
- Cache may have stale data (restart application)

**Cover not loading?**

- Check network connection
- Some tracks may not have cover art
- Default image will be shown as fallback

**Hover not working?**

- Ensure you're hovering over the results tree view
- Check that the application has focus
- Debounce delay may need adjustment
