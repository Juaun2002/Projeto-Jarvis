# config.py
import os
import sys
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv(override=True)


def _env_list(var_name: str, default_values: list[str]) -> list[str]:
    raw_value = os.getenv(var_name, "").strip()
    if not raw_value:
        return default_values[:]
    parsed = [item.strip() for item in raw_value.split(",") if item.strip()]
    return parsed or default_values[:]


def _env_float(var_name: str, default_value: float) -> float:
    raw_value = os.getenv(var_name, "").strip()
    if not raw_value:
        return default_value
    try:
        return float(raw_value)
    except ValueError:
        return default_value


def _env_int_or_none(var_name: str):
    raw_value = os.getenv(var_name, "").strip()
    if not raw_value:
        return None
    try:
        return int(raw_value)
    except ValueError:
        return None

# Detecta se está rodando como executável
if getattr(sys, 'frozen', False):
    # Executável PyInstaller
    BASE_PATH = sys._MEIPASS
else:
    # Desenvolvimento
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

PIPER_MODEL_PATH = os.path.join(BASE_PATH, "piper", "models", "pt_BR-faber-medium.onnx")
PIPER_EXE_PATH = os.path.join(BASE_PATH, "piper", "piper.exe")
TTS_BACKEND = os.getenv("TTS_BACKEND", "auto").strip().lower()  # auto | piper | windows_speech | pyttsx3
PIPER_SPEAKER_ID = _env_int_or_none("PIPER_SPEAKER_ID")
PIPER_LENGTH_SCALE = _env_float("PIPER_LENGTH_SCALE", 1.05)
PIPER_NOISE_SCALE = _env_float("PIPER_NOISE_SCALE", 0.55)
PIPER_NOISE_W = _env_float("PIPER_NOISE_W", 0.72)
OWW_THRESHOLD = _env_float("OWW_THRESHOLD", 0.52)
OWW_VAD_THRESHOLD = _env_float("OWW_VAD_THRESHOLD", 0.45)

WHISPER_MODEL = "small"   # base, small, medium (small recomendado)
HOTWORD = "olá"           # nome da hotword principal
HOTWORD_ALIASES = ["jarvis", "jarves", "javis", "assistente", "oi", "ei", "hey"]  # palavras alternativas (evita termos ambíguos)
# IA principal (somente Groq)
GROQ_FREE_MODELS = _env_list(
    "GROQ_FREE_MODELS",
    [
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "openai/gpt-oss-20b",
    ],
)
GROQ_MODEL = os.getenv("GROQ_MODEL", GROQ_FREE_MODELS[0]).strip() or GROQ_FREE_MODELS[0]
GROQ_FALLBACK_MODELS = [GROQ_MODEL] + [model for model in GROQ_FREE_MODELS if model != GROQ_MODEL]
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Conversa contínua sem repetir hotword (mais natural)
FOLLOW_UP_WINDOW_SECONDS = 14
FOLLOW_UP_LISTEN_SECONDS = 4

# Atalhos de programas
PROGRAMS = {
    "whatsapp": r"C:\Users\Public\WhatsApp\WhatsApp.exe",
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
}
