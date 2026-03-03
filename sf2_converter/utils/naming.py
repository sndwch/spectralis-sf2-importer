"""Name truncation, ASCII sanitization, and Spectralis 2 category utilities."""

# =============================================================================
# Main category codes (second character of 2-char abbreviation)
# Confirmed from factory SLI/SLC files and SpectImp.exe UI screenshots.
# =============================================================================
CATEGORIES = {
    "Other": "@",
    "Kick": "K",
    "Snare": "S",
    "HiHat": "H",
    "Tom": "O",
    "Cymbal": "Y",
    "Percsn": "P",
    "DrumLp": "d",
    "PercLp": "p",
    "TonlLp": "t",
    "FX-Lp": "x",      # confirmed from "[x*] FX-Loop" in SpectImp
    "Asynth": "A",
    "Dsynth": "D",
}

# Display names for the UI (SpectImp shows these full names)
CATEGORY_DISPLAY_NAMES = {
    "Other": "Other",
    "Kick": "Kick",
    "Snare": "Snare",
    "HiHat": "HiHat",
    "Tom": "Tom",
    "Cymbal": "Cymbal",
    "Percsn": "Percussion",
    "DrumLp": "Drum-Loop",
    "PercLp": "Perc-Loop",
    "TonlLp": "Tonal-Loop",
    "FX-Lp": "FX-Loop",
    "Asynth": "A-Synth",
    "Dsynth": "D-Synth",
}

# Reverse lookup: code -> category key
CATEGORY_FROM_CODE = {v: k for k, v in CATEGORIES.items()}

# =============================================================================
# Subcategory definitions per category type
# Names confirmed from SpectImp.exe high-res screenshots.
# Codes confirmed from factory SLI/SLC files and new_slc2.SLC binary analysis.
# =============================================================================

# D-Synth subcategories (19 items)
# Confirmed codes from factory SLI files (D50, DX, FM, Puls, MKS series).
DSYNTH_SUBCATEGORIES = {
    "Synth-Bass": "S",
    "Bass": "B",
    "Sequencer": "Q",
    "Plug": "U",         # confirmed: [DU] in SpectImp + D50Fantasia on hardware
    "Attack": "A",
    "Release": "R",       # confirmed: [DR] in SpectImp
    "Lead": "L",
    "Pad": "P",
    "String": "G",
    "Brass": "F",         # confirmed: [DF] in SpectImp
    "Voice": "V",
    "Organ": "O",
    "Wind": "W",
    "Piano": "I",
    "Percussive": "C",
    "Ethnic": "E",
    "Texture": "T",
    "Effects": "X",
    "Other": "@",
}

# A-Synth subcategories (21 items)
# Same as D-Synth EXCEPT: no Piano, adds Multi, FB-Loop, Ext-In.
# Codes confirmed from new_slc2.SLC binary: [AM]=Multi, [AN]=FB-Loop, [AI]=Ext-In.
ASYNTH_SUBCATEGORIES = {
    "Synth-Bass": "S",
    "Bass": "B",
    "Sequencer": "Q",
    "Plug": "U",
    "Attack": "A",
    "Release": "R",
    "Lead": "L",
    "Pad": "P",
    "String": "G",
    "Brass": "F",
    "Voice": "V",
    "Organ": "O",
    "Wind": "W",
    "Percussive": "C",
    "Ethnic": "E",
    "Texture": "T",
    "Effects": "X",
    "Multi": "M",        # confirmed from new_slc2.SLC binary 'MA' = [AM]
    "FB-Loop": "N",      # confirmed from new_slc2.SLC binary 'NA' = [AN]
    "Ext-In": "I",       # confirmed from new_slc2.SLC binary 'IA' = [AI]
    "Other": "@",
}

# Genre-based subcategories (18 items)
# Shared by: Kick, Snare, HiHat, Tom, Drum-Loop, Perc-Loop, Tonal-Loop
# Codes confirmed from factory SLC files (TR909, TR808, Rock, Nord, MF_ series).
GENRE_SUBCATEGORIES = {
    "TR-alike": "T",     # confirmed from "[KT] TR-alike Kick" etc.
    "Big Beat": "B",     # confirmed: [KB] in SpectImp
    "HipHop": "H",       # confirmed: [KH] from user/SpectImp
    "Electro": "E",
    "Acid": "A",          # confirmed: [KA] in SpectImp
    "Techno": "C",        # confirmed: [KC] in SpectImp
    "House": "U",         # confirmed: [KU] from user/SpectImp
    "Funk": "F",          # confirmed: [KF] in SpectImp
    "Disco": "D",         # confirmed: [KD] from user/SpectImp
    "Pop": "P",
    "80s": "8",
    "Natural": "N",
    "Rock": "R",
    "Jazz": "J",          # confirmed: [KJ] in SpectImp
    "Oldie": "O",         # confirmed: [KO] in SpectImp
    "World": "W",         # confirmed: [KW] in SpectImp
    "Effects": "X",
    "Other": "@",
}

# Percussion subcategories (20 items) - unique instrument-based list
# All codes confirmed from new_slc2.SLC binary and SpectImp screenshots.
PERCUSSION_SUBCATEGORIES = {
    "Bell": "L",         # confirmed: 'LP' = [PL]
    "Block": "K",        # confirmed: 'KP' = [PK]
    "Bongo": "B",        # confirmed: 'BP' = [PB]
    "Chime": "J",        # confirmed: 'JP' = [PJ]
    "Clap": "C",         # confirmed: 'CP' = [PC]
    "Clave": "V",        # confirmed: 'VP' = [PV]
    "Conga": "O",        # confirmed: 'OP' = [PO]
    "Cuica": "I",        # confirmed: 'IP' = [PI]
    "Effects": "X",      # confirmed: 'XP' = [PX]
    "Ethnic": "E",       # confirmed: 'EP' = [PE]
    "Guiro": "G",        # confirmed: 'GP' = [PG]
    "Human": "H",        # from screenshot [PH] (instrument merged in SLC)
    "Industry": "Y",     # confirmed: 'YP' = [PY]
    "Marimba": "M",      # confirmed: 'MP' = [PM]
    "Scratch": "R",      # from screenshot [PR] (instrument merged in SLC)
    "Shaker": "S",       # from screenshot [PS] (instrument merged in SLC)
    "Timbale": "T",      # confirmed: 'TP' = [PT]
    "Triangle": "N",     # from screenshot [PN] (instrument merged in SLC)
    "Whistle": "W",      # from screenshot [PW] (instrument merged in SLC)
    "Other": "@",        # confirmed: [P@]
}

# Cymbal subcategories (9 items) - unique list
# Codes confirmed from new_slc2.SLC binary and SpectImp screenshots.
CYMBAL_SUBCATEGORIES = {
    "China": "H",        # confirmed: 'HY' = [YH]
    "Ride": "R",         # from screenshot [YR] (instrument merged in SLC)
    "Gong": "G",         # confirmed: 'GY' = [YG]
    "Ethnic": "E",       # confirmed: 'EY' = [YE]
    "Crash": "C",        # confirmed: 'CY' = [YC]
    "Splash": "S",       # from screenshot [YS] (instrument merged in SLC)
    "March": "M",        # confirmed: 'MY' = [YM]
    "Effects": "X",      # confirmed: 'XY' = [YX]
    "Other": "@",        # from screenshot [Y@]
}

# Categories with NO subcategories (no ">" arrow in SpectImp menu)
NO_SUBCATEGORY_CATEGORIES = {"Other", "FX-Lp"}

# Mapping: category key -> its subcategory dict (None = no subcategories)
SUBCATEGORIES_FOR_CATEGORY = {
    "Other": None,
    "Kick": GENRE_SUBCATEGORIES,
    "Snare": GENRE_SUBCATEGORIES,
    "HiHat": GENRE_SUBCATEGORIES,
    "Tom": GENRE_SUBCATEGORIES,
    "Cymbal": CYMBAL_SUBCATEGORIES,
    "Percsn": PERCUSSION_SUBCATEGORIES,
    "DrumLp": GENRE_SUBCATEGORIES,
    "PercLp": GENRE_SUBCATEGORIES,
    "TonlLp": GENRE_SUBCATEGORIES,
    "FX-Lp": None,
    "Asynth": ASYNTH_SUBCATEGORIES,
    "Dsynth": DSYNTH_SUBCATEGORIES,
}

# Default category for each output format
DEFAULT_SLI_CATEGORY = "Dsynth"
DEFAULT_SLC_CATEGORY = "Percsn"

# =============================================================================
# Legacy aliases (kept for any old references, map to the new dicts)
# =============================================================================
SYNTH_SUBCATEGORIES = DSYNTH_SUBCATEGORIES
DRUM_SUBCATEGORIES = GENRE_SUBCATEGORIES

# =============================================================================
# Auto-categorization keywords
# =============================================================================

# Keywords for guessing main category from instrument/sample name
_CATEGORY_KEYWORDS = {
    "Kick": ["kick", "bass drum", "bassdrum", "bd ", "bd_", "bd1", "bd2", "bd3"],
    "Snare": ["snare", "snr", "rimshot", "rim shot", "sidestick"],
    "HiHat": ["hihat", "hi-hat", "hi hat", "hh ", "hh_", "clhh", "ophh",
              "closed hat", "open hat", "pedal hat"],
    "Tom": ["tom ", "tom_", "tom1", "tom2", "tom3", "toms", "tomhi", "tomlo",
            "bongo", "conga", "timbale", "surdo"],
    "Cymbal": ["cymbal", "crash", "ride", "splash", "china"],
    "Percsn": ["perc", "clap", "claves", "clave", "shaker", "tamb",
               "cowbell", "woodblock", "triangle", "castanet", "guiro",
               "maracas", "agogo", "cabasa", "cuica", "whistle",
               "scratch", "stick", "click", "bell"],
}


# =============================================================================
# Utility functions
# =============================================================================

def sanitize_ascii(name: str) -> str:
    """Replace non-printable/non-ASCII characters with underscores."""
    return "".join(c if 32 <= ord(c) < 127 else "_" for c in name)


def truncate_name(name: str, max_length: int) -> str:
    """Sanitize and truncate a name to fit within max_length bytes."""
    name = sanitize_ascii(name)
    return name[:max_length]


def make_abbreviation(name: str, category: str = "Percsn",
                      subcategory: str | None = None) -> str:
    """Generate a 2-character abbreviation for a Spectralis instrument.

    Format: [subcategory_code][category_code]

    The category code (char[1]) encodes the main Spectralis category.
    The subcategory code (char[0]) comes from the subcategory, or defaults
    to '@' if no subcategory is specified or the code is unknown.

    For categories with no subcategories (Other, FX-Lp), uses '*' as
    the subcategory byte (matching SpectImp's "[x*] FX-Loop" pattern).
    """
    cat_code = CATEGORIES.get(category, "@")

    # Categories with no subcategories use '*' as subcategory marker
    if category in NO_SUBCATEGORY_CATEGORIES:
        return "*" + cat_code

    # Look up subcategory code
    sub_code = "@"  # default
    if subcategory is not None:
        sub_dict = SUBCATEGORIES_FOR_CATEGORY.get(category)
        if sub_dict and subcategory in sub_dict:
            code = sub_dict[subcategory]
            if code is not None:
                sub_code = code

    return sub_code + cat_code


def get_subcategory_names(category: str) -> list[str]:
    """Return the list of subcategory names for a given category.

    Returns an empty list for categories with no subcategories.
    """
    sub_dict = SUBCATEGORIES_FOR_CATEGORY.get(category)
    if sub_dict is None:
        return []
    return list(sub_dict.keys())


def guess_category(name: str, fallback: str = "Dsynth") -> str:
    """Guess a Spectralis category from an instrument/sample name.

    Scans the name for keywords associated with each drum category.
    Returns the fallback category if no keywords match.
    """
    # Pad with space so keywords with trailing spaces also match at end of string
    lower = name.lower() + " "
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return category
    return fallback
