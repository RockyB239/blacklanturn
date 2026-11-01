"""Local PNG decisions preserve bright logos and reject invisible dark marks."""
import struct
import sys
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'addon'))
try:
    from logo_readability import png_readable
except ModuleNotFoundError:
    png_readable = None


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)


def png(width=2, height=2, rows=None, color=6, depth=8, interlace=0, compressed=None, extra=b''):
    header = struct.pack('>IIBBBBB', width, height, depth, color, 0, 0, interlace)
    if rows is None:
        rows = b'\0' + bytes([255] * 8)
        rows *= 2
    data = zlib.compress(rows) if compressed is None else compressed
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + extra + chunk(b'IDAT', data) + chunk(b'IEND', b'')


class LogoReadability(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(png_readable, 'Bounded cached-PNG readability analysis is missing')

    def test_black_and_nearly_black_marks_fall_back_to_text(self):
        for rgb in ((0, 0, 0), (24, 20, 18), (55, 55, 55)):
            with self.subTest(rgb=rgb):
                self.assertIs(png_readable(png(rows=(b'\0' + bytes((*rgb, 255)) * 2) * 2)), False)

    def test_white_and_bright_colorful_logos_are_preserved(self):
        for rgb in ((255, 255, 255), (255, 0, 0), (0, 0, 255), (0, 220, 80), (130, 130, 130)):
            with self.subTest(rgb=rgb):
                self.assertIs(png_readable(png(rows=(b'\0' + bytes((*rgb, 255)) * 2) * 2)), True)

    def test_hidden_rgb_in_transparent_padding_cannot_change_decision(self):
        dark = b'\0' + bytes((8, 8, 8, 255, 255, 255, 255, 0))
        light = b'\0' + bytes((240, 240, 240, 255, 0, 0, 0, 0))
        self.assertIs(png_readable(png(rows=dark * 2)), False)
        self.assertIs(png_readable(png(rows=light * 2)), True)
        self.assertIsNone(png_readable(png(rows=(b'\0' + bytes((255, 255, 255, 0)) * 2) * 2)))

    def test_faint_white_edge_does_not_outweigh_opaque_black_text(self):
        self.assertIs(png_readable(png(rows=(b'\0' + bytes((0, 0, 0, 255, 255, 255, 255, 20))) * 2)), False)

    def test_a_small_bright_glint_does_not_rescue_a_black_logo(self):
        row = b'\0' + bytes((0, 0, 0, 255)) * 19 + bytes((255, 255, 255, 255))
        self.assertIs(png_readable(png(width=20, height=1, rows=row)), False)

    def test_rgb_without_alpha_is_supported(self):
        self.assertIs(png_readable(png(color=2, rows=(b'\0' + b'\xff' * 6) * 2)), True)
        self.assertIs(png_readable(png(color=2, rows=(b'\0' + b'\0' * 6) * 2)), False)

    def test_all_png_filters_decode_bright_and_black_rows(self):
        # Hand-calculated filtered two-pixel rows; no encoder shares decoder logic.
        white = {
            0: b'\0' + b'\xff' * 8 + b'\0' + b'\xff' * 8,
            1: b'\1' + b'\xff' * 4 + b'\0' * 4 + b'\1' + b'\xff' * 4 + b'\0' * 4,
            2: b'\2' + b'\xff' * 8 + b'\2' + b'\0' * 8,
            3: b'\3' + b'\xff' * 4 + b'\x80' * 4 + b'\3' + b'\x80' * 4 + b'\0' * 4,
            4: b'\4' + b'\xff' * 4 + b'\0' * 4 + b'\4' + b'\0' * 8,
        }
        black = {
            0: b'\0\0\0\0\xff\0\0\0\xff' * 2,
            1: b'\1\0\0\0\xff\0\0\0\0' * 2,
            2: b'\2\0\0\0\xff\0\0\0\xff' + b'\2' + b'\0' * 8,
            3: b'\3\0\0\0\xff\0\0\0\x80' + b'\3\0\0\0\x80\0\0\0\0',
            4: b'\4\0\0\0\xff\0\0\0\0' + b'\4' + b'\0' * 8,
        }
        for filtering in range(5):
            with self.subTest(filtering=filtering):
                self.assertIs(png_readable(png(rows=white[filtering])), True)
                self.assertIs(png_readable(png(rows=black[filtering])), False)

    def test_filters_reconstruct_nonuniform_pixels_before_classifying(self):
        # Known greyscale RGB pixels: bright [[10,110],[110,130]] has mean90;
        # dark [[200,0],[0,0]] has mean50. Encoded row values are hand-derived.
        bright = {0: ((10,110),(110,130)), 1: ((10,100),(110,20)),
                  2: ((10,110),(100,20)), 3: ((10,105),(105,20)),
                  4: ((10,100),(100,20))}
        dark = {0: ((200,0),(0,0)), 1: ((200,56),(0,0)),
                2: ((200,0),(56,0)), 3: ((200,156),(156,0)),
                4: ((200,56),(56,0))}
        for filtering in range(5):
            for encoded, expected in ((bright, True), (dark, False)):
                rows = b''.join(bytes((filtering,)) + bytes((a,))*3 + bytes((b,))*3
                                for a, b in encoded[filtering])
                with self.subTest(filtering=filtering, expected=expected):
                    self.assertIs(png_readable(png(color=2, rows=rows)), expected)

    def test_ancillary_chunks_are_bounded_even_when_each_one_is_small(self):
        text = chunk(b'tEXt', b'Comment\0cached logo')
        self.assertIs(png_readable(png(extra=text)), True)
        self.assertIsNone(png_readable(png(extra=text * 513)))

    def test_corrupt_and_truncated_files_are_unknown(self):
        valid = png()
        broken_crc = bytearray(valid)
        broken_crc[-1] ^= 1
        for raw in (None, '', b'', b'JPEG', valid[:32], valid[:-1], bytes(broken_crc), valid + b'junk', png(rows=b'\5' + b'\xff' * 8 + b'\0' + b'\xff' * 8), png(compressed=b'broken')):
            with self.subTest(raw_type=type(raw).__name__, size=len(raw) if raw is not None else None):
                self.assertIsNone(png_readable(raw))

    def test_unsupported_encodings_and_transparent_rgb_are_unknown(self):
        for raw in (png(color=3), png(color=0), png(depth=16), png(interlace=1), png(extra=chunk(b'tRNS', b'\0' * 6)), png(extra=chunk(b'acTL', b'\0' * 8))):
            self.assertIsNone(png_readable(raw))

    def test_missing_reordered_or_unknown_critical_chunks_are_unknown(self):
        valid = png()
        ihdr = valid[8:33]
        for raw in (valid[:33] + chunk(b'IEND', b''), valid[:8] + chunk(b'IDAT', zlib.compress(b'')) + valid[8:], png(extra=chunk(b'BOOM', b'')), valid[:33] + ihdr + valid[33:]):
            self.assertIsNone(png_readable(raw))

    def test_valid_png_may_split_compressed_data_across_idat_chunks(self):
        valid = png()
        data = zlib.compress((b'\0' + b'\xff' * 8) * 2)
        split = valid[:33] + chunk(b'IDAT', data[:3]) + chunk(b'IDAT', data[3:]) + chunk(b'IEND', b'')
        self.assertIs(png_readable(split), True)

    def test_large_input_dimensions_and_declared_chunks_are_unknown(self):
        for raw in (b'\x89PNG\r\n\x1a\n' + b'\0' * (2 * 1024 * 1024), png(width=0), png(width=1000000), png(width=2048, height=2048), png()[:33] + struct.pack('>I', 0x7fffffff) + b'IDAT'):
            self.assertIsNone(png_readable(raw))

    def test_decompression_bomb_and_inexact_streams_are_unknown(self):
        bomb = zlib.compress(b'\0' * (8 * 1024 * 1024))
        for compressed in (bomb, zlib.compress(b'\0'), zlib.compress(b'\0' * 18)[:-1], zlib.compress(b'\0' * 18) + b'junk'):
            self.assertIsNone(png_readable(png(compressed=compressed)))


if __name__ == '__main__':
    unittest.main()
