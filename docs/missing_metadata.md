# Missing Metadata in the Interface

## Why do some fields display "—" or "N/A"?

When using TIDAL Downloader NG, some metadata fields may display `—` (dash) or `N/A`. This means that **the data is not provided by the TIDAL API** for that specific track/album.

### Affected Fields

The following fields depend on data availability from the TIDAL API:

| Field         | API Source                                                          | Notes                                  | Status                    |
| ------------- | ------------------------------------------------------------------- | -------------------------------------- | ------------------------- |
| **BPM**       | Track JSON (`bpm`)                                                  | Loaded asynchronously from API         | ✅ Functional             |
| **Bitrate**   | Calculated based on codec                                           | `N/A` for LOSSLESS (variable bitrate)  | ✅ Functional             |
| **Codec**     | Track metadata                                                      | Always available (LOSSLESS, AAC, etc.) | ✅ Functional             |
| **Genres**    | Album JSON (`genres` or `genre`)                                    | Not available via TIDAL API v2         | ❌ Removed from interface |
| **Label**     | Album JSON (`label` or `recordLabel`)                               | Not reliably available                 | ❌ Removed from interface |
| **Producers** | Track/Album JSON (`credits` or `contributors` with role="producer") | Not available via TIDAL API v2         | ❌ Removed from interface |
| **Composers** | Track/Album JSON (`credits` or `contributors` with role="composer") | Not available via TIDAL API v2         | ❌ Removed from interface |

### Recent Improvements & API Limitations

**Current version**: The application retrieves available metadata from the TIDAL API:

- ✅ **BPM**: Loaded asynchronously from `track._data['bpm']` via API
- ✅ Display of basic information: title, artists, album, duration, codec, bitrate
- ✅ ISRC, track number, release date, popularity
- ❌ **Genres, Label, Producers, Composers**: Removed from interface (not available via API)

**TIDAL API Limitations**:

According to the official TIDAL OpenAPI specification analysis (https://tidal-music.github.io/tidal-api-reference/):

- ❌ **No reliable `genres` field** in API v2 (sometimes present but often empty)
- ❌ **No `credits` field** in API v2
- ❌ **No `contributors` field** in API v2
- ❌ **No `producers` field** available
- ❌ **No `composers` field** available
- ❌ **`label` and `recordLabel`** only available at album level, and often absent

The TIDAL API v2 (official JSON:API) does **NOT** reliably provide these metadata. The older API v1 (undocumented) may contain some of these fields randomly, but they are not guaranteed and depend entirely on what music labels provide to TIDAL.

### What is Actually Available

Fields **guaranteed** by the TIDAL API:

- ✅ `title`, `duration`, `isrc`, `explicit`
- ✅ `bpm` (optional, when provided by the label)
- ✅ `popularity` (0.0 - 1.0)
- ✅ `mediaTags` (HIRES_LOSSLESS, etc.)
- ✅ `artists` via relationship
- ✅ `album` via relationship
- ✅ `genres` via relationship (but often empty)

### Why is this Data Missing?

1. **TIDAL doesn't have the information**: Some metadata is not provided by music labels
2. **Data not exposed by API**: Even if TIDAL displays certain information on their website, the public API may not provide it
3. **Variability by track**: An album may have genres, but individual tracks may not
4. **Metadata quality**: Some independent or older tracks may have incomplete metadata

### API Response Example

For the track "Breathing (Techno)" in your screenshot:

```
Track ID: 336084531
- BPM: Not provided by TIDAL
- Label: Not provided by TIDAL
- Genres: Not provided by TIDAL
- Contributors: Maybe available but without specific role (producer/composer)
```

### How to Get More Data?

1. **Check TIDAL directly**: Sometimes data is visible on the TIDAL website but not via API
2. **Use other sources**: MusicBrainz, Discogs, etc. (not integrated in tidal-dl-ng)
3. **Manual editing**: After download, use a tag editor (Mp3tag, Kid3, etc.)

### Debugging

To see what the TIDAL API returns, you can check the console output when hovering over tracks. The application silently fetches BPM data in the background without cluttering the console.

**Technical Architecture**: BPM is loaded asynchronously:

1. Worker thread fetches raw JSON data from TIDAL API
2. `parse_track_and_album_extras()` extracts BPM from JSON
3. Qt Signal (`s_invoke_callback`) emits result to main thread
4. Stored callback is invoked in main thread (safe for UI updates)
5. `_handle_track_extras_ready` verifies it's the correct track
6. `_update_extras_ui` updates the BPM label in the interface

**Loading Indicator**: While BPM is being fetched, you'll see:

- `⏳ Loading...` - BPM data is being fetched from API (~100-500ms)
- `136` - BPM value successfully loaded
- `—` - BPM not available for this track

**Note**: If you previously hovered over a track, the BPM will display instantly on subsequent hovers thanks to the built-in cache system.

## Bitrate = N/A for LOSSLESS

The **LOSSLESS** codec (FLAC) uses lossless compression with a **variable bitrate (VBR)**. The exact bitrate depends on the audio content and changes constantly during playback. This is why it is displayed as `N/A` rather than a fixed number.

For codecs with fixed bitrate (AAC, etc.), you will see a number like "320 kbps".
