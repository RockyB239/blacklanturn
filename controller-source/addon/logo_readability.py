"""Bounded, local-only readability check for cached logos on the dark hero.

Call once in background work and cache the result. False means use the title
text; True preserves the logo; None leaves an unsupported/invalid file alone.
No I/O, image changes, Kodi APIs, or third-party/native imaging dependencies.
"""
import struct
import zlib

MAX_PNG_BYTES = 2 * 1024 * 1024
MAX_DIMENSION = 2048
MAX_PIXELS = 1024 * 1024
MAX_CHUNKS = 512


def _png_data(raw):
    """Validate a small noninterlaced 8-bit RGB/RGBA PNG and bound inflation."""
    if not isinstance(raw, (bytes, bytearray)) or not 45 <= len(raw) <= MAX_PNG_BYTES:
        return None
    if raw[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    position = 8
    header = None
    compressed = []
    data_ended = False
    for _ in range(MAX_CHUNKS):
        if position + 12 > len(raw):
            return None
        length = struct.unpack_from('>I', raw, position)[0]
        end = position + 12 + length
        if end > len(raw):
            return None
        kind = bytes(raw[position + 4:position + 8])
        payload = raw[position + 8:end - 4]
        checksum = zlib.crc32(kind)
        checksum = zlib.crc32(payload, checksum) & 0xffffffff
        if checksum != struct.unpack_from('>I', raw, end - 4)[0]:
            return None
        if header is None and kind != b'IHDR':
            return None
        if kind == b'IHDR':
            if header is not None or length != 13:
                return None
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            if not (0 < width <= MAX_DIMENSION and 0 < height <= MAX_DIMENSION):
                return None
            if width * height > MAX_PIXELS or depth != 8 or color not in (2, 6):
                return None
            if compression or filtering or interlace:
                return None
            header = (width, height, 3 if color == 2 else 4)
        elif kind == b'IDAT':
            if data_ended:
                return None
            compressed.append(payload)
        elif kind == b'IEND':
            if length or not compressed or end != len(raw):
                return None
            width, height, channels = header
            expected = (width * channels + 1) * height
            decoder = zlib.decompressobj()
            try:
                # Never allow even a valid small PNG to inflate past its rows.
                decoded = decoder.decompress(b''.join(compressed), expected + 1)
            except zlib.error:
                return None
            if len(decoded) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                return None
            return header, decoded
        elif kind in (b'tRNS', b'acTL', b'fcTL', b'fdAT'):
            # RGB color-key transparency and animation need different semantics.
            return None
        elif kind == b'PLTE':
            if compressed or not 0 < length <= 768 or length % 3:
                return None
        elif not (len(kind) == 4 and all(65 <= c <= 90 or 97 <= c <= 122 for c in kind) and kind[0] & 32):
            return None
        if compressed and kind != b'IDAT':
            data_ended = True
        position = end
    return None


def png_readable(raw):
    """Return bool or None for bounded cached PNG bytes; perform no file reads.

    Opacity weights visible pixels; transparent padding cannot turn a black
    logo white or dilute a white one. Combining luminance and peak channel
    retains saturated bright colored marks as well as neutral light logos.
    This is a conservative dark-logo heuristic, not a background-aware WCAG
    contrast measurement. Unsupported encodings and corruption are unknown.
    """
    parsed = _png_data(raw)
    if parsed is None:
        return None
    (width, height, channels), decoded = parsed
    row_bytes = width * channels
    previous = bytearray(row_bytes)
    position = 0
    alpha_sum = 0
    brightness_sum = 0
    for _ in range(height):
        filtering = decoded[position]
        row = bytearray(decoded[position + 1:position + 1 + row_bytes])
        position += row_bytes + 1
        if filtering > 4:
            return None
        if filtering:
            for i in range(row_bytes):
                left = row[i - channels] if i >= channels else 0
                above = previous[i]
                if filtering == 1:
                    predictor = left
                elif filtering == 2:
                    predictor = above
                elif filtering == 3:
                    predictor = (left + above) // 2
                else:
                    upper_left = previous[i - channels] if i >= channels else 0
                    estimate = left + above - upper_left
                    dl = abs(estimate - left)
                    da = abs(estimate - above)
                    du = abs(estimate - upper_left)
                    predictor = left if dl <= da and dl <= du else above if da <= du else upper_left
                row[i] = (row[i] + predictor) & 255
        for i in range(0, row_bytes, channels):
            alpha = row[i + 3] if channels == 4 else 255
            if alpha < 16:
                continue
            red, green, blue = row[i:i + 3]
            # Integer Rec.709 luma plus peak channel, both on a 0..255 scale.
            luminance = (54 * red + 183 * green + 19 * blue) // 256
            brightness_sum += alpha * (luminance + max(red, green, blue))
            alpha_sum += alpha
        previous = row
    if not alpha_sum:
        return None
    return brightness_sum >= alpha_sum * 160  # mean combined brightness >= 80
