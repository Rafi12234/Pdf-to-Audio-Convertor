import argparse
import sys
from pathlib import Path

# ---- Text extraction ----
def extract_text_pdfminer(pdf_path: str) -> str:
    try:
        from pdfminer.high_level import extract_text
        return extract_text(pdf_path) or ""
    except Exception as e:
        print(f"[warn] pdfminer extraction failed: {e}", file=sys.stderr)
        return ""

def extract_text_ocr(pdf_path: str, dpi: int = 300, lang: str = "eng") -> str:
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except Exception as e:
        print("[error] OCR dependencies missing. Install with: pip install pdf2image pytesseract", file=sys.stderr)
        raise

    try:
        pages = convert_from_path(pdf_path, dpi=dpi)
    except Exception as e:
        print(f"[error] pdf2image failed. Ensure poppler is installed and on PATH. Details: {e}", file=sys.stderr)
        raise

    text_parts = []
    for i, img in enumerate(pages, 1):
        try:
            txt = pytesseract.image_to_string(img, lang=lang)
        except Exception as e:
            print(f"[warn] Tesseract failed on page {i}: {e}", file=sys.stderr)
            txt = ""
        text_parts.append(txt)
        print(f"[info] OCR page {i}/{len(pages)}: {len(text_parts[-1])} chars", file=sys.stderr)
    return "\n".join(text_parts).strip()

# ---- TTS (offline) ----
def tts_pyttsx3(text: str, out_path: str, voice: str = None, rate: int = None, volume: float = None):
    try:
        import pyttsx3
    except Exception as e:
        print("[error] pyttsx3 not installed. Install with: pip install pyttsx3", file=sys.stderr)
        raise

    engine = pyttsx3.init()
    if voice:
        # try to find a voice by substring match (case-insensitive) in name or id
        v_match = None
        for v in engine.getProperty("voices"):
            name = getattr(v, "name", "") or ""
            vid = getattr(v, "id", "") or ""
            if voice.lower() in name.lower() or voice.lower() in str(vid).lower():
                v_match = v.id
                break
        if v_match is None:
            print(f"[warn] voice '{voice}' not found. Using default.", file=sys.stderr)
        else:
            engine.setProperty("voice", v_match)
    if rate:
        engine.setProperty("rate", int(rate))
    if volume is not None:
        engine.setProperty("volume", float(volume))  # 0.0 - 1.0

    # Note: pyttsx3 typically saves WAV files. Use .wav extension for best results.
    engine.save_to_file(text, out_path)
    engine.runAndWait()

def main():
    parser = argparse.ArgumentParser(
        description="Convert a PDF to an audio narration (offline TTS via pyttsx3)."
    )
    parser.add_argument("pdf", help="Path to input PDF")
    parser.add_argument("-o", "--output", default=None, help="Output audio file (e.g., out.wav). Defaults to <pdf_basename>.wav")
    parser.add_argument("--ocr-fallback", action="store_true", help="If normal text extraction is empty, OCR the pages (requires poppler + Tesseract).")
    parser.add_argument("--ocr-only", action="store_true", help="Force OCR (skip normal text extraction).")
    parser.add_argument("--ocr-lang", default="eng", help="Tesseract language code for OCR (default: eng).")
    parser.add_argument("--voice", default=None, help="Voice name/id substring for pyttsx3 (system dependent).")
    parser.add_argument("--rate", type=int, default=None, help="Speech rate (words per minute).")
    parser.add_argument("--volume", type=float, default=None, help="Volume 0.0 - 1.0")
    parser.add_argument("--save-text", default=None, help="Optional path to save extracted text (e.g., out.txt)")

    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"[error] PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    if args.output is None:
        args.output = str(pdf_path.with_suffix(".wav"))

    print(f"[info] Reading: {pdf_path}", file=sys.stderr)

    text = ""
    if not args.ocr_only:
        text = extract_text_pdfminer(str(pdf_path)).strip()

    if (args.ocr_only or not text) and args.ocr_fallback:
        print("[info] Falling back to OCR...", file=sys.stderr)
        text = extract_text_ocr(str(pdf_path), dpi=300, lang=args.ocr_lang).strip()

    if not text:
        print("[error] No text could be extracted. Try --ocr-fallback or check your PDF.", file=sys.stderr)
        sys.exit(2)

    if args.save_text:
        Path(args.save_text).write_text(text, encoding="utf-8")
        print(f"[info] Saved extracted text to: {args.save_text}", file=sys.stderr)

    print(f"[info] Generating speech -> {args.output}", file=sys.stderr)
    tts_pyttsx3(text, args.output, voice=args.voice, rate=args.rate, volume=args.volume)
    print("[done] All set ✔", file=sys.stderr)

if __name__ == "__main__":
    main()
