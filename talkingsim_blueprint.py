import os
import datetime
import uuid
import base64
import re


from flask import Blueprint, request, jsonify

import torch
import torchaudio
import whisper

from ctransformers import AutoModelForCausalLM

talkingsim_bp = Blueprint("talkingsim", __name__)


class InterviewChatbotWeb:
    def __init__(self):
        self.model_path = "models/mistral/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
        self.base_output_dir = "final/outputs"

        self.questions = [
            "Tell me about yourself and your background.",
            "What are your strongest technical or professional skills?",
            "Describe a difficult problem you solved and how you approached it.",
            "Why are you interested in this role and company?",
            "Where do you see yourself professionally in the next 3–5 years?"
        ]

        self.current_question = 0
        self.interview_responses = []
        self.session_id = None

        self.create_directories()
        self.load_models()

    def create_directories(self):
        for d in ["stt", "tts", "ai_output"]:
            os.makedirs(os.path.join(self.base_output_dir, d), exist_ok=True)

    def load_models(self):
        gpu_layers = 45 if torch.cuda.is_available() else 0

        self.mistral_model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            model_type="mistral",
            gpu_layers=gpu_layers,
            context_length=2048
        )

        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.whisper_model = whisper.load_model("base", device=device)
        self.load_silero_tts()

    def load_silero_tts(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        if self.device.type == "cpu":
            torch.set_num_threads(4)


        self.tts_model, self.symbols, self.sample_rate, _, self.apply_tts = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language="en",
            speaker="lj_16khz"
        )
        self.tts_model.to(self.device)

    def process_audio(self, audio_data):
        audio_bytes = base64.b64decode(audio_data.split(",")[1])
        filename = f"stt_{uuid.uuid4()}.wav"
        path = os.path.join(self.base_output_dir, "stt", filename)

        with open(path, "wb") as f:
            f.write(audio_bytes)

        result = self.whisper_model.transcribe(
            path,
            fp16=torch.cuda.is_available()
        )

        os.remove(path)
        return result["text"].strip()

    def generate_ai_feedback(self, answer, question):
        prompt = f"""
[INST]
You are an interview evaluator.

Analyze the candidate's answer objectively.
Do not praise or encourage.
Focus only on clarity, relevance, depth, and structure.

Question:
{question}

Answer:
{answer}

Respond strictly in this format:

1. Strengths:
2. Weaknesses:
3. Missing elements:
4. How to improve:
[/INST]
"""

        output = self.mistral_model(
            prompt,
            max_new_tokens=250,
            temperature=0.2
        )

        return output.split("[/INST]")[-1].strip()

    def text_to_speech(self, text):
        import soundfile as sf
        
        chunks = self.chunk_text(text)
        audio_parts = []

        for chunk in chunks:
            audio = self.apply_tts(
                texts=[chunk],
                model=self.tts_model,
                sample_rate=self.sample_rate,
                symbols=self.symbols,
                device=self.device
            )[0]
            audio_parts.append(audio)

        final_audio = torch.cat(audio_parts)
        filename = f"tts_{uuid.uuid4()}.wav"
        path = os.path.join(self.base_output_dir, "tts", filename)

        sf.write(
            path,
            final_audio.cpu().numpy(),
            self.sample_rate
        )

        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()

        os.remove(path)
        return f"data:audio/wav;base64,{encoded}"

    def chunk_text(self, text, limit=120):
        text = re.sub(r"<[^>]+>", "", text)
        words = text.split()

        chunks, current = [], ""
        for w in words:
            if len(current) + len(w) > limit:
                chunks.append(current.strip())
                current = w
            else:
                current += " " + w
        if current:
            chunks.append(current.strip())
        return chunks


chatbot = InterviewChatbotWeb()


@talkingsim_bp.route("/start_interview", methods=["POST"])
def start_interview():
    chatbot.session_id = str(uuid.uuid4())
    chatbot.current_question = 0
    chatbot.interview_responses.clear()

    q = chatbot.questions[0]
    return jsonify({
        "success": True,
        "session_id": chatbot.session_id,
        "question": q,
        "tts_audio": chatbot.text_to_speech(q)
    })


@talkingsim_bp.route("/submit_answer", methods=["POST"])
def submit_answer():
    data = request.get_json()
    text = chatbot.process_audio(data["audio_data"])

    q = chatbot.questions[chatbot.current_question]
    chatbot.interview_responses.append({
        "question": q,
        "answer": text
    })

    chatbot.current_question += 1

    if chatbot.current_question >= len(chatbot.questions):
        return jsonify({
            "success": True,
            "interview_complete": True
        })

    next_q = chatbot.questions[chatbot.current_question]
    return jsonify({
        "success": True,
        "transcribed_text": text,
        "next_question": next_q,
        "tts_audio": chatbot.text_to_speech(next_q)
    })


@talkingsim_bp.route("/get_single_feedback", methods=["POST"])
def get_single_feedback():
    data = request.get_json()
    feedback = chatbot.generate_ai_feedback(data["answer"], data["question"])

    return jsonify({
        "success": True,
        "feedback": feedback,
        "feedback_audio": chatbot.text_to_speech(feedback)
    })


@talkingsim_bp.route("/reset_interview", methods=["POST"])
def reset_interview():
    chatbot.session_id = None
    chatbot.current_question = 0
    chatbot.interview_responses.clear()
    return jsonify({"success": True})
