"""Audio utility functions for PCM data manipulation."""

import struct
import sys


def ensure_little_endian(pcm_data: bytes, bit_depth: int = 16) -> bytes:
    """Ensure PCM data is in little-endian byte order.

    On big-endian systems, swaps bytes. On little-endian (most modern systems),
    returns data unchanged.
    """
    if sys.byteorder == "big" and bit_depth == 16:
        # Swap bytes for each 16-bit sample
        data = bytearray(pcm_data)
        for i in range(0, len(data) - 1, 2):
            data[i], data[i + 1] = data[i + 1], data[i]
        return bytes(data)
    return pcm_data


def interleave_stereo(left: bytes, right: bytes) -> bytes:
    """Interleave left and right 16-bit PCM channels into LRLRLR format."""
    if len(left) != len(right):
        # Pad shorter channel to match longer
        max_len = max(len(left), len(right))
        left = left.ljust(max_len, b"\x00")
        right = right.ljust(max_len, b"\x00")

    sample_count = len(left) // 2
    result = bytearray(sample_count * 4)  # 2 bytes per sample, 2 channels

    for i in range(sample_count):
        offset_in = i * 2
        offset_out = i * 4
        result[offset_out:offset_out + 2] = left[offset_in:offset_in + 2]
        result[offset_out + 2:offset_out + 4] = right[offset_in:offset_in + 2]

    return bytes(result)


def mono_to_stereo(pcm_data: bytes) -> bytes:
    """Duplicate mono 16-bit PCM to stereo (LRLR interleaved)."""
    return interleave_stereo(pcm_data, pcm_data)
