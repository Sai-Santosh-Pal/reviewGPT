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
        with fitz.open(stream=file_stream, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text("text") + "\n"
    except Exception as e:
        return None
    return clean_text(text)  # Clean extracted text

def send_to_helpingai(text, tone):
    tone_prompts = {
        "friendly": "Write a warm and friendly review of my resume, encouraging me with positive feedback and constructive suggestions.",
        "roast": "Critique my resume harshly, like a brutal roast. Be savage but insightful.",
        "advice": "Provide professional career advice based on my resume. Give actionable tips for improvement.",
        "formal": "Give me a formal and professional review of my resume with detailed recommendations.",
    }
    
    prompt = tone_prompts.get(tone, tone_prompts["friendly"])  # Default to friendly if tone is invalid
    prompt += f" Here is my resume text and review this: {text}"
    
    response = requests.post(
        'https://api.helpingai.co/v1/chat/completions',
        headers={
            'Authorization': 'hl-6bd612ae-c43c-4143-ba20-459b9b9e7544',
            'Content-Type': 'application/json'
        },
        json={
            'model': 'helpingai3-raw',
            'messages': [{'role': 'user', 'content': prompt}],
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
    <script>
        function uploadFile() {
            const fileInput = document.getElementById("fileInput");
            const toneSelect = document.getElementById("tone");
            if (!fileInput || !fileInput.files.length) {
                alert("Please select a file.");
                return;
            }

            document.getElementById("output").innerText = "Loading..";
            document.getElementById("output").style.opacity = 1;
            const formData = new FormData();
            formData.append("file", fileInput.files[0]);
            formData.append("tone", toneSelect.value); // Send selected tone

            fetch("/api/upload", {
                method: "POST",
                body: formData
            })
            .then(response => response.json()) 
            .then(data => {
                document.getElementById("output").innerText = data.content || "Unexpected response format";
            })
            .catch(error => {
                document.getElementById("output").innerText = "Error: " + error.message;
            });
        }

        function updateFileName(event) {
            const fileNameDisplay = document.getElementById("fileName");
            fileNameDisplay.innerText = event.target.files.length ? event.target.files[0].name : "No file selected";
        }
    </script>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <h2>Upload Your Resume (PDF)</h2>
    
    <label for="fileInput" class="file-label">Choose a file</label>
    <input type="file" id="fileInput" accept="application/pdf" onchange="updateFileName(event)">
    <p id="fileName">No file selected</p>

    <label for="tone">Select Tone:</label>
    <select id="tone">
        <option value="friendly">Friendly</option>
        <option value="roast">Roast</option>
        <option value="advice">Advice</option>
        <option value="formal">Formal</option>
    </select>

    <button onclick="uploadFile()">Upload</button>
    <div id="output"></div>
</body>
</html>
    """

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files or "tone" not in request.form:
        return jsonify({"error": "Missing file or tone"}), 400

    file = request.files["file"]
    tone = request.form["tone"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are allowed"}), 400

    text = pdf_to_text(file)
    if text is None:
        return jsonify({"error": "Failed to extract text"}), 500

    response = send_to_helpingai(text, tone)
    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

    return jsonify({"content": content}) 

if __name__ == "__main__":
    app.run(debug=True)

