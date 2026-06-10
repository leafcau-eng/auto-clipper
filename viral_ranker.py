import os
import json
from config import CACHE_DIR, PROMPTS_DIR, FINAL_TOP_CLIPS
from llm_client import call_llm

def load_prompt() -> str:
    prompt_path = f"{PROMPTS_DIR}viral_ranker.txt"
    if os.path.exists(prompt_path):
        with open(prompt_path) as f:
            return f.read()
    # Default prompt kalau file belum ada
    return """Kamu adalah viral content expert.
Tugasmu menilai potensi viral sebuah clip video dari transkripnya.

Berikan score 0-100 berdasarkan:
- Hook strength (apakah langsung menarik perhatian?)
- Emotional impact (sedih, lucu, mengejutkan, inspiratif?)
- Clarity (mudah dipahami?)
- Shareability (orang mau share?)

Balas HANYA dalam format JSON:
{
  "score": 85,
  "reason": "alasan singkat",
  "hook": "kalimat pertama yang menarik"
}"""

def rank_candidates(candidates: list) -> list:
    prompt_template = load_prompt()
    ranked = []

    for i, candidate in enumerate(candidates):
        cache_file = f"{CACHE_DIR}ranking/candidate_{i}.json"
        os.makedirs(f"{CACHE_DIR}ranking", exist_ok=True)

        if os.path.exists(cache_file):
            print(f"[RANKER] Cache hit: candidate {i}")
            with open(cache_file) as f:
                result = json.load(f)
        else:
            print(f"[RANKER] Ranking candidate {i+1}/{len(candidates)}...")
            prompt = f"{prompt_template}\n\nTranskip clip:\n{candidate['transcript']}"

            try:
                response = call_llm(prompt)
                # Bersihin response kalau ada markdown
                clean = response.strip().replace("```json", "").replace("```", "").strip()
                result = json.loads(clean)
            except Exception as e:
                print(f"[RANKER] Failed candidate {i}: {e}")
                result = {"score": 0, "reason": "failed", "hook": ""}

            with open(cache_file, "w") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

        candidate["score"]  = result.get("score", 0)
        candidate["reason"] = result.get("reason", "")
        candidate["hook"]   = result.get("hook", "")
        ranked.append(candidate)

    # Sort by score
    ranked.sort(key=lambda x: x["score"], reverse=True)
    top = ranked[:FINAL_TOP_CLIPS]

    print(f"\n[RANKER] Top {FINAL_TOP_CLIPS} clips:")
    for i, c in enumerate(top):
        print(f"  #{i+1} Score: {c['score']} | {c['reason']}")

    return top
