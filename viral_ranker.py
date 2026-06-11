import os
import json
from config import CACHE_DIR, PROMPTS_DIR, FINAL_TOP_CLIPS, MIN_SCORE_THRESHOLD
from llm_client import call_llm

def load_prompt() -> str:
    prompt_path = f"{PROMPTS_DIR}viral_ranker.txt"
    if os.path.exists(prompt_path):
        with open(prompt_path) as f:
            return f.read()
    return ""

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

            # Minta semua provider voting
            votes = _multi_provider_vote(prompt)
            result = _aggregate_votes(votes)

            with open(cache_file, "w") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

        candidate["score"]            = result.get("score", 0)
        candidate["reason"]           = result.get("reason", "")
        candidate["hook"]             = result.get("hook", "")
        candidate["emotional_trigger"] = result.get("emotional_trigger", "")
        candidate["verdict"]          = result.get("verdict", "SKIP")
        ranked.append(candidate)

    # Filter hanya yang VIRAL dan score >= threshold
    viral = [c for c in ranked if c["score"] >= MIN_SCORE_THRESHOLD and c["verdict"] == "VIRAL"]
    viral.sort(key=lambda x: x["score"], reverse=True)
    top = viral[:FINAL_TOP_CLIPS]

    # Kalau kurang dari 3, ambil yang score tertinggi walau dibawah threshold
    if len(top) < FINAL_TOP_CLIPS:
        print(f"[RANKER] Kurang dari {FINAL_TOP_CLIPS} viral clips, ambil top score...")
        ranked.sort(key=lambda x: x["score"], reverse=True)
        top = ranked[:FINAL_TOP_CLIPS]

    print(f"\n[RANKER] Top {len(top)} clips:")
    for i, c in enumerate(top):
        print(f"  #{i+1} Score: {c['score']} | {c['verdict']} | {c['reason']}")

    return top

def _multi_provider_vote(prompt: str) -> list:
    from config import LLM_PROVIDERS
    import requests

    votes = []
    for provider in LLM_PROVIDERS[:4]:  # Maks 4 provider voting
        if not provider["key"]:
            continue
        try:
            from llm_client import _call_provider
            response = _call_provider(provider, prompt)
            clean = response.strip().replace("```json", "").replace("```", "").strip()
            result = json.loads(clean)
            votes.append(result)
            print(f"[RANKER] {provider['name']} vote: {result.get('score', 0)}")
        except Exception as e:
            print(f"[RANKER] {provider['name']} failed: {e}")

    return votes

def _aggregate_votes(votes: list) -> dict:
    if not votes:
        return {"score": 0, "reason": "no votes", "hook": "", "verdict": "SKIP"}

    avg_score = sum(v.get("score", 0) for v in votes) / len(votes)
    best = max(votes, key=lambda x: x.get("score", 0))

    return {
        "score": round(avg_score),
        "reason": best.get("reason", ""),
        "hook": best.get("hook", ""),
        "emotional_trigger": best.get("emotional_trigger", ""),
        "verdict": "VIRAL" if avg_score >= 90 else "SKIP"
    }
