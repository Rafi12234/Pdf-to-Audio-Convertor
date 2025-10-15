from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
from utils import extract_text_pdfminer, smart_chunk
import tempfile
import os

app = Flask(__name__, static_url_path='/static', static_folder='static', template_folder='templates')
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB max upload

ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"ok": False, "error": "No selected file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"ok": False, "error": "Only PDF files are allowed"}), 400

    # Save to a temp file
    filename = secure_filename(file.filename)
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = Path(tmpdir) / filename
        file.save(str(fpath))

        # Extract text
        text = extract_text_pdfminer(str(fpath)).strip()

    if not text:
        # If you want OCR fallback later, add it in utils and call here.
        return jsonify({"ok": False, "error": "No readable text found in PDF. If it's scanned, enable OCR in backend."}), 200

    # Chunk it for smoother speech synthesis
    chunks = smart_chunk(text, max_chars=280)  # short chunks for natural playback

    return jsonify({
        "ok": True,
        "filename": filename,
        "chunk_count": len(chunks),
        "chunks": chunks
    })

if __name__ == "__main__":
    # Run dev server
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)
