from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import re
import unicodedata
import requests
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(stream=pdf_path.read(), filetype="pdf")
        return " ".join([page.get_text("text") for page in doc])
    except Exception as e:
        return str(e)

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
    <title>ResumeGPT</title>
    <script>
        function uploadFile() {
            const fileInput = document.getElementById("fileInput");
            const toneSelect = document.getElementById("tone");

            if (!fileInput || !fileInput.files.length) {
                alert("Please select a file.");
                return;
            }

            document.getElementById("output").style.opacity = 1; // Added line
            document.getElementById("output").innerText = "Uploading...";

            const formData = new FormData();
            formData.append("file", fileInput.files[0]);
            formData.append("tone", toneSelect.value);

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

        let recognition;
function startInterview() {
     window.location.href += "interview";  // this reloads
}

function speak(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    utterance.rate = 1; 
    utterance.pitch = 1; 
    speechSynthesis.speak(utterance);
}

function startListening() {
    recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
        const userAnswer = event.results[0][0].transcript;
        document.getElementById("output").innerText = "You: " + userAnswer;
        continueInterview(userAnswer);
    };

    recognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
    };

    recognition.start();
}

function continueInterview(userAnswer) {
    fetch("http://127.0.0.1:5000/api/interview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer: userAnswer, resume_text: "" }) 
    })
    .then(response => response.json())
    .then(data => {
        const question = data.question || "Error: " + data.error;
        document.getElementById("output").innerText = question;
        speak(question);
    })
    .catch(error => {
        console.error("Interview API error:", error);
        document.getElementById("output").innerText = "Error: Failed to continue interview.";
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
    <h2>ReviewGPT</h2>
    
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
    <button id="start_interview" onclick="startInterview()">Free 1:1 AI Interview!</button>
    <div id="output"></div>
</body>
</html>
    """


@app.route("/api/interview", methods=["POST"])
def interview():
    data = request.json
    user_answer = data.get("answer", "").strip()
    resume_text = data.get("resume_text", "").strip()

    if not resume_text and not user_answer:
        return jsonify({"error": "No resume data or user answer found"}), 400

    prompt = f"You are a professional interviewer USE PROFFESIONAL AND FORMAL LANGUAGE ONLY NO FUNNY AND CASUAL LANGUAGE ONLY AND ONLY FORMAL LANGUAGE. DONT SPEAK RESUME DETAILS ONLY ASK QUESTIONS AS IF IT IS A INTERVIEW. Resume details:\n{resume_text}\n\n"
    if user_answer:
        prompt += f"Candidate's answer: {user_answer}\n\nNow, ask the next question."
    else:
        prompt += "Ask the first interview question."

    response = requests.post(
        "https://api.helpingai.co/v1/chat/completions",
        headers={"Authorization": "hl-6bd612ae-c43c-4143-ba20-459b9b9e7544", "Content-Type": "application/json"},
        json={"model": "helpingai3-raw", "messages": [{"role": "system", "content": "You are an AI interviewer."}, {"role": "user", "content": prompt}], "temperature": 0.7, "max_tokens": 150}
    )

    ai_question = response.json().get("choices", [{}])[0].get("message", {}).get("content", "I didn't understand that.")
    
    return jsonify({"question": ai_question})


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
    

def ask_ai_for_questions(resume_text, previous_answer=None):
    prompt = "Extract key details from this resume and generate an interview question: " + resume_text
    if previous_answer:
        prompt = "Based on the candidate's last response: '" + previous_answer + "', generate the next interview question in a professional manner."
    response = requests.post(
        "https://api.helpingai.co/v1/chat/completions",
        headers={"Authorization": "hl-6bd612ae-c43c-4143-ba20-459b9b9e7544", "Content-Type": "application/json"},
        json={"model": "helpingai3-raw", "messages": [{"role": "system", "content": "You are a professional AI interviewer. ONLY USE PROFESSIONAL LANGUAGE AND BE FORMAL THROUGHOUT. ALSO WRITE ONLY QUESTIONS, NO FLUFF AT ALL ONLY PROFESSIONALISM"}, {"role": "user", "content": prompt}], "temperature": 0.7, "max_tokens": 150}
    )
    return response.json().get("choices", [{}])[0].get("message", {}).get("content", "No question generated.")

@app.route('/interview', methods=['GET', 'POST'])
def upload_resume():
    if request.method == 'POST':
        file = request.files['resume']
        if file:
            resume_text = extract_text_from_pdf(file)
            first_question = ask_ai_for_questions(resume_text)
            return '''
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <title>Interview</title>
                <link rel="stylesheet" href="static/interview.css">
                <script>
                    let credits = localStorage.getItem("credits") ? parseInt(localStorage.getItem("credits")) : 100;
                    document.addEventListener("DOMContentLoaded", function() {
                        document.getElementById("credits").innerText = "Credits: " + credits;
                        document.getElementById("chat").innerHTML += `<p><strong>AI:</strong> ''' + first_question + '''</p>`;
                    });
                    
                    function sendMessage() {
                        if (credits <= 0) {
                            alert("You have exhausted your available credits.");
                            return;
                        }
                        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                        if (!SpeechRecognition) {
                            alert("Speech recognition is not supported in this browser.");
                            return;
                        }
                        const recognition = new SpeechRecognition();
                        recognition.onstart = function() {
                            console.log("Listening...");
                        };
                        recognition.onresult = async function(event) {
                            if (event.results.length > 0) {
                                const transcript = event.results[0][0].transcript;
                                console.log("Recognized:", transcript);
                                credits -= 2;
                                localStorage.setItem("credits", credits);
                                document.getElementById("credits").innerText = "Credits: " + credits;
                                document.getElementById("chat").innerHTML += "<p><strong>Candidate:</strong> " + transcript + "</p>";
                                let response = await fetch('/next_question', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ response: transcript })
                                }).then(res => res.text());
                                console.log("AI:", response);
                                document.getElementById("chat").innerHTML += "<p><strong>AI:</strong> " + response + "</p>";
                            } else {
                                document.getElementById('retry').style.display = 'block';
                            }
                        };
                        recognition.onerror = function() {
                            document.getElementById('retry').style.display = 'block';
                        };
                        recognition.start();
                    }
                    
                    function reviewChat() {
                    if (credits < 10) {
                        alert("Not enough credits! You need at least 10 credits to review your chat.");
                        return;
                    }
                        document.getElementById("reviewBox").style.opacity = 1; // Added line
                        let chatText = document.getElementById("chat").innerText;
                        fetch('/review_chat', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ chat: chatText })
                        })
                        .then(res => res.text())
                        .then(score => {
                            credits -= 10;
                            localStorage.setItem("credits", credits);
                            document.getElementById("credits").innerText = "Credits: " + credits;
                            document.getElementById("reviewBox").innerText = "Your speaking review: " + score;
                        });
                    }
                </script>
            </head>
            <body>
                <h2>Interview</h2>
                <p id="credits">Credits: 100</p>
                <div id="chat" style="border:1px solid #000; padding:10px; width:300px; height:400px; overflow-y:auto;"></div>
                <button onclick="sendMessage()">Speak - 2 credits</button>
                <button id="retry" style="display:none; margin-top: 10px;" onclick="sendMessage()">Retry</button>
                <button onclick="reviewChat()">Review Chat - 10 credits</button>
                <div id="reviewBox" style="border:1px solid #000; padding:10px; margin-top:10px; width:300px;"></div>
            </body>
            </html>
            '''
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Upload Resume</title>
        <link rel="stylesheet" type="text/css" href="static/upload.css">
        <script>
            function openFileDialog() {
                document.getElementById('resume').click();
            }
            function updateFileName() {
                const fileInput = document.getElementById('resume');
                const fileNameDisplay = document.getElementById('fileName');
                fileNameDisplay.innerText = fileInput.files.length > 0 ? fileInput.files[0].name : "No file chosen";
            }
        </script>
    </head>
    <body>
        <h2>Upload Your Resume</h2>
        <form method="post" enctype="multipart/form-data">
            <input type="file" id="resume" name="resume" required onchange="updateFileName()" hidden>
            <button type="button" onclick="openFileDialog()">Choose File</button>
            <span id="fileName">No file chose</span>
            <button id="start" type="submit">Upload and Start Interview</button>
        </form>
    </body>
    </html>
    '''

@app.route('/next_question', methods=['POST'])
def next_question():
    data = request.json
    user_response = data.get("response", "")
    next_question = ask_ai_for_questions("", user_response)
    return next_question

@app.route('/review_chat', methods=['POST'])
def review_chat():
    data = request.json
    chat_text = data.get("chat", "")
    review_prompt = "and reply with only the score Evaluate this candidate's interview responses and provide a score out of 10: " + chat_text
    response = requests.post(
        "https://api.helpingai.co/v1/chat/completions",
        headers={"Authorization": "hl-6bd612ae-c43c-4143-ba20-459b9b9e7544", "Content-Type": "application/json"},
        json={"model": "helpingai3-raw", "messages": [{"role": "system", "content": "You are an AI reviewer."}, {"role": "user", "content": review_prompt}], "temperature": 0.7, "max_tokens": 50}
    )
    return response.json().get("choices", [{}])[0].get("message", {}).get("content", "Score not generated.")


if __name__ == "__main__":
    app.run(debug=True)
