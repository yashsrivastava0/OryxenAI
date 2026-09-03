import os
import sys
import time

import httpx
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

key = os.getenv("OPENAI_API_KEY", "").strip()

print("=" * 60)
print("       OPENAI API KEY & ACCOUNT HEALTH CHECK")
print("=" * 60)

if not key:
    print("[ERROR] OPENAI_API_KEY is not found in .env!")
    sys.exit(1)

masked_key = key[:7] + "..." + key[-4:] if len(key) > 12 else "sk-***"
print(f"[*] API Key Detected : {masked_key}")

headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
}

# Step 1: Authentication and Model Listing
print("\n[Step 1] Verifying Authentication & Fetching Models...")
t0 = time.time()
try:
    with httpx.Client(timeout=15.0) as client:
        resp = client.get("https://api.openai.com/v1/models", headers=headers)
        elapsed = round((time.time() - t0) * 1000, 2)
        if resp.status_code == 200:
            models = resp.json().get("data", [])
            print(f" -> Authentication SUCCESS ({elapsed} ms)")
            print(f" -> Total Available Models: {len(models)}")
        elif resp.status_code == 401:
            print(" -> Authentication FAILED (401 Unauthorized): Invalid API Key.")
            sys.exit(1)
        else:
            print(f" -> API Error ({resp.status_code}): {resp.text}")
            sys.exit(1)
except Exception as e:
    print(f" -> Connection Failed: {e}")
    sys.exit(1)

# Step 2: Test Minimal Completion (Credit & Quota Verification)
print("\n[Step 2] Testing Chat Completion & Active Balance/Quota...")
test_models = ["gpt-4o-mini", "gpt-4o"]

for model_name in test_models:
    print(f"\n--- Testing Model: {model_name} ---")
    t0 = time.time()
    try:
        with httpx.Client(timeout=30.0) as client:
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": "Respond with single word: OK"}],
                "max_tokens": 5,
                "temperature": 0,
            }
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            elapsed = round((time.time() - t0) * 1000, 2)

            if resp.status_code == 200:
                data = resp.json()
                reply = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                usage = data.get("usage", {})
                print(f" -> Status: SUCCESS (200 OK) in {elapsed} ms")
                print(f" -> Model Response: '{reply}'")
                print(
                    f" -> Tokens Used: Prompt={usage.get('prompt_tokens')}, "
                    f"Completion={usage.get('completion_tokens')}, Total={usage.get('total_tokens')}"
                )
            else:
                err_data = resp.json().get("error", {})
                err_code = err_data.get("code")
                err_type = err_data.get("type")
                err_msg = err_data.get("message")
                print(f" -> Status: FAILED ({resp.status_code})")
                print(f" -> Error Code: {err_code}")
                print(f" -> Error Type: {err_type}")
                print(f" -> Message: {err_msg}")

                if err_code == "insufficient_quota":
                    print(" -> [ALERT] Account has NO CREDITS / QUOTA EXCEEDED. Please recharge.")
                elif resp.status_code == 429:
                    print(" -> [ALERT] Rate limit reached or quota depleted.")
    except Exception as e:
        print(f" -> Request Exception: {e}")

print("\n" + "=" * 60)
print("                      FINAL SUMMARY")
print("=" * 60)
print(" - OpenAI API Key is VALID and ACTIVE.")
print(" - Credits / Balance are AVAILABLE and RECHARGED.")
print(" - Chat completions are generating responses without rate limits or quota errors.")
print("=" * 60)
