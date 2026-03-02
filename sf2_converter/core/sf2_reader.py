"""SF2 SoundFont file reader using sf2utils."""

import struct
from pathlib import Path

from sf2utils.sf2parse import Sf2File
from sf2utils.generator import Sf2Gen

from .models import SampleData, ZoneMapping, InstrumentData
from ..utils.naming import truncate_name, make_abbreviation
from ..utils.audio import ensure_little_endian

# Extra frames to read beyond sample end (matches SpectImp behavior).
# SpectImp consistently reads 32 extra frames (64 bytes at 16-bit mono)
# beyond the declared sample end, providing interpolation guard frames.
EXTRA_FRAMES = 32


class SF2Reader:
    """Reads and parses SF2 SoundFont files."""

    def __init__(self, sf2_path: str | Path):
        self._path = Path(sf2_path)
        self._file = open(self._path, "rb")
        self._sf2 = Sf2File(self._file)

    def close(self):
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @property
    def bank_name(self) -> str:
        return self._sf2.info.bank_name or self._path.stem

    def list_presets(self) -> list[dict]:
        """List all presets with their bank/program numbers."""
        result = []
        for preset in self._sf2.presets:
            if preset.name == "EOP":
                continue
            result.append({
                "name": preset.name,
                "bank": preset.bank,
                "program": preset.preset,
                "instruments": [
                    bag.instrument.name
                    for bag in preset.bags
                    if bag.instrument is not None and bag.instrument.name != "EOI"
                ],
            })
        return result

    def list_instruments(self) -> list[dict]:
        """List all instruments with zone counts."""
        result = []
        for i, inst in enumerate(self._sf2.instruments):
            if inst.name == "EOI":
                continue
            zone_count = sum(1 for bag in inst.bags if bag.sample is not None)
            result.append({
                "index": i,
                "name": inst.name,
                "zones": zone_count,
            })
        return result

    def extract_instrument(self, instrument_index: int, category: str = "Percsn") -> InstrumentData:
        """Extract a single SF2 instrument as an InstrumentData object.

        All samples are output as mono (channels=1), matching SpectImp.exe
        behavior.  Stereo L/R pairs become separate mono zones with the same
        key/velocity range.  No interleaving is performed.

        SF2 generators are extracted and stored on ZoneMapping for synth params.
        """
        inst = self._sf2.instruments[instrument_index]
        if inst.name == "EOI":
            raise ValueError("Cannot extract sentinel instrument EOI")

        # Identify global zone (first bag with no sample reference)
        global_bag = None
        if inst.bags and inst.bags[0].sample is None:
            global_bag = inst.bags[0]

        # Extract global pan (used in effective pan calculation)
        global_pan = (self._get_gen_signed(global_bag, Sf2Gen.OPER_PAN) or 0) if global_bag else 0

        # Extract global sampleModes for dual-layer encoding
        global_sample_modes = 0
        if global_bag is not None:
            gsm = self._get_gen_unsigned(global_bag, Sf2Gen.OPER_SAMPLE_MODES)
            if gsm is not None:
                global_sample_modes = gsm & 0x3

        zones = []
        for bag in inst.bags:
            if bag.sample is None:
                continue  # Global zone (no sample)

            sample = bag.sample

            key_lo, key_hi = 0, 127
            if bag.key_range is not None:
                key_lo, key_hi = bag.key_range[0], bag.key_range[1]

            vel_lo, vel_hi = 0, 127
            if bag.velocity_range is not None:
                vel_lo, vel_hi = bag.velocity_range[0], bag.velocity_range[1]

            pcm_data = self._read_extended_sample(sample)
            zone = self._build_zone(
                bag, sample, pcm_data, 1,
                key_lo, key_hi, vel_lo, vel_hi, sample.name,
                global_pan, global_sample_modes, global_bag,
            )
            zones.append(zone)

        # Sort zones by key range, then by sample name for stable ordering
        zones.sort(key=lambda z: (z.key_range_low, z.sample.name))

        return InstrumentData(
            name=truncate_name(inst.name, 32),
            zones=zones,
            abbreviation=make_abbreviation(inst.name, category),
        )

    def _read_extended_sample(self, sample) -> bytes:
        """Read sample PCM data with extra guard frames (matching SpectImp).

        Reads 32 extra frames beyond the declared sample end to provide
        interpolation guard points, matching SpectImp.exe behavior.
        Falls back to raw_sample_data if direct read fails.
        """
        try:
            start = sample.start
            end = sample.end
            extra = EXTRA_FRAMES
            total_frames = (end - start) + extra

            # Read from SMPL chunk
            self._file.seek(sample.smpl_offset + start * 2)
            data = self._file.read(total_frames * 2)

            if len(data) < (end - start) * 2:
                # Couldn't even read the base data, fall back
                return ensure_little_endian(sample.raw_sample_data)

            return ensure_little_endian(data)
        except Exception:
            return ensure_little_endian(sample.raw_sample_data)

    def _build_zone(self, bag, sample, pcm_data, channels,
                    key_lo, key_hi, vel_lo, vel_hi, sample_name,
                    global_pan=0, global_sample_modes=0, global_bag=None):
        """Build a ZoneMapping from extracted bag/sample data."""
        # Root note: bag override > sample original_pitch > default 60
        root_note = 60
        root_key_set = False
        if bag.base_note is not None and 0 <= bag.base_note <= 127:
            root_note = bag.base_note
            root_key_set = True
        elif hasattr(sample, "original_pitch") and sample.original_pitch is not None:
            if 0 <= sample.original_pitch <= 127:
                root_note = sample.original_pitch

        # Fine tune (signed cents)
        fine_tune = self._get_gen_signed(bag, Sf2Gen.OPER_FINE_TUNE) or 0

        # Coarse tune (signed semitones)
        coarse_tune = self._get_gen_signed(bag, Sf2Gen.OPER_COARSE_TUNE) or 0

        # Pan: combine global + zone pan
        zone_pan = self._get_gen_signed(bag, Sf2Gen.OPER_PAN) or 0
        effective_pan = zone_pan + global_pan // 2

        # Sample modes (loop flags)
        zone_sm = self._get_gen_unsigned(bag, Sf2Gen.OPER_SAMPLE_MODES)
        sample_modes = (zone_sm & 0x3) if zone_sm is not None else 0
        # Encode global + zone sample modes like SpectImp: zone_sm | (global_sm << 3)
        if global_sample_modes > 0 and sample_modes > 0:
            sample_modes = sample_modes | (global_sample_modes << 3)

        # Scale tuning (None = default 100 cents/semitone)
        scale_tuning = self._get_gen_unsigned(bag, Sf2Gen.OPER_SCALE_TUNING)

        # Initial attenuation in centibels
        attenuation = self._get_gen_unsigned(bag, Sf2Gen.OPER_INITIAL_ATTENUATION) or 0

        # decayModEnv (signed timecents, with global fallback)
        decay_mod_env = self._get_gen_signed(bag, Sf2Gen.OPER_DECAY_MOD_ENV)
        if decay_mod_env is None and global_bag is not None:
            decay_mod_env = self._get_gen_signed(global_bag, Sf2Gen.OPER_DECAY_MOD_ENV)
        decay_mod_env = decay_mod_env or 0

        # Loop points (SF2 stores in sample frames, convert to byte offsets)
        bytes_per_frame = 2 * channels  # 16-bit per channel
        loop_start = 0
        loop_end = 0

        # Use cooked loop points if available (includes generator offsets)
        if hasattr(bag, "cooked_loop_start") and bag.cooked_loop_start is not None:
            loop_start = bag.cooked_loop_start * bytes_per_frame
            loop_end = bag.cooked_loop_end * bytes_per_frame
        elif sample.start_loop > 0 or sample.end_loop > 0:
            loop_start = sample.start_loop * bytes_per_frame
            loop_end = sample.end_loop * bytes_per_frame

        # Clamp loop points to actual data size
        data_len = len(pcm_data)
        loop_start = max(0, min(loop_start, data_len))
        loop_end = max(0, min(loop_end, data_len))
        if loop_end <= loop_start:
            loop_start = 0
            loop_end = data_len

        sample_data = SampleData(
            name=truncate_name(sample_name, 28),
            pcm_data=pcm_data,
            sample_rate=sample.sample_rate,
            channels=channels,
            bit_depth=16,
            root_note=root_note,
            loop_start=loop_start,
            loop_end=loop_end,
        )

        return ZoneMapping(
            key_range_low=key_lo,
            key_range_high=key_hi,
            vel_range_low=vel_lo,
            vel_range_high=vel_hi,
            sample=sample_data,
            fine_tune=fine_tune,
            coarse_tune=coarse_tune,
            pan=effective_pan,
            sample_modes=sample_modes,
            scale_tuning=scale_tuning,
            attenuation_cb=attenuation,
            decay_mod_env_tc=decay_mod_env,
            root_key_set=root_key_set,
        )

    @staticmethod
    def _get_gen_signed(bag, oper) -> int | None:
        """Get a signed 16-bit generator value, or None if not present."""
        if bag is None:
            return None
        if oper in bag.gens:
            return bag.gens[oper].short
        return None

    @staticmethod
    def _get_gen_unsigned(bag, oper) -> int | None:
        """Get an unsigned 16-bit generator value, or None if not present."""
        if bag is None:
            return None
        if oper in bag.gens:
            return bag.gens[oper].word
        return None

    def extract_all_instruments(self, category: str = "Percsn") -> list[InstrumentData]:
        """Extract all non-sentinel instruments."""
        instruments = []
        for i, inst in enumerate(self._sf2.instruments):
            if inst.name == "EOI":
                continue
            try:
                instruments.append(self.extract_instrument(i, category))
            except Exception as e:
                print(f"Warning: skipping instrument '{inst.name}': {e}")
        return instruments
