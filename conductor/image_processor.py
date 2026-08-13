#!/usr/bin/env python3
"""
GeoCentro Image Processor
Standardizes all alert/news images: download from URL, resize to uniform width,
maintain aspect ratio (no cropping), save as optimized JPG, return local URL path.
"""

import os
import sys
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

import requests
from PIL import Image

# ── Configuration ────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent  # /var/www/geocentro/
IMG_DIR = BASE_DIR / "static" / "img"
TARGET_WIDTH = 640          # pixels — 2× CSS max-width (320px) for retina
JPEG_QUALITY = 85
MAX_FILE_SIZE_MB = 20       # reject images larger than this

def ensure_img_dir():
    """Create the images directory if it doesn't exist."""
    IMG_DIR.mkdir(parents=True, exist_ok=True)

def _generate_filename(url_or_name: str, ext: str = ".jpg") -> str:
    """Generate a unique, URL-safe filename from a URL or name."""
    # Derive a short hash from the URL to avoid collisions
    slug = hashlib.md5(url_or_name.encode()).hexdigest()[:10]
    # Try to extract a meaningful name component
    name_part = ""
    if "/" in url_or_name:
        basename = url_or_name.rsplit("/", 1)[-1].split("?")[0]
        if "." in basename and len(basename) < 80:
            name_part = basename.rsplit(".", 1)[0]
    if not name_part:
        name_part = datetime.now().strftime("img_%Y%m%d_%H%M%S")
    # Sanitize: only alphanumeric, hyphens, underscores
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name_part)
    return f"{safe_name}_{slug}{ext}"

def process_image(source: str, target_width: int = TARGET_WIDTH,
                  jpeg_quality: int = JPEG_QUALITY) -> dict:
    """
    Download and standardize an image from a URL or local path.

    Args:
        source: URL (http/https) or local filesystem path.
        target_width: Desired width in pixels. Height is auto-calculated.
        jpeg_quality: JPEG encoding quality (1-100).

    Returns:
        dict with:
            - success (bool)
            - local_path (Path): absolute path to the saved image
            - web_url (str):  public URL for serving (e.g., /static/img/*)
            - original_width, original_height, new_width, new_height (int)
            - error (str, only on failure)
    """
    ensure_img_dir()
    temp_file = None

    try:
        # ── Step 1: Acquire the image ──
        if source.startswith(("http://", "https://")):
            # Download from URL
            resp = requests.get(source, stream=True, timeout=30,
                                headers={"User-Agent": "GeoCentro/1.0"})
            if resp.status_code >= 400:
                return {"success": False,
                        "error": f"HTTP {resp.status_code} downloading {source}"}

            # Check content-length to avoid downloading huge files
            content_length = resp.headers.get("Content-Length")
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > MAX_FILE_SIZE_MB:
                    return {"success": False,
                            "error": f"Image too large ({size_mb:.1f} MB > {MAX_FILE_SIZE_MB} MB limit)"}

            ext = ".jpg"
            content_type = resp.headers.get("Content-Type", "")
            if "png" in content_type:
                ext = ".png"
            elif "webp" in content_type:
                ext = ".webp"
            elif "gif" in content_type:
                ext = ".gif"

            filename = _generate_filename(source, ext)
            temp_file = IMG_DIR / f"_dl_{filename}"
            with open(temp_file, "wb") as f:
                shutil.copyfileobj(resp.raw, f)
        else:
            # Local file — copy it
            local_src = Path(source)
            if not local_src.is_absolute():
                local_src = BASE_DIR / source
            if not local_src.exists():
                return {"success": False,
                        "error": f"Local file not found: {local_src}"}
            ext = local_src.suffix.lower()
            filename = _generate_filename(source, ext)
            temp_file = IMG_DIR / f"_dl_{filename}"
            shutil.copy2(local_src, temp_file)

        # ── Step 2: Open with Pillow ──
        try:
            img = Image.open(temp_file)
            img.load()
        except Exception:
            raise ValueError(f"Cannot open as image: {temp_file}")

        original_size = img.size  # (width, height)
        original_mode = img.mode

        # ── Step 3: Resize ──
        if img.size[0] <= target_width:
            # Image is already smaller than target — no upscale needed
            # But still convert to RGB and optimize
            new_img = img
            new_size = original_size
        else:
            # Calculate proportional height
            ratio = target_width / img.size[0]
            new_height = int(img.size[1] * ratio)
            new_size = (target_width, new_height)

            # Use LANCZOS (high-quality downsampling)
            new_img = img.resize(new_size, Image.Resampling.LANCZOS)

        # ── Step 4: Convert to RGB and save as JPG ──
        if new_img.mode in ("RGBA", "P", "LA"):
            # Create white background for transparency
            background = Image.new("RGB", new_img.size, (255, 255, 255))
            if new_img.mode == "P":
                new_img = new_img.convert("RGBA")
            background.paste(new_img, mask=new_img.split()[-1] if new_img.mode == "RGBA" else None)
            new_img = background
        elif new_img.mode not in ("RGB", "L"):
            new_img = new_img.convert("RGB")

        output_name = filename.rsplit(".", 1)[0] + ".jpg"
        output_path = IMG_DIR / output_name
        new_img.save(output_path, "JPEG", quality=jpeg_quality, optimize=True)

        # ── Step 5: Cleanup ──
        if temp_file and temp_file.exists():
            temp_file.unlink()

        file_size_kb = output_path.stat().st_size / 1024
        web_url = f"/static/img/{output_name}"

        return {
            "success": True,
            "local_path": str(output_path),
            "web_url": web_url,
            "original_width": original_size[0],
            "original_height": original_size[1],
            "new_width": new_size[0],
            "new_height": new_size[1],
            "file_size_kb": round(file_size_kb, 1),
        }

    except requests.RequestException as e:
        return {"success": False, "error": f"Network error: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Processing error: {e}"}
    finally:
        if temp_file and temp_file.exists():
            temp_file.unlink()


def process_existing_images(dry_run: bool = False) -> list:
    """
    Reprocess all existing images in static/img/ to standardize them.
    Skips already-optimized files (suffix check or size check).

    Returns list of dicts with processing results.
    """
    ensure_img_dir()
    results = []
    existing = sorted(IMG_DIR.glob("*"))
    for img_path in existing:
        if not img_path.is_file():
            continue
        ext = img_path.suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            continue
        if img_path.name.startswith("_dl_"):
            continue  # skip temp download files

        try:
            img = Image.open(img_path)
            img.load()
        except Exception:
            results.append({"file": img_path.name, "success": False,
                            "error": "Cannot open as image"})
            continue

        w, h = img.size
        if w <= TARGET_WIDTH and img_path.suffix.lower() in (".jpg", ".jpeg"):
            # Already small enough and JPEG — skip
            results.append({"file": img_path.name, "success": True,
                            "skipped": True, "reason": f"Already {w}px wide"})
            continue

        if dry_run:
            new_h = int(h * TARGET_WIDTH / w) if w > TARGET_WIDTH else h
            new_w = min(w, TARGET_WIDTH)
            results.append({"file": img_path.name, "success": True,
                            "dry_run": True,
                            "original": f"{w}×{h}",
                            "would_be": f"{new_w}×{new_h}"})
            continue

        try:
            result = process_image(str(img_path), target_width=TARGET_WIDTH)
            if result["success"]:
                # Overwrite the original with the processed version
                processed = Path(result["local_path"])
                if processed != img_path:
                    processed.replace(img_path)
                result["file"] = img_path.name
            else:
                result["file"] = img_path.name
            results.append(result)
        except Exception as e:
            results.append({"file": img_path.name, "success": False,
                            "error": str(e)})

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="GeoCentro Image Processor — standardize alert images"
    )
    sub = parser.add_subparsers(dest="command")

    # process single image
    p_single = sub.add_parser("process", help="Process a single image")
    p_single.add_argument("source", help="URL or local path of the image")
    p_single.add_argument("--width", type=int, default=TARGET_WIDTH,
                          help=f"Target width (default: {TARGET_WIDTH})")
    p_single.add_argument("--quality", type=int, default=JPEG_QUALITY,
                          help=f"JPEG quality (default: {JPEG_QUALITY})")

    # batch reprocess all existing
    p_batch = sub.add_parser("batch", help="Reprocess all existing images in static/img/")
    p_batch.add_argument("--dry-run", action="store_true",
                         help="Show what would be done without actually changing files")
    p_batch.add_argument("--width", type=int, default=TARGET_WIDTH)

    args = parser.parse_args()

    if args.command == "process":
        result = process_image(args.source, target_width=args.width,
                               jpeg_quality=args.quality)
        if result["success"]:
            print(f"✓ Processed: {result['original_width']}×{result['original_height']} "
                  f"→ {result['new_width']}×{result['new_height']} "
                  f"({result['file_size_kb']} KB)")
            print(f"  Local: {result['local_path']}")
            print(f"  Web:   {result['web_url']}")
        else:
            print(f"✗ Error: {result['error']}")
            sys.exit(1)

    elif args.command == "batch":
        results = process_existing_images(dry_run=args.dry_run)
        for r in results:
            if r.get("skipped"):
                print(f"⊙ {r['file']}: SKIP ({r['reason']})")
            elif r.get("dry_run"):
                print(f"→ {r['file']}: {r['original']} → {r['would_be']} (dry-run)")
            elif r["success"]:
                print(f"✓ {r['file']}: {r.get('original_width','?')}×{r.get('original_height','?')} "
                      f"→ {r.get('new_width','?')}×{r.get('new_height','?')} "
                      f"({r.get('file_size_kb', '?')} KB)")
            else:
                print(f"✗ {r['file']}: {r.get('error', 'unknown')}")
        total = len(results)
        ok = sum(1 for r in results if r["success"])
        skipped = sum(1 for r in results if r.get("skipped"))
        failed = total - ok
        print(f"\n─ Total: {total} | ✓ {ok} ({skipped} skipped) | ✗ {failed} ─")

    else:
        parser.print_help()
