"""Orchestrates the SF2 to SLI/SLC conversion pipeline."""

from pathlib import Path
from typing import Callable, Optional

from .models import InstrumentData
from .sf2_reader import SF2Reader
from .sli_writer import write_sli, write_slc
from ..utils.naming import make_abbreviation, guess_category


ProgressCallback = Optional[Callable[[str, int], None]]


def convert_to_sli(
    sf2_path: str | Path,
    instrument_indices: list[int],
    output_dir: str | Path,
    progress: ProgressCallback = None,
    category: str = "Dsynth",
    auto_categorize: bool = False,
    category_map: dict[int, str] | None = None,
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

            # Determine category for this instrument
            if auto_categorize:
                inst_category = category  # will be refined after extraction
            elif category_map and idx in category_map:
                inst_category = category_map[idx]
            else:
                inst_category = category

            instrument = reader.extract_instrument(idx, inst_category)

            if auto_categorize:
                inst_category = guess_category(instrument.name, fallback=category)
                instrument.abbreviation = make_abbreviation(
                    instrument.name, inst_category
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
    auto_categorize: bool = False,
    category_map: dict[int, str] | None = None,
) -> Path:
    """Convert selected SF2 instruments to a single SLC file.

    Each SF2 instrument becomes one SiIg chunk in the collection,
    preserving its original key zones intact.

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

            # Determine category for this instrument
            if auto_categorize:
                inst_category = category
            elif category_map and idx in category_map:
                inst_category = category_map[idx]
            else:
                inst_category = category

            instrument = reader.extract_instrument(idx, inst_category)

            if auto_categorize:
                inst_category = guess_category(instrument.name, fallback=category)
                instrument.abbreviation = make_abbreviation(
                    instrument.name, inst_category
                )

            slc_instruments.append(instrument)

    if progress:
        progress("Writing SLC file...", 90)

    write_slc(slc_instruments, output_path)

    if progress:
        progress("Done!", 100)

    return output_path
