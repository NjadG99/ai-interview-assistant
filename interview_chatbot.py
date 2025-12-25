import os
import re
import chromadb
from typing import List
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from llama_cpp import Llama

MODEL_PATH = "models/mistral/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
CHROMA_PATH = "./chromadb_data"

KNOWN_COMPANIES = [
    "ibm_india", "hcl_technologies", "tech_mahindra", "l&t_infotech",
    "accenture", "capgemini", "cognizant", "infosys", "tcs", "wipro"
]

def parse_filename(filename: str):
    base = filename.replace(".txt", "").lower()
    for comp in sorted(KNOWN_COMPANIES, key=len, reverse=True):
        if base.startswith(comp + "_"):
            return comp.replace("_", " ").title(), base[len(comp) + 1:].replace("_", " ").title()
    parts = base.split("_", 1)
    return parts[0].title(), parts[1].replace("_", " ").title() if len(parts) > 1 else ""

def load_llm():
    print("🚀 Loading GGUF model via llama.cpp (CUDA if available)...")

    llm = Llama(
        model_path=MODEL_PATH,
        n_gpu_layers=40,
        n_ctx=2048,
        n_batch=512,
        f16_kv=True,
        verbose=False
    )

    print("✅ Model loaded")
    return llm

def init_chromadb():
    return chromadb.PersistentClient(path=CHROMA_PATH)

class InterviewAssistant:
    def __init__(self, llm, chroma):
        self.llm = llm
        self.collection = chroma.get_or_create_collection("interview_content")

    def get_companies(self) -> List[str]:
        result = self.collection.get()
        return sorted({
            m["company"].title()
            for m in result.get("metadatas", [])
            if "company" in m
        })

    def get_roles(self, company: str) -> List[str]:
        result = self.collection.get()
        return sorted({
            m["role"].replace("_", " ").title()
            for m in result.get("metadatas", [])
            if m.get("company") == company.lower()
        })

    def get_raw_content(self, company: str, role: str) -> str:
        tag = f"{company.lower()} - {role.lower()}"
        result = self.collection.get(where={"tag": tag})
        return "\n\n".join(result["documents"]) if result["documents"] else ""

    def extract_section(self, content: str, key: str):
        patterns = {
            "interview_questions": r"📌.*?\n(.*?)(?=\n\n|$)",
            "study_material": r"📚.*?\n(.*?)(?=\n\n|$)",
            "tips": r"💡.*?\n(.*?)(?=\n\n|$)"
        }
        match = re.search(patterns.get(key, ""), content, re.DOTALL)
        return match.group(1).strip() if match else "Section not found."

    def get_section(self, company, role, section):
        content = self.get_raw_content(company, role)
        return self.extract_section(content, section)

    def generate(self, query: str, context: str = "") -> str:
        prompt = f"""[INST]
You are an interview assistant.

Context:
{context[:800]}

User question:
{query}

Give a clear, concise answer in 2–3 sentences.
No self references.
[/INST]
"""
        output = self.llm(
            prompt,
            max_tokens=120,
            temperature=0.6,
            top_p=0.9
        )

        text = output["choices"][0]["text"].strip()
        sentences = text.split(". ")
        result = ". ".join(sentences[:3]).strip()
        return result + "." if not result.endswith(".") else result

print("🤖 Starting Interview Assistant")

llm = load_llm()
chroma = init_chromadb()
assistant = InterviewAssistant(llm, chroma)

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/companies")
def companies():
    return jsonify(assistant.get_companies())

@app.route("/api/roles/<company>")
def roles(company):
    return jsonify(assistant.get_roles(company))

@app.route("/api/content", methods=["POST"])
def content():
    data = request.json
    return jsonify({
        "content": assistant.get_section(
            data["company"], data["role"], data["section_type"]
        )
    })

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    response = assistant.generate(
        data["message"],
        assistant.get_raw_content(data.get("company", ""), data.get("role", ""))
    )
    return jsonify({"response": response})

if __name__ == "__main__":
    print("🔥 Server running on http://127.0.0.1:5000")
    socketio.run(app, host="127.0.0.1", port=5000, debug=False)
