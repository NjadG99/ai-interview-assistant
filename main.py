import re
import os
import chromadb
from typing import List, Tuple
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import torch
from ctransformers import AutoModelForCausalLM
from llama_cpp import Llama

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
GPU_NAME = torch.cuda.get_device_name(0) if DEVICE == "cuda" else "None"
NPU_AVAILABLE = False

MODEL_PATH = "models/mistral/mistral-7b-instruct-v0.2.Q4_K_M.gguf"

KNOWN_COMPANIES = [
    "ibm_india", "hcl_technologies", "tech_mahindra", "l&t_infotech",
    "accenture", "capgemini", "cognizant", "infosys", "tcs", "wipro"
]

def parse_filename(filename: str) -> Tuple[str, str]:
    base = filename.replace(".txt", "").lower()
    for comp in sorted(KNOWN_COMPANIES, key=len, reverse=True):
        if base.startswith(comp + "_"):
            return (
                comp.replace("_", " ").title(),
                base[len(comp) + 1:].replace("_", " ").title()
            )
    parts = base.split("_", 1)
    company = parts[0].title()
    role = parts[1].replace("_", " ").title() if len(parts) > 1 else ""
    return company, role

def load_mistral_model():
    try:
        if DEVICE == "cuda":
            llm = AutoModelForCausalLM.from_pretrained(
                MODEL_PATH,
                model_type="mistral",
                gpu_layers=60,
                context_length=2048
            )
            return llm, "NVIDIA_GPU"
        llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=2048,
            n_gpu_layers=0,
            n_batch=512,
            n_threads=8,
            verbose=False,
            f16_kv=True
        )
        return llm, "CPU"
    except Exception:
        return None, None

def init_chromadb():
    return chromadb.PersistentClient(path="./chromadb_data")

def load_content_at_startup(upload_dir="interview_content"):
    client = chromadb.PersistentClient(path="./chromadb_data")
    collection = client.get_or_create_collection("interview_content")

    existing = collection.get().get("documents")
    if existing:
        return len(existing)

    if not os.path.exists(upload_dir):
        return 0

    for filename in os.listdir(upload_dir):
        if not filename.endswith(".txt"):
            continue
        with open(os.path.join(upload_dir, filename), encoding="utf-8") as f:
            content = f.read()
        company, role = parse_filename(filename)
        tag = f"{company.lower()} - {role.lower()}"
        collection.add(
            documents=[content],
            metadatas=[{"tag": tag, "company": company.lower(), "role": role.lower()}],
            ids=[f"{company.lower().replace(' ', '_')}_{role.lower().replace(' ', '_')}"]
        )
    return len(collection.get()["documents"])

class InterviewAssistant:
    def __init__(self, llm, device_type, chromadb_client):
        self.llm = llm
        self.device_type = device_type
        self.collection = chromadb_client.get_or_create_collection("interview_content")

    def get_companies(self) -> List[str]:
        return sorted({
            m["company"].title()
            for m in self.collection.get().get("metadatas", [])
            if "company" in m
        })

    def get_roles(self, company: str) -> List[str]:
        return sorted({
            m["role"].replace("_", " ").title()
            for m in self.collection.get().get("metadatas", [])
            if m.get("company") == company.lower()
        })

    def get_raw_content(self, company: str, role: str) -> str:
        tag = f"{company.lower()} - {role.lower()}"
        result = self.collection.get(where={"tag": tag})
        return "\n\n".join(result["documents"]) if result.get("documents") else ""

    def extract_section_content(self, content: str, section_type: str) -> str:
        patterns = {
            "interview_questions": r"📌[^\n]*\n(.*?)(?=\n\n📚|\n\n💡|\n\n🎯|\n\n⚠️|$)",
            "study_material": r"📚[^\n]*\n(.*?)(?=\n\n📌|\n\n💡|\n\n🎯|\n\n⚠️|$)",
            "tips": r"💡[^\n]*\n(.*?)(?=\n\n📌|\n\n📚|\n\n🎯|\n\n⚠️|$)",
            "mock_interview": r"🎯[^\n]*\n(.*?)(?=\n\n📌|\n\n📚|\n\n💡|\n\n⚠️|$)",
            "common_mistakes": r"⚠️[^\n]*\n(.*?)(?=\n\n📌|\n\n📚|\n\n💡|\n\n🎯|$)"
        }
        match = re.search(patterns.get(section_type, ""), content, re.DOTALL)
        return match.group(1).strip() if match else "Section not found"

    def get_section_content(self, company: str, role: str, section_type: str) -> str:
        content = self.get_raw_content(company, role)
        return self.extract_section_content(content, section_type) if content else "No content found"

    def generate_response(self, query: str, context: str = "") -> str:
        if "GPU" in self.device_type:
            prompt = f"[INST] {query} [/INST]"
            output = self.llm(prompt)
            text = output if isinstance(output, str) else "".join(output)
        else:
            prompt = f"{context[:800]}\n\nQuestion: {query}"
            output = self.llm.create_completion(
                prompt=prompt,
                max_tokens=80,
                temperature=0.7,
                top_p=0.9
            )
            text = output["choices"][0]["text"]

        sentences = text.strip().split(". ")
        reply = ". ".join(sentences[:3]).strip()
        return reply + "." if reply and not reply.endswith(".") else reply

llm, device_type = load_mistral_model()
if not llm:
    exit(1)

chromadb_client = init_chromadb()
loaded_count = load_content_at_startup()
assistant = InterviewAssistant(llm, device_type, chromadb_client)

from talkingsim_blueprint import talkingsim_bp

app = Flask(__name__)
app.config["SECRET_KEY"] = "interview_chatbot_secret_key"
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
app.register_blueprint(talkingsim_bp, url_prefix="/interview")

@app.route("/")
@app.route("/home")
def home():
    return render_template("index.html")

@app.route("/features.html")
def features():
    return render_template("features.html")

@app.route("/hire-ready-ai.html")
def hire_ready_ai():
    return render_template("hire-ready-ai.html")

@app.route("/mock-interview.html")
def mock_interview():
    return render_template("mock-interview.html")

@app.route("/aboutus.html")
def about():
    return render_template("aboutus.html")

@app.route("/api/companies")
def api_companies():
    return jsonify(assistant.get_companies())

@app.route("/api/roles/<company>")
def api_roles(company):
    return jsonify(assistant.get_roles(company))

@app.route("/api/content", methods=["POST"])
def api_content():
    data = request.json
    return jsonify({
        "content": assistant.get_section_content(
            data["company"], data["role"], data["section_type"]
        )
    })

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json
    response = assistant.generate_response(
        data["message"],
        assistant.get_raw_content(
            data.get("company", ""), data.get("role", "")
        )
    )
    return jsonify({"response": response, "device": device_type})

@app.route("/api/status")
def api_status():
    return jsonify({
        "device": device_type,
        "gpu_name": GPU_NAME,
        "openvino_available": NPU_AVAILABLE,
        "loaded_documents": loaded_count
    })

if __name__ == "__main__":
    socketio.run(
        app,
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )
