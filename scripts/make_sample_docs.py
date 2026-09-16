"""Generate 3 synthetic English land-record documents + ground truth.

All content is fictitious and labeled FOR TESTING ONLY (05 section 11:
prefer synthetic examples). Same 13 text lines in every variant so the
benchmark measures degradation, not content differences.

Variants:
  doc01_clean.pdf/png  EASY   clean printout (also exercises the PDF path)
  doc02_noisy.png      MEDIUM print + noise + 2.5-degree skew
  doc03_faded.png      HARD   washed-out low-contrast print

Usage (from repo root, any python with pillow+numpy):
    python scripts\\make_sample_docs.py

Writes dataset/raw_documents/*, dataset/ground_truth/*.json,
dataset/manifest.json. Deterministic (seeded RNG).
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "dataset" / "raw_documents"
GT = ROOT / "dataset" / "ground_truth"

LINES = [
    "SAMPLE LAND RECORD - FOR TESTING ONLY",
    "District: Demo District",
    "Tehsil: Demo Tehsil",
    "Village: Demo Village",
    "Khata Number: 123",
    "Khasra Number: 78",
    "Survey Number: 145/2",
    "Owner Name: Ramesh Kumar",
    "Father Name: Suresh Kumar",
    "Area: 2.45 Hectare",
    "Land Classification: Agricultural",
    "Mutation Number: M-2024-0091",
    "Record Date: 2024-03-15",
]

WIDTH, FONT_SIZE, MARGIN, LINE_GAP = 1800, 46, 120, 26


def load_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, FONT_SIZE)
        except OSError:
            continue
    return ImageFont.load_default()


def render_base() -> Image.Image:
    font = load_font()
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    heights = [probe.textbbox((0, 0), line, font=font)[3] for line in LINES]
    height = MARGIN * 2 + sum(heights) + LINE_GAP * (len(LINES) - 1)
    img = Image.new("RGB", (WIDTH, height), "white")
    draw = ImageDraw.Draw(img)
    y = MARGIN
    for line, h in zip(LINES, heights):
        draw.text((MARGIN, y), line, fill="black", font=font)
        y += h + LINE_GAP
    return img


def degrade_noisy_skew(img: Image.Image) -> Image.Image:
    rng = np.random.default_rng(42)
    arr = np.asarray(img).astype(np.int16)
    arr += rng.normal(0, 18, arr.shape).astype(np.int16)
    noisy = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return noisy.rotate(2.5, expand=True, fillcolor="white")


def degrade_faded(img: Image.Image) -> Image.Image:
    washed = Image.blend(img, Image.new("RGB", img.size, "white"), 0.55)
    arr = np.asarray(washed).astype(np.float32)
    mean = arr.mean()
    flat = np.clip((arr - mean) * 0.55 + mean, 0, 255).astype(np.uint8)
    return Image.fromarray(flat)


def main() -> None:
    base = render_base()
    variants = {
        "doc01_clean": (base, "EASY", ["printed"]),
        "doc02_noisy": (degrade_noisy_skew(base), "MEDIUM", ["printed", "noisy", "skewed"]),
        "doc03_faded": (degrade_faded(base), "HARD", ["printed", "faded", "low-contrast"]),
    }
    manifest = {"version": "dataset_v1", "documents": []}
    for doc_id, (img, difficulty, attributes) in variants.items():
        png_path = RAW / f"{doc_id}.png"
        img.save(png_path)
        entry_file = f"raw_documents/{doc_id}.png"
        if doc_id == "doc01_clean":
            pdf_path = RAW / f"{doc_id}.pdf"
            img.save(pdf_path, "PDF", resolution=300.0)
            entry_file = f"raw_documents/{doc_id}.pdf"  # benchmark the PDF path
        gt_path = GT / f"{doc_id}.json"
        gt_path.write_text(
            json.dumps({"id": doc_id, "text": "\n".join(LINES), "lines": LINES}, indent=2),
            encoding="utf-8",
        )
        manifest["documents"].append(
            {
                "id": doc_id,
                "file": entry_file,
                "ground_truth": f"ground_truth/{doc_id}.json",
                "difficulty": difficulty,
                "attributes": attributes,
            }
        )
        print(f"wrote {png_path.name}" + (" + pdf" if doc_id == "doc01_clean" else ""))
    (ROOT / "dataset" / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("wrote dataset/manifest.json")


if __name__ == "__main__":
    sys.exit(main())
