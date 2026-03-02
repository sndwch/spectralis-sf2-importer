"""Data models for SF2 to SLI/SLC conversion."""

from dataclasses import dataclass, field


@dataclass
class SampleData:
    """Represents a single audio sample."""
    name: str
    pcm_data: bytes  # Raw 16-bit signed LE PCM
    sample_rate: int  # Hz (target: 44100)
    channels: int  # 1=mono, 2=stereo
    bit_depth: int  # Always 16 for Spectralis
    root_note: int  # MIDI note number (60=C4)
    loop_start: int  # Byte offset from sample start
    loop_end: int  # Byte offset from sample start


@dataclass
class ZoneMapping:
    """Maps a key/velocity range to a sample.

    Synth parameter fields are extracted from SF2 generators and written
    to the 68-byte synth params block in each zone entry.
    """
    key_range_low: int  # MIDI note 0-127
    key_range_high: int  # MIDI note 0-127
    vel_range_low: int  # 0-127
    vel_range_high: int  # 0-127
    sample: SampleData
    # SF2 generator-derived synth parameters
    fine_tune: int = 0          # SF2 fineTune in cents (signed)
    coarse_tune: int = 0        # SF2 coarseTune in semitones (signed)
    pan: int = 0                # Effective pan (-500 to +500, from SF2 pan generator)
    sample_modes: int = 0       # SF2 sampleModes (0=no loop, 1=loop, 3=loop+release)
    scale_tuning: int | None = None  # SF2 scaleTuning (None = default 100)
    attenuation_cb: int = 0     # SF2 initialAttenuation in centibels
    decay_mod_env_tc: int = 0   # SF2 decayModEnv in timecents (signed)
    root_key_set: bool = True   # Whether overridingRootKey was explicitly set


@dataclass
class InstrumentData:
    """A complete instrument with one or more zones."""
    name: str
    zones: list[ZoneMapping] = field(default_factory=list)
    abbreviation: str = "SF"  # 2-char abbreviation for Section 0
