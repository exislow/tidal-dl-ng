#!/usr/bin/env python3
"""Test script to verify artist separator configuration saves and loads correctly."""

import json
import logging

logging.basicConfig(level=logging.DEBUG)


# Test if configuration saves and reloads correctly
def test_save_load():
    """Test that artist separator configuration persists."""
    print("\n" + "=" * 60)
    print("Testing Artist Separator Save/Load")
    print("=" * 60 + "\n")

    from tidal_dl_ng.config import Settings
    from tidal_dl_ng.constants import ArtistSeparator

    # Create a settings instance
    print("1. Creating Settings instance...")
    settings = Settings()

    # Display current configuration
    print("\n2. Current configuration:")
    print(f"   metadata_artist_separator: {settings.data.metadata_artist_separator}")
    print(f"   metadata_artist_space_before: {settings.data.metadata_artist_space_before}")
    print(f"   metadata_artist_space_after: {settings.data.metadata_artist_space_after}")
    print(f"   Resulting delimiter: '{settings.get_metadata_artist_delimiter()}'")

    # Modify configuration
    print("\n3. Modifying configuration to Jellyfin style ( ; )...")
    settings.data.metadata_artist_separator = ArtistSeparator.SEMICOLON
    settings.data.metadata_artist_space_before = True
    settings.data.metadata_artist_space_after = True

    print(f"   New delimiter: '{settings.get_metadata_artist_delimiter()}'")

    # Save
    print("\n4. Saving configuration...")
    settings.save()
    print(f"   Saved to: {settings.file_path}")

    # Verify file content
    print("\n5. Verifying saved file content...")
    with open(settings.file_path, encoding="utf-8") as f:
        saved_data = json.load(f)

    print(f"   metadata_artist_separator: {saved_data.get('metadata_artist_separator')}")
    print(f"   metadata_artist_space_before: {saved_data.get('metadata_artist_space_before')}")
    print(f"   metadata_artist_space_after: {saved_data.get('metadata_artist_space_after')}")

    # Create new Settings instance (reload from file)
    print("\n6. Creating new Settings instance (reload)...")
    settings2 = Settings()

    print(f"   metadata_artist_separator: {settings2.data.metadata_artist_separator}")
    print(f"   metadata_artist_space_before: {settings2.data.metadata_artist_space_before}")
    print(f"   metadata_artist_space_after: {settings2.data.metadata_artist_space_after}")
    print(f"   Resulting delimiter: '{settings2.get_metadata_artist_delimiter()}'")

    # Verify
    print("\n7. Verification:")
    if settings2.data.metadata_artist_separator == ArtistSeparator.SEMICOLON:
        print("   ✅ Separator saved correctly")
    else:
        print(f"   ❌ Separator NOT saved (got {settings2.data.metadata_artist_separator})")

    if settings2.data.metadata_artist_space_before is True:
        print("   ✅ Space before saved correctly")
    else:
        print("   ❌ Space before NOT saved")

    if settings2.data.metadata_artist_space_after is True:
        print("   ✅ Space after saved correctly")
    else:
        print("   ❌ Space after NOT saved")

    if settings2.get_metadata_artist_delimiter() == " ; ":
        print("   ✅ Final delimiter correct: ' ; '")
    else:
        print(f"   ❌ Final delimiter incorrect: '{settings2.get_metadata_artist_delimiter()}'")

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    test_save_load()
