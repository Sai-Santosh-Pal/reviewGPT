from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import re
import unicodedata
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

def clean_text(text):
    text = unicodedata.normalize("NFKD", text)  # Normalize Unicode characters
    text = re.sub(r'\\u[0-9A-Fa-f]{4}', '', text)  # Remove Unicode escape sequences
    text = re.sub(r'[^\w\s]', '', text)  # Remove non-alphanumeric symbols
    text = re.sub(r'\s+', ' ', text).strip()  # Remove extra whitespace and newlines
    return text

def pdf_to_text(file):
    text = ""
    try:
        file_stream = file.read()  # Read file into memory
        print("[DEBUG] File read into memory")
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
                {'role': 'user', 'content': "This is my CV. Write a constructive review about my resume and suggest recommendations. Keep the tone light and cheerful. " + text}
            ],
            'temperature': 0.7,
            'max_tokens': 150
        }
    )
    return response.json()

@app.route("/")
def home():
    return """
    <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume Analyzer</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        #output { margin-top: 20px; white-space: pre-wrap; text-align: left; display: inline-block; max-width: 80%; }
    </style>
</head>
<body>
    <h2>Upload Your Resume (PDF)</h2>
    <input type="file" id="fileInput" accept="application/pdf">
    <button onclick="uploadFile()">Upload</button>
    <div id="output"></div>

    <script>
        function uploadFile() {
            const fileInput = document.getElementById("fileInput");
            if (!fileInput.files.length) {
                alert("Please select a file.");
                return;
            }
            
            const formData = new FormData();
            formData.append("file", fileInput.files[0]);
            
            fetch("http://127.0.0.1:5000/api/upload", {
                method: "POST",
                body: formData
            })
            .then(response => response.text())  // Get plain text response
            .then(data => {
                document.getElementById("output").innerHTML = data.replace(/\n/g, "<br>"); // Preserve line breaks
            })
            .catch(error => {
                document.getElementById("output").innerText = "Error: " + error;
            });
        }
    </script>
</body>
</html>
    """

@app.route("/api/upload", methods=["POST"])
def upload_file():
    print("[DEBUG] Received upload request")
    if "file" not in request.files:
        print("[ERROR] No file part in request")
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    
    if file.filename == "":
        print("[ERROR] No selected file")
        return jsonify({"error": "No selected file"}), 400

    if not file.filename.lower().endswith(".pdf"):
        print("[ERROR] Invalid file type")
        return jsonify({"error": "Only PDF files are allowed"}), 400

    text = pdf_to_text(file)
    if text is None:
        return jsonify({"error": "Failed to extract text"}), 500

    print("[DEBUG] Successfully extracted text")
    response = send_to_helpingai(text)
    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

    return content

if __name__ == "__main__":
    print("[DEBUG] Starting Flask server...")
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)
