"""Binary SLI/SLC file writer for Spectralis 2 format."""

import math
import struct
from pathlib import Path

from .models import InstrumentData, ZoneMapping
from ..utils.naming import truncate_name


# Magic bytes and constants
SIFI_MAGIC = b"SiFi"
SIIG_MAGIC = b"SiIg"
SIDP_MAGIC = b"SiDp"
FORMAT_VERSION = 0x0100
SIFI_FLAGS = 0x0010
SIDP_SIZE = 12

# Section sizes
INSTRUMENT_HEADER_SIZE = 40
ZONE_ENTRY_SIZE = 76
SAMPLE_DESCRIPTOR_SIZE = 48

# Offsets
SIFI_HEADER_SIZE = 16
SIIG_HEADER_SIZE = 12
OFFSET_TABLE_SIZE = 16  # 4 entries × 4 bytes each
SECTION_0_OFFSET = SIIG_HEADER_SIZE + OFFSET_TABLE_SIZE  # 0x1C = 28


def _timecents_to_ms(tc: int) -> int:
    """Convert SF2 timecents to milliseconds (LE16-safe)."""
    if tc <= -32768:
        return 0
    return max(0, min(65535, int(1000.0 * math.pow(2.0, tc / 1200.0))))


def _build_sidp() -> bytes:
    """Build the SiDp footer chunk (12 bytes)."""
    return struct.pack("<4sII", SIDP_MAGIC, SIDP_SIZE, FORMAT_VERSION)


def _build_instrument_header(instrument: InstrumentData) -> bytes:
    """Build Section 0: instrument header (40 bytes)."""
    name = truncate_name(instrument.name, 32)
    name_bytes = name.encode("ascii", errors="replace").ljust(32, b"\x00")

    abbrev = instrument.abbreviation[:2].encode("ascii", errors="replace").ljust(2, b"\x00")

    zone_count = len(instrument.zones)

    return struct.pack(
        "<32s2s2xHH",
        name_bytes,
        abbrev,
        0,  # unknown, always 0
        zone_count,
    )


def _build_zone_entry(zone: ZoneMapping, zone_index: int) -> bytes:
    """Build one Section 1 zone entry (76 bytes).

    Synth parameter bytes (offsets relative to byte 4 of entry, i.e.
    entry[N+4] = synth byte N):

        byte 16 (entry[20]): coarseTune (signed byte, duplicate at byte 22)
        byte 17 (entry[21]): fineTune (signed byte, cents)
        byte 18 (entry[22]): sampleModes (loop flags)
        byte 19 (entry[23]): overridingRootKey (0 if not set)
        byte 20 (entry[24]): scaleTuning (only when non-default)
        byte 22 (entry[26]): coarseTune (signed byte, semitones)
        byte 23 (entry[27]): fineTune duplicate (for L channel in stereo)
        byte 56 (entry[60]): pan position (effective_pan // 5, unsigned byte)
        byte 67 (entry[71]): attenuation ((centibels // 10 - 5) & 0xFF)

    Mappings reverse-engineered from SpectImp.exe output analysis.
    """
    entry = bytearray(ZONE_ENTRY_SIZE)
    entry[0] = zone.key_range_low
    entry[1] = zone.key_range_high
    entry[2] = zone.vel_range_low
    entry[3] = zone.vel_range_high

    # Synth byte 17: fineTune (signed byte)
    entry[21] = zone.fine_tune & 0xFF

    # Synth byte 18: sampleModes
    entry[22] = zone.sample_modes & 0xFF

    # Synth byte 19: root note (0 if overridingRootKey not explicitly set)
    if zone.root_key_set:
        entry[23] = zone.sample.root_note & 0x7F
    else:
        entry[23] = 0

    # Synth byte 20: scaleTuning (only when explicitly set and non-default)
    if zone.scale_tuning is not None and zone.scale_tuning != 100:
        entry[24] = zone.scale_tuning & 0xFF

    # Synth byte 16: coarseTune (signed byte) — SpectImp writes coarseTune here too
    entry[20] = zone.coarse_tune & 0xFF

    # Synth byte 22: coarseTune (signed byte)
    entry[26] = zone.coarse_tune & 0xFF

    # Synth byte 23: fineTune (same as byte 17 for mono; for stereo pairs,
    # SpectImp stores R fine tune in byte 17 and L in byte 23.  Since we
    # extract each channel as a separate mono zone, they are the same.)
    entry[27] = zone.fine_tune & 0xFF

    # Synth byte 56: pan position (Spectralis uses inverted polarity vs SF2)
    if zone.pan != 0:
        entry[60] = (-zone.pan // 5) & 0xFF

    # Synth bytes 28-29 (entry[32-33]): decayModEnv as LE16 milliseconds
    if zone.decay_mod_env_tc != 0:
        ms = _timecents_to_ms(zone.decay_mod_env_tc)
        struct.pack_into("<H", entry, 32, ms)

    # Synth byte 67: attenuation
    if zone.attenuation_cb > 0:
        entry[71] = (zone.attenuation_cb // 10 - 5) & 0xFF

    struct.pack_into("<I", entry, 72, zone_index)
    return bytes(entry)


def _build_sample_descriptor(zone: ZoneMapping, cumulative_end: int) -> bytes:
    """Build one Section 2 sample descriptor (48 bytes).

    Root note in descriptor is always 60 (placeholder), matching SpectImp.
    The actual root note is stored in synth[19] of the zone entry.
    """
    sample = zone.sample
    name = truncate_name(sample.name, 28)
    name_bytes = name.encode("ascii", errors="replace").ljust(28, b"\x00")

    return struct.pack(
        "<28sIII x B B B I",
        name_bytes,
        cumulative_end,
        sample.loop_start,
        sample.loop_end,
        # 1 byte padding (always 0) via 'x'
        60,  # root note placeholder (actual root in zone synth[19])
        sample.channels,
        0x10,  # bit depth indicator (16-bit)
        sample.sample_rate,
    )


def _build_siig_chunk(instrument: InstrumentData) -> bytes:
    """Build a complete SiIg chunk for one instrument.

    Returns the full chunk including SiIg header and SiDp footer.
    """
    zones = sorted(instrument.zones, key=lambda z: z.key_range_low)
    zone_count = len(zones)

    # Calculate section offsets (relative to SiIg chunk start, i.e. start of SiIg magic)
    section_0_offset = SECTION_0_OFFSET  # 0x1C
    section_1_offset = section_0_offset + INSTRUMENT_HEADER_SIZE  # 0x44
    section_2_offset = section_1_offset + (ZONE_ENTRY_SIZE * zone_count)
    section_3_offset = section_2_offset + (SAMPLE_DESCRIPTOR_SIZE * zone_count)

    # Build offset table: 4 entries of (offset_u16, count_u16)
    offset_table = struct.pack(
        "<4H4H",
        section_0_offset, 1,  # Entry 0: instrument header, count=1
        section_1_offset, zone_count,  # Entry 1: zone mappings
        section_2_offset, zone_count,  # Entry 2: sample descriptors
        section_3_offset, 0,  # Entry 3: audio data, count=0
    )

    # Build Section 0: instrument header
    inst_header = _build_instrument_header(instrument)

    # Build Section 1: zone entries
    zone_entries = b""
    for i, zone in enumerate(zones):
        zone_entries += _build_zone_entry(zone, i)

    # Build Section 2: sample descriptors + collect audio
    descriptors = b""
    audio_data = b""
    cumulative_end = 0
    for zone in zones:
        audio_data += zone.sample.pcm_data
        cumulative_end += len(zone.sample.pcm_data)
        descriptors += _build_sample_descriptor(zone, cumulative_end)

    # Add zero padding after audio (64 bytes × channels of the last zone)
    if zones:
        last_channels = zones[-1].sample.channels
        padding_size = 64 * last_channels
        audio_data += b"\x00" * padding_size

    # Build SiDp footer
    sidp = _build_sidp()

    # Assemble everything after the SiIg header
    chunk_data = offset_table + inst_header + zone_entries + descriptors + audio_data + sidp

    # SiIg header: data_size = everything after the 12-byte header
    data_size = len(chunk_data)
    siig_header = struct.pack("<4sII", SIIG_MAGIC, data_size, FORMAT_VERSION)

    return siig_header + chunk_data


def _build_sifi_header(total_file_size: int, instrument_count: int) -> bytes:
    """Build the SiFi file header (16 bytes)."""
    return struct.pack(
        "<4sIHHHH",
        SIFI_MAGIC,
        total_file_size,
        FORMAT_VERSION,
        0,  # reserved
        instrument_count,
        SIFI_FLAGS,
    )


def write_sli(instrument: InstrumentData, output_path: str | Path) -> None:
    """Write a single instrument as an SLI file."""
    output_path = Path(output_path)
    siig_chunk = _build_siig_chunk(instrument)
    total_size = SIFI_HEADER_SIZE + len(siig_chunk)
    sifi_header = _build_sifi_header(total_size, 1)
    file_data = sifi_header + siig_chunk

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(file_data)
    _validate_file(file_data)


def write_slc(instruments: list[InstrumentData], output_path: str | Path) -> None:
    """Write multiple instruments as an SLC file.

    Each instrument becomes one SiIg chunk and may have one or more zones.
    """
    output_path = Path(output_path)
    siig_chunks = b""
    for inst in instruments:
        siig_chunks += _build_siig_chunk(inst)

    total_size = SIFI_HEADER_SIZE + len(siig_chunks)
    sifi_header = _build_sifi_header(total_size, len(instruments))
    file_data = sifi_header + siig_chunks

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(file_data)
    _validate_file(file_data)


def _validate_file(data: bytes) -> None:
    """Validate basic structural integrity of written file data."""
    # Check SiFi header
    assert data[:4] == SIFI_MAGIC, "Missing SiFi magic"
    file_size = struct.unpack_from("<I", data, 4)[0]
    assert file_size == len(data), f"File size mismatch: header says {file_size}, actual {len(data)}"

    inst_count = struct.unpack_from("<H", data, 12)[0]

    # Walk SiIg chunks
    offset = SIFI_HEADER_SIZE
    for i in range(inst_count):
        assert data[offset:offset + 4] == SIIG_MAGIC, f"Missing SiIg magic at chunk {i}"
        data_size = struct.unpack_from("<I", data, offset + 4)[0]
        chunk_end = offset + SIIG_HEADER_SIZE + data_size
        # Check SiDp footer at end of chunk
        sidp_offset = chunk_end - SIDP_SIZE
        assert data[sidp_offset:sidp_offset + 4] == SIDP_MAGIC, f"Missing SiDp at chunk {i}"
        offset = chunk_end
