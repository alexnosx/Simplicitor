#!/usr/bin/env python3
"""
Generate resources/icon.ico — a 32×32 solid Simplicitor-blue (#2563EB) icon.

No third-party dependencies. Run:  python resources/create_icon.py
"""
import struct
from pathlib import Path

# Simplicitor primary accent: #2563EB  →  R=37, G=99, B=235
_R, _G, _B, _A = 37, 99, 235, 255


def _make_ico(size: int) -> bytes:
    """Return raw bytes for a single solid-colour ICO image at `size` × `size`."""
    # BGRA pixel data (ICO uses BGRA order)
    pixels = bytes([_B, _G, _R, _A]) * size * size

    # BITMAPINFOHEADER (40 bytes) — height doubled in ICO format
    bmi = struct.pack(
        "<IIIHHIIIIII",
        40,        # biSize
        size,      # biWidth
        size * 2,  # biHeight (×2 = XOR + AND bitmaps stacked)
        1,         # biPlanes
        32,        # biBitCount (32-bit BGRA)
        0,         # biCompression (BI_RGB)
        0,         # biSizeImage
        0,         # biXPelsPerMeter
        0,         # biYPelsPerMeter
        0,         # biClrUsed
        0,         # biClrImportant
    )

    # AND mask: 1 bit/pixel, rows padded to DWORD boundary
    # For 32-bit images Windows ignores the AND mask if alpha=0xFF, but we
    # must include it. Row width in bits = size, padded to 32 bits.
    row_bytes = ((size + 31) // 32) * 4
    and_mask = b"\x00" * (row_bytes * size)

    return bmi + pixels + and_mask


def create_icon(output_path: Path) -> None:
    """Write a multi-size ICO (16×16, 32×32) to *output_path*."""
    sizes = [16, 32]
    images = [_make_ico(s) for s in sizes]

    # ICONDIR header: reserved=0, type=1 (ICO), count
    icon_dir = struct.pack("<HHH", 0, 1, len(sizes))

    # ICONDIRENTRY for each image; offset starts after ICONDIR + all entries
    entry_size = 16
    data_offset = 6 + entry_size * len(sizes)
    entries = b""
    for size, image in zip(sizes, images):
        w = h = size if size < 256 else 0  # 256 encoded as 0 in ICO spec
        entries += struct.pack(
            "<BBBBHHII",
            w, h,           # width, height
            0,              # colorCount (0 = no palette)
            0,              # reserved
            1,              # planes
            32,             # bitCount
            len(image),     # bytesInRes
            data_offset,    # imageOffset
        )
        data_offset += len(image)

    output_path.write_bytes(icon_dir + entries + b"".join(images))
    print(f"Icon written: {output_path}  ({output_path.stat().st_size} bytes)")


if __name__ == "__main__":
    out = Path(__file__).parent / "icon.ico"
    create_icon(out)
