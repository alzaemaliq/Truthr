from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
import httpx
import asyncio
import os
import json

# === CONFIG ===
OPENAI_API_KEY = "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"  # Replace with your key
BRAVE_API_KEY = "BSA2cs6XTpvmVAL0dg5_9PW90WNU25R"
BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"

app = FastAPI()

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Async OpenAI call ===
async def call_openai_chat(model: str, messages: list):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0
    }
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
        return response.json()["choices"][0]["message"]["content"]

# === Async Brave Search ===
async def search_brave(query):
    headers = {"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY}
    params = {"q": query, "count": 7}
    async with httpx.AsyncClient() as client:
        response = await client.get(BRAVE_API_URL, headers=headers, params=params)
        results = response.json().get("web", {}).get("results", [])
        return [{"title": r.get("title"), "url": r.get("url"), "snippet": r.get("description")} for r in results]

# === Main Endpoint ===
@app.post("/video")
async def analyze_video(request: Request):
    body = await request.body()
    try:
        body_str = body.decode()
        video_id = body_str.split("videoId=")[1].strip()
        print(f"\n📺 Received video ID: {video_id}")
    except:
        return {"error": "Invalid body format"}

    # === Get Transcript (Threadpool) ===
    from youtube_transcript_api import YouTubeTranscriptApi
    try:
        transcript = await run_in_threadpool(lambda: YouTubeTranscriptApi.get_transcript(video_id, languages=['en']))
        only_text = " ".join([entry['text'] for entry in transcript])
    except Exception as e:
        return {"error": f"Transcript fetch error: {str(e)}"}

    # === Step 2: Extract Claims ===
    claim_prompt = (
    "You are an expert assistant tasked with analyzing a transcript and extracting **claims** made within it. "
    "A claim is a factual or opinion-based statement that asserts something to be true, false, or likely.\n\n"

    "Your output must follow these strict rules:\n"
    "- Only include statements that could reasonably be fact-checked or debated.\n"
    "- Each claim must be written as a fully self-contained sentence — meaning the reader must be able to understand it without seeing the transcript.\n"
    "- Exclude vague, fictional, or narrative descriptions unless they are presented in the transcript as predictions or factual assertions.\n"
    "- Include all necessary context (who, what, when, where) so the claim is specific and unambiguous.\n\n"

    "Format your output as a numbered list:\n"
    "1. [Self-contained claim]\n"
    "2. [Self-contained claim]\n"
    "3. [Self-contained claim]\n"
    "...\n\n"

    "Do not include dramatic imagery or incomplete references (e.g., 'the country', 'the enemy', or 'the report') unless those are clearly defined in the sentence itself."
    )

    claim_messages = [
        {"role": "system", "content": claim_prompt},
        {"role": "user", "content": only_text}
    ]
    claims_raw = await call_openai_chat("gpt-4o-2024-08-06", claim_messages)
    claims = [line.split(". ", 1)[1] for line in claims_raw.splitlines() if line.strip() and line[0].isdigit()]

    # === Step 3: Brave Search for each Claim ===
    claim_evidence_pairs = []
    for claim in claims:
        results = await search_brave(claim)
        snippets = "\n".join([f"- {r['snippet']}" for r in results])
        claim_evidence_pairs.append((claim, snippets))
        await asyncio.sleep(1.2)  # to respect Brave's rate limit

    # === Step 4: Cross-reference with OpenAI ===
    crosscheck_prompt = """
    You are a factuality-checking assistant. For each of the following claims, examine the supporting evidence (snippets from search results). Then for each claim, output:
    
    - "Correct" if the evidence clearly supports it. Do NOT include a correction in this case.
    - "False" if the evidence contradicts it. In this case, provide a corrected version or clarification under 'Correction'.
    - "Unverifiable" if the evidence neither confirms nor contradicts it. In this case, provide a short note in 'Correction' explaining why it's unverifiable or what context is missing.
    
    Be precise and consistent. Always include:
    - 'Claim: [text]'
    - 'Status: Correct / False / Unverifiable'
    - 'Correction:' only if Status is False or Unverifiable (omit if Correct)
    
    Example output format:
    
    Claim: [claim]
    Status: False
    Correction: [brief correction or clarification]
    
    Claim: [claim]
    Status: Correct
    
    Claim: [claim]
    Status: Unverifiable
    Correction: [brief reason why unverifiable]
    """
    batched_results = []

    for i in range(0, len(claim_evidence_pairs), 3):
        batch = claim_evidence_pairs[i:i+3]
        user_input = "You are given a batch of 3 claims and their search result snippets.\n\n"
        for claim, evidence in batch:
            user_input += f"---\nClaim: {claim}\nEvidence:\n{evidence.strip()}\n"
        user_input += "\n---\nProvide one formatted judgment per claim.\n"

        crosscheck_messages = [
            {"role": "system", "content": crosscheck_prompt},
            {"role": "user", "content": user_input}
        ]

        result = await call_openai_chat("gpt-4o-2024-08-06", crosscheck_messages)
        batched_results.append(result if result else "⚠️ GPT returned empty response.")

    print("\n==== FACTUALITY ANALYSIS RESULTS ====\n")
    for section in batched_results:
        print(section.strip())
        print("\n-------------------------------\n")

    return {
        "video_id": video_id,
        "claims_checked": len(claims),
        "result_blocks": batched_results
    }
