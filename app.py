# app.py
import io
import secrets

from flask import (
    Flask,
    render_template,
    request,
    send_file,
    flash,
    redirect,
    url_for,
)
from werkzeug.utils import secure_filename
from PIL import Image

from stego_crypto import (
    generate_rsa_keypair_pem,
    hybrid_encrypt_package,
    hybrid_decrypt_package,
    embed_into_image_lsb,
    extract_from_image_lsb,
    embed_into_wav_lsb,
    extract_from_wav_lsb,
    embed_into_text_zero_width,
    extract_from_text_zero_width,
    embed_into_video_fallback,
    extract_from_video_fallback,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = secrets.token_hex(16)
app.config["MAX_CONTENT_LENGTH"] = 400 * 1024 * 1024  # 400 MB

ALLOWED_IMAGE = {"png", "bmp", "jpg", "jpeg"}
ALLOWED_WAV = {"wav"}
ALLOWED_VIDEO = {"avi"}
ALLOWED_TEXT = {"txt"}


def allowed_file(filename, kinds):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in kinds


@app.route("/")
def index():
    return redirect(url_for("genkeys"))


@app.route("/genkeys", methods=["GET", "POST"])
def genkeys():
    priv_pem = None
    pub_pem = None
    if request.method == "POST":
        passphrase = request.form.get("passphrase") or None
        pw = passphrase.encode("utf-8") if passphrase else None
        priv_pem, pub_pem = generate_rsa_keypair_pem(password=pw)
        priv_pem = priv_pem.decode("utf-8")
        pub_pem = pub_pem.decode("utf-8")
    return render_template("genkeys.html", priv_pem=priv_pem, pub_pem=pub_pem)


@app.route("/encrypt", methods=["GET", "POST"])
def encrypt():
    if request.method == "POST":
        secret_text = request.form.get("secret") or ""
        recipient_pub_pem = request.form.get("recipient_pub") or ""
        carrier = request.files.get("carrier")
        carrier_type = request.form.get("carrier_type")
        lsb_bits = int(request.form.get("lsb_bits") or 1)
        compress = request.form.get("compress") == "on"

        if not recipient_pub_pem:
            flash("Recipient public key (PEM) required", "danger")
            return redirect(request.url)

        if not carrier or carrier.filename == "":
            flash("Please upload a carrier file", "danger")
            return redirect(request.url)

        filename = secure_filename(carrier.filename)
        ext = filename.rsplit(".", 1)[-1].lower()

        # Build the encrypted package once (used by all carrier types)
        package = hybrid_encrypt_package(
            secret_text.encode("utf-8"),
            recipient_pub_pem.encode("utf-8"),
            compress=compress,
        )

        try:
            # ------------- IMAGE -------------
            if carrier_type == "image" and allowed_file(filename, ALLOWED_IMAGE):
                # Accept JPEG/PNG/BMP. JPEG is converted to PNG internally.
                raw = carrier.read()

                if ext in ("jpg", "jpeg"):
                    # Convert JPEG bytes to PNG in-memory (lossless for LSB)
                    img = Image.open(io.BytesIO(raw)).convert("RGBA")
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    buf.seek(0)
                    out_bytes = embed_into_image_lsb(buf, package, lsb_bits)
                else:
                    # PNG/BMP etc.
                    out_bytes = embed_into_image_lsb(io.BytesIO(raw), package, lsb_bits)

                base_name = filename.rsplit(".", 1)[0]
                out_name = f"stego_{base_name}.png"

                return send_file(
                    io.BytesIO(out_bytes),
                    as_attachment=True,
                    download_name=out_name,
                    mimetype="image/png",
                )

            # ------------- AUDIO -------------
            elif carrier_type == "audio" and allowed_file(filename, ALLOWED_WAV):
                out_bytes = embed_into_wav_lsb(io.BytesIO(carrier.read()), package, lsb_bits)
                return send_file(
                    io.BytesIO(out_bytes),
                    as_attachment=True,
                    download_name="stego_" + filename,
                    mimetype="audio/wav",
                )

            # ------------- TEXT -------------
            elif carrier_type == "text" and allowed_file(filename, ALLOWED_TEXT):
                text_data = carrier.read().decode("utf-8", errors="ignore")
                out_text = embed_into_text_zero_width(text_data, package)
                return send_file(
                    io.BytesIO(out_text.encode("utf-8")),
                    as_attachment=True,
                    download_name="stego_" + filename,
                    mimetype="text/plain",
                )

            # ------------- VIDEO -------------
            elif carrier_type == "video" and allowed_file(filename, ALLOWED_VIDEO):
                out_bytes = embed_into_video_fallback(io.BytesIO(carrier.read()), package)
                return send_file(
                    io.BytesIO(out_bytes),
                    as_attachment=True,
                    download_name="stego_" + filename,
                    mimetype="video/avi",
                )

            else:
                flash(
                    "Unsupported carrier type or file extension. "
                    "Use PNG/JPG/JPEG/BMP for images, WAV for audio, TXT for text, AVI for video.",
                    "danger",
                )
                return redirect(request.url)

        except Exception as e:
            flash("Embedding failed: " + str(e), "danger")
            return redirect(request.url)

    return render_template("encrypt.html")


@app.route("/decrypt", methods=["GET", "POST"])
def decrypt():
    result = None
    if request.method == "POST":
        carrier = request.files.get("carrier")
        priv_key_pem = request.form.get("private_key") or ''
        passphrase = request.form.get('passphrase') or ''
        carrier_type = request.form.get("carrier_type")
        lsb_bits = int(request.form.get("lsb_bits") or 1)

        if not priv_key_pem:
            flash("Private key (PEM) required", "danger")
            return redirect(request.url)

        if not carrier or carrier.filename == "":
            flash("Please upload the carrier file", "danger")
            return redirect(request.url)
        pw = passphrase.encode('utf-8') if passphrase else None
        filename = secure_filename(carrier.filename)
        ext = filename.rsplit(".", 1)[-1].lower()

        try:
            # ------------- IMAGE -------------
            if carrier_type == "image" and allowed_file(filename, ALLOWED_IMAGE):
                raw = carrier.read()
                package = extract_from_image_lsb(io.BytesIO(raw), lsb_bits)

            # ------------- AUDIO -------------
            elif carrier_type == "audio" and allowed_file(filename, ALLOWED_WAV):
                package = extract_from_wav_lsb(io.BytesIO(carrier.read()), lsb_bits)

            # ------------- TEXT -------------
            elif carrier_type == "text" and allowed_file(filename, ALLOWED_TEXT):
                text_data = carrier.read().decode("utf-8", errors="ignore")
                package = extract_from_text_zero_width(text_data)

            # ------------- VIDEO -------------
            elif carrier_type == "video" and allowed_file(filename, ALLOWED_VIDEO):
                package = extract_from_video_fallback(io.BytesIO(carrier.read()))

            else:
                flash("Unsupported carrier type or file extension", "danger")
                return redirect(request.url)

            plaintext = hybrid_decrypt_package(
                package,
                priv_key_pem.encode("utf-8"),password=pw
            )
            result = plaintext.decode("utf-8", errors="replace")
        except ValueError as ve:
            # common for wrong passphrase / no key / parse failures
            flash('Failed to extract/decrypt: ' + str(ve), 'danger')
            return redirect(request.url)
        except Exception as e:
            flash("Failed to extract/decrypt: " + str(e), "danger")
            return redirect(request.url)

    return render_template("decrypt.html", result=result)


if __name__ == "__main__":
    app.run(debug=True)
