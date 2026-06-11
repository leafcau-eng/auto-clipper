import os

# === VIDEO SETTINGS ===
TARGET_CANDIDATES = 20
MIN_CLIP_DURATION = 45
MAX_CLIP_DURATION = 120
FINAL_TOP_CLIPS = 3

# === LLM PROVIDERS (fallback order) ===
LLM_PROVIDERS = [
    {"name": "groq",       "key": os.getenv("GROQ_API_KEY"),       "model": "llama-3.1-8b-instant"},
    {"name": "gemini",     "key": os.getenv("GEMINI_API_KEY"),     "model": "gemini-1.5-flash"},
    {"name": "openai",     "key": os.getenv("OPENAI_API_KEY"),     "model": "gpt-4o-mini"},
    {"name": "deepseek",   "key": os.getenv("DEEPSEEK_API_KEY"),   "model": "deepseek-chat"},
    {"name": "mistral",    "key": os.getenv("MISTRAL_API_KEY"),    "model": "mistral-small-latest"},
    {"name": "openrouter", "key": os.getenv("OPENROUTER_API_KEY"), "model": "meta-llama/llama-3.1-8b-instruct:free"},
]

# === OTHER KEYS ===
YOUTUBE_COOKIES = os.getenv("YOUTUBE_COOKIES")
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN")

# === PATHS ===
DOWNLOAD_DIR = "downloads/"
OUTPUT_DIR   = "outputs/"
CACHE_DIR    = "cache/"
PROMPTS_DIR  = "prompts/"

# === WHISPER ===
WHISPER_MODEL    = "base"
WHISPER_LANGUAGE = "id"

# === RANKING ===
MIN_SCORE_THRESHOLD = 90
