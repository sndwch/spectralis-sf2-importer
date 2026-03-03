"""CLI entry point for SF2 to SLI/SLC converter."""

import argparse
import sys
from pathlib import Path

from .core.sf2_reader import SF2Reader
from .core.converter import convert_to_sli, convert_to_slc


def progress_callback(message: str, percent: int):
    sys.stdout.write(f"\r[{percent:3d}%] {message:<60}")
    sys.stdout.flush()
    if percent >= 100:
        print()


def main():
    parser = argparse.ArgumentParser(
        prog="sf2_converter",
        description="Convert SF2 SoundFont files to Spectralis 2 SLI/SLC format",
    )
    parser.add_argument("input", nargs="?", help="Input SF2 file path (omit to launch GUI)")
    parser.add_argument(
        "-f", "--format",
        choices=["sli", "slc"],
        default="sli",
        help="Output format (default: sli)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output directory (SLI) or file path (SLC). Default: current directory",
    )
    parser.add_argument(
        "-i", "--instruments",
        type=int,
        nargs="+",
        help="Instrument indices to convert (default: all)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List instruments in the SF2 file and exit",
    )
    parser.add_argument(
        "--presets",
        action="store_true",
        help="List presets in the SF2 file and exit",
    )
    parser.add_argument(
        "-c", "--category",
        choices=["Other", "Kick", "Snare", "HiHat", "Tom", "Cymbal", "Percsn",
                 "DrumLp", "PercLp", "TonlLp", "FX-Lp", "Asynth", "Dsynth"],
        default=None,
        help="Spectralis category (default: Dsynth for SLI, Percsn for SLC)",
    )
    parser.add_argument(
        "--subcategory",
        default=None,
        help="Spectralis subcategory (e.g. Pad, Bass, Lead). Default: Other",
    )

    args = parser.parse_args()

    # Launch GUI if no input file specified
    if args.input is None:
        from .app import run
        run()
        return

    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # List mode
    if args.list or args.presets:
        with SF2Reader(input_path) as reader:
            if args.presets:
                print(f"Presets in {input_path.name}:")
                for p in reader.list_presets():
                    print(f"  Bank {p['bank']:03d} Program {p['program']:03d}: {p['name']}")
                    for inst_name in p["instruments"]:
                        print(f"    -> {inst_name}")
            if args.list:
                print(f"\nInstruments in {input_path.name}:")
                for info in reader.list_instruments():
                    print(f"  [{info['index']:3d}] {info['name']} ({info['zones']} zones)")
        return

    # Determine instrument indices
    if args.instruments is not None:
        indices = args.instruments
    else:
        with SF2Reader(input_path) as reader:
            indices = [info["index"] for info in reader.list_instruments()]

    if not indices:
        print("No instruments found in SF2 file.", file=sys.stderr)
        sys.exit(1)

    print(f"Converting {len(indices)} instrument(s) from {input_path.name}...")

    subcategory = args.subcategory or "Other"

    if args.format == "sli":
        category = args.category or "Dsynth"
        output_dir = Path(args.output) if args.output else Path.cwd()
        paths = convert_to_sli(input_path, indices, output_dir, progress_callback,
                               category=category, subcategory=subcategory)
        print(f"\nCreated {len(paths)} SLI file(s):")
        for p in paths:
            print(f"  {p}")
    else:
        category = args.category or "Percsn"
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = Path.cwd() / f"{input_path.stem}.SLC"
        path = convert_to_slc(input_path, indices, output_path, progress_callback,
                              category=category, subcategory=subcategory)
        print(f"\nCreated SLC file: {path}")


if __name__ == "__main__":
    main()
