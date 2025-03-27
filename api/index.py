from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import os
import re
import unicodedata
import requests

app = Flask(__name__)

def clean_text(text):
    text = unicodedata.normalize("NFKD", text)  # Normalize Unicode characters
    text = re.sub(r'\\u[0-9A-Fa-f]{4}', '', text)  # Remove Unicode escape sequences
    text = re.sub(r'[^\w\s]', '', text)  # Remove non-alphanumeric symbols
    text = re.sub(r'\s+', ' ', text).strip()  # Remove extra whitespace and newlines
    return text

def pdf_to_text(file, file_path):
    text = ""
    try:
        file_stream = file.read()  # Read file into memory
        print(f"[DEBUG] File read into memory from path: {file_path}")
        with fitz.open(stream=file_stream, filetype="pdf") as doc:
            print("[DEBUG] PDF opened successfully")
            for page in doc:
                text += page.get_text("text") + "\n"
    except Exception as e:
        print(f"[ERROR] Failed to process PDF: {e}")
        return None
    return clean_text(text)  # Clean extracted text

def send_to_helpingai(text):
    response = requests.post(
        'https://api.helpingai.co/v1/chat/completions',
        headers={
            'Authorization': 'hl-6bd612ae-c43c-4143-ba20-459b9b9e7544',
            'Content-Type': 'application/json'
        },
        json={
            'model': 'helpingai3-raw',
            'messages': [
                {'role': 'user', 'content': "This is my CV. write a constructive review about my resume and suggest me some recommendation. Keep the tone light and cheerful" + text}
            ],
            'temperature': 0.7,
            'max_tokens': 150
        }
    )
    return response.json()

@app.route("/api/upload", methods=["POST"])
def upload_file():
    print("[DEBUG] Received upload request")
    if "file" not in request.files:
        print("[ERROR] No file part in request")
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    file_path = os.path.abspath(file.filename)  # Get absolute path
    print(f"[DEBUG] File received: {file.filename}, Absolute Path: {file_path}")
    
    if file.filename == "":
        print("[ERROR] No selected file")
        return jsonify({"error": "No selected file"}), 400

    if not file.filename.lower().endswith(".pdf"):
        print("[ERROR] Invalid file type")
        return jsonify({"error": "Only PDF files are allowed"}), 400

    text = pdf_to_text(file, file_path)
    if text is None:
        return jsonify({"error": "Failed to extract text"}), 500

    print("[DEBUG] Successfully extracted text")
    helpingai_response = send_to_helpingai(text)
    
    return jsonify(helpingai_response)

if __name__ == "__main__":
    app.run(debug=True)
