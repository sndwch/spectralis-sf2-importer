"""Orchestrates the SF2 to SLI/SLC conversion pipeline."""

import logging
from pathlib import Path
from typing import Callable, Optional

from .models import InstrumentData
from .sf2_reader import SF2Reader
from .sli_writer import write_sli, write_slc
from ..utils.naming import make_abbreviation, guess_category


ProgressCallback = Optional[Callable[[str, int], None]]

# Factory SLI files max out at 44 zones. 128 (one per MIDI key) is a
# safe upper bound — the Spectralis 2 hardware won't handle more.
MAX_SLI_ZONES = 128


def convert_to_sli(
    sf2_path: str | Path,
    instrument_indices: list[int],
    output_dir: str | Path,
    progress: ProgressCallback = None,
    category: str = "Dsynth",
    subcategory: str = "Other",
    auto_categorize: bool = False,
    category_map: dict[int, str] | None = None,
    subcategory_map: dict[int, str] | None = None,
) -> list[Path]:
    """Convert selected SF2 instruments to individual SLI files.

    Each instrument becomes one SLI file (may have multiple zones/key splits).

    Args:
        category_map: Optional dict mapping instrument index -> category name.
                      Used when auto_categorize is False for per-instrument categories.

    Returns list of output file paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = []

    with SF2Reader(sf2_path) as reader:
        total = len(instrument_indices)
        for step, idx in enumerate(instrument_indices):
            if progress:
                progress(f"Extracting instrument {idx}...", int(step / total * 50))

            # Determine category and subcategory for this instrument
            if auto_categorize:
                inst_category = category  # will be refined after extraction
                inst_subcategory = subcategory
            elif category_map and idx in category_map:
                inst_category = category_map[idx]
                inst_subcategory = subcategory_map[idx] if subcategory_map and idx in subcategory_map else subcategory
            else:
                inst_category = category
                inst_subcategory = subcategory

            instrument = reader.extract_instrument(idx, inst_category, inst_subcategory)

            if auto_categorize:
                inst_category = guess_category(instrument.name, fallback=category)
                instrument.abbreviation = make_abbreviation(
                    instrument.name, inst_category, inst_subcategory
                )

            zone_count = len(instrument.zones)
            if zone_count > MAX_SLI_ZONES:
                logging.warning(
                    f"Instrument '{instrument.name}' has {zone_count} zones "
                    f"(max recommended: {MAX_SLI_ZONES}). "
                    f"The Spectralis 2 may not load this file."
                )

            # Generate filename from instrument name
            safe_name = "".join(
                c if c.isalnum() or c in " _-" else "_"
                for c in instrument.name
            ).strip()
            if not safe_name:
                safe_name = f"instrument_{idx}"
            output_path = output_dir / f"{safe_name}.SLI"

            if progress:
                progress(f"Writing {output_path.name}...", int((step + 0.5) / total * 50) + 50)

            write_sli(instrument, output_path)
            output_paths.append(output_path)

    if progress:
        progress("Done!", 100)

    return output_paths


def convert_to_slc(
    sf2_path: str | Path,
    instrument_indices: list[int],
    output_path: str | Path,
    progress: ProgressCallback = None,
    category: str = "Percsn",
    subcategory: str = "Other",
    auto_categorize: bool = False,
    category_map: dict[int, str] | None = None,
    subcategory_map: dict[int, str] | None = None,
) -> Path:
    """Convert selected SF2 instruments to a single SLC file.

    Each SF2 instrument becomes one instrument in the SLC collection,
    preserving its zones (key splits / velocity layers).  Single-zone
    instruments get their key and velocity ranges widened to 0-127 so
    they respond to all notes, matching the most common factory SLC
    layout.  Multi-zone instruments keep their original ranges intact.

    Args:
        category_map: Optional dict mapping instrument index -> category name.
                      Used when auto_categorize is False for per-instrument categories.

    Returns the output file path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    slc_instruments = []

    with SF2Reader(sf2_path) as reader:
        total = len(instrument_indices)
        for step, idx in enumerate(instrument_indices):
            if progress:
                progress(f"Extracting instrument {idx}...", int(step / total * 80))

            # Determine category and subcategory for this instrument
            if auto_categorize:
                inst_category = category
                inst_subcategory = subcategory
            elif category_map and idx in category_map:
                inst_category = category_map[idx]
                inst_subcategory = subcategory_map[idx] if subcategory_map and idx in subcategory_map else subcategory
            else:
                inst_category = category
                inst_subcategory = subcategory

            instrument = reader.extract_instrument(idx, inst_category, inst_subcategory)

            if auto_categorize:
                inst_category = guess_category(instrument.name, fallback=category)

            instrument.abbreviation = make_abbreviation(
                instrument.name, inst_category, inst_subcategory
            )

            # Single-zone instruments: widen to full 0-127 range so they
            # respond to all notes (standard SLC drum/sample behavior).
            # Multi-zone instruments: keep original key splits intact.
            if len(instrument.zones) == 1:
                zone = instrument.zones[0]
                zone.key_range_low = 0
                zone.key_range_high = 127
                zone.vel_range_low = 0
                zone.vel_range_high = 127

            slc_instruments.append(instrument)

    if progress:
        progress("Writing SLC file...", 90)

    write_slc(slc_instruments, output_path)

    if progress:
        progress("Done!", 100)

    return output_path
