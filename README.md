# CryptAVIT — Hybrid Crypto-Stego Client

CryptAVIT is a hybrid cryptography + steganography system that securely hides encrypted messages inside multiple types of media (image, audio, text, and video).

## 🔐 What it does

- Uses **AES-256-GCM** for fast symmetric encryption of the message
- Wraps the AES key using **RSA-3072 OAEP** (public key encryption)
- Packs everything into a custom binary format (`CRYPTAV1`)
- Hides the encrypted package into:
  - 🖼 PNG images (LSB on RGBA channels)
  - 🎵 WAV audio (LSB on PCM samples)
  - 📝 Text files (zero-width Unicode characters)
  - 🎬 Video files (demo: appends encrypted package at file end)

## 🧠 Tech Stack

- **Backend:** Python, Flask
- **Crypto:** `cryptography` library (RSA, AESGCM, hashes, serialization)
- **Stego:**
  - `Pillow` + `numpy` for image processing
  - `wave` + `numpy` for audio
  - zero-width Unicode for text
- **Others:** `Flask-CORS`, `pyngrok` (optional for tunneling)

## 🗂 Project Structure

```text
CrpytAvit/
  app.py               # Flask web server (API + UI routes)
  stego_crypto.py      # All crypto + stego logic
  requirements.txt     # Python dependencies
  templates/           # HTML templates (Flask Jinja2)
    index.html
    ...
  static/              # CSS, JS, images for frontend
    css/
    js/
    img/
