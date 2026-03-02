"""Sample rate conversion using linear interpolation."""

import struct

TARGET_RATE = 44100


def resample(pcm_data: bytes, src_rate: int, channels: int,
             loop_start: int, loop_end: int) -> tuple[bytes, int, int]:
    """Resample 16-bit PCM data from src_rate to 44100 Hz.

    Args:
        pcm_data: Raw 16-bit signed LE PCM data
        src_rate: Source sample rate in Hz
        channels: 1 for mono, 2 for stereo
        loop_start: Loop start byte offset
        loop_end: Loop end byte offset

    Returns:
        Tuple of (resampled_pcm_data, new_loop_start, new_loop_end)
    """
    if src_rate == TARGET_RATE:
        return pcm_data, loop_start, loop_end

    bytes_per_frame = 2 * channels  # 16-bit = 2 bytes per sample per channel
    src_frame_count = len(pcm_data) // bytes_per_frame
    if src_frame_count == 0:
        return pcm_data, loop_start, loop_end

    ratio = TARGET_RATE / src_rate
    dst_frame_count = int(src_frame_count * ratio)

    # Decode source frames
    fmt = f"<{src_frame_count * channels}h"
    try:
        samples = list(struct.unpack(fmt, pcm_data[:src_frame_count * bytes_per_frame]))
    except struct.error:
        return pcm_data, loop_start, loop_end

    # Resample each channel with linear interpolation
    resampled_channels = []
    for ch in range(channels):
        # Extract this channel's samples
        ch_samples = samples[ch::channels]
        ch_resampled = []
        for i in range(dst_frame_count):
            src_pos = i / ratio
            idx = int(src_pos)
            frac = src_pos - idx
            if idx + 1 < len(ch_samples):
                val = ch_samples[idx] * (1.0 - frac) + ch_samples[idx + 1] * frac
            elif idx < len(ch_samples):
                val = ch_samples[idx]
            else:
                val = 0
            ch_resampled.append(max(-32768, min(32767, int(round(val)))))
        resampled_channels.append(ch_resampled)

    # Interleave channels back
    result = []
    for i in range(dst_frame_count):
        for ch in range(channels):
            result.append(resampled_channels[ch][i])

    resampled_data = struct.pack(f"<{len(result)}h", *result)

    # Scale loop points proportionally
    new_loop_start = int(loop_start * ratio) & ~(bytes_per_frame - 1)  # Align to frame
    new_loop_end = int(loop_end * ratio) & ~(bytes_per_frame - 1)

    return resampled_data, new_loop_start, new_loop_end
