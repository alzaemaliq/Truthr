from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from youtube_transcript_api import YouTubeTranscriptApi
import json
import os
from starlette.concurrency import run_in_threadpool
from threading import Lock

MAX_REQUESTS = 1000
request_count = 0
request_lock = Lock()


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "truthr-337e8ae71241.json"

system_prompt = """
You are an expert fact-checker and analyst. Your primary objective is to meticulously analyze a given transcript for factual inaccuracies, misleading statements, and unverifiable claims. You are impartial, precise, and rely solely on credible, verifiable sources. You are thorough in your analysis and clear in your presentation of findings. Your tone is neutral and objective.

Analyze the provided transcript to identify and evaluate all verifiable claims. For each claim, you must determine its veracity by cross-referencing it with reliable, publicly available sources.

Step-by-Step Process:
1.	Claim Extraction: First, carefully read through the entire transcript. Identify and extract every distinct and verifiable claim made. A verifiable claim is a statement that can be proven true or false through evidence. Do not extract opinions, personal anecdotes unless they contain a verifiable element, or subjective statements.
2.	Information Gathering and Verification: For each extracted claim, you must conduct a thorough and unbiased search for corroborating or refuting evidence from reputable sources (e.g., established news organizations, scientific journals, academic papers, official government publications). When available, prioritize primary sources. You must use grounding via Google Search and must not rely on internal knowledge.
3.	Categorization and Analysis: Based on your verification, categorize each claim into one of the following statuses:
3.	Categorization and Analysis: Based on your verification, categorize each claim into one of the following statuses:
o	True: The claim is factually accurate and well-supported by credible evidence.
o	False: The claim is factually inaccurate and contradicted by credible evidence.
o	Misleading: The claim is technically true but presented in a way that is deceptive or out of context, leading to a false impression.
o	Unverifiable: There is insufficient credible evidence available to either confirm or deny the claim.
4.	Correction and Elaboration:
o	For any claim that is False, you must provide a concise and accurate correction.
o	For any claim that is Misleading, you must explain the context and clarify why the statement is deceptive.
o	For claims that are True or Unverifiable, no correction is needed.

Output Format:
You must present your findings in the following structured format for each claim identified. Use Markdown for clear presentation.
________________________________________
Claim: "[Insert the exact claim as a direct quote from the transcript]" 
Status: [True/False/Misleading/Unverifiable] 
Correction/Clarification (If not True): [Provide a clear and concise correction or explanation of the misleading context. If the status is True or Unverifiable, state "N/A".]
"""

cleanup_prompt = """
You are a data formatter. Convert the following raw input into clean JSON.

The input contains multiple claims, each with a "Claim", "Status", and "Correction/Clarification (If not True)" section.

Your job is to extract only:
- Claim
- Status
- Correction

Use "N/A" for any missing field. Strip out everything else, including:
- Headers like "### Claim X"
- Asterisks, markdown symbols, and analysis text
- Any footnotes, sources, citations, or sections not part of the three fields above

Format the output as a JSON array like this:

[
  {
    "Claim": "...",
    "Status": "...",
    "Correction": "..."
  },
  ...
]

Be precise, concise, and consistent in output structure. Input Below:
"""

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://khamidenhdcccdekdeafdoiojpnjcjmh"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_streaming_call(client, model, contents, config):
    full_text = ""
    final_response = None
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config
    ):
        if chunk.text:
            full_text += chunk.text
        final_response = chunk
    return full_text, final_response

@app.get("/analyze/{video_id}")
async def analyze(video_id: str):
    global request_count

    with request_lock:
        if request_count >= MAX_REQUESTS:
            return {"error": "Request limit reached (1000 hits)."}
        request_count += 1
    # Get transcript
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    only_text = "Transcript:\n" + " ".join([entry['text'] for entry in transcript])

    # Initialize Gemini client
    client = genai.Client(
        vertexai=True,
        project="truthr",
        location="global",
    )

    # Generate content (first model)
    model = "gemini-2.5-pro"
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=system_prompt + only_text)]
        ),
    ]
    tools = [types.Tool(google_search=types.GoogleSearch())]
    config = types.GenerateContentConfig(
        temperature=0,
        top_p=0.7,
        seed=-274817027,
        max_output_tokens=65535,
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF")
        ],
        tools=tools,
        thinking_config=types.ThinkingConfig(thinking_budget=-1),
    )

    full_text, final_response = await run_in_threadpool(
    run_streaming_call, client, model, contents, config
    )

    # Add citations
    full_text += "\n\n---\n**Citation Sources:**\n"
    citations = final_response.candidates[0].citation_metadata if final_response else None
    if citations and citations.citations:
        for citation in citations.citations:
            full_text += f"- {citation.uri}\n"
    else:
        full_text += "No citation sources found.\n"

    # Add grounding metadata
    gm = final_response.candidates[0].grounding_metadata if final_response else None
    if gm and gm.grounding_supports and gm.grounding_chunks:
        full_text += "\n---\n**Grounding Sources with Segments:**\n"
        chunks = gm.grounding_chunks
        for i, support in enumerate(gm.grounding_supports, start=1):
            seg = support.segment
            start, end = seg.start_index, seg.end_index
            uris = []
            for idx in support.grounding_chunk_indices:
                try:
                    uri = chunks[idx].web.uri if chunks[idx] and chunks[idx].web and chunks[idx].web.uri else "[No URI]"
                    uris.append(uri)
                except Exception:
                    uris.append("[Invalid or missing chunk]")
            full_text += f"{i}. Segment [{start}:{end}] grounded by chunk(s) {support.grounding_chunk_indices} → {uris}\n"
    else:
        full_text += "\n---\nNo grounding metadata or no grounding supports available.\n"

    # Postprocess the full_text with second model
    post_contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=cleanup_prompt + full_text)]
        )
    ]
    post_config = types.GenerateContentConfig(
        temperature=0,
        top_p=0.7,
        seed=0,
        max_output_tokens=65535,
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF")
        ],
        response_mime_type="application/json",
        response_schema={"type": "OBJECT", "properties": {"response": {"type": "STRING"}}},
        thinking_config=types.ThinkingConfig(thinking_budget=-1),
    )

    result = client.models.generate_content(model="gemini-2.5-flash", contents=post_contents, config=post_config)

    raw_response = result.candidates[0].content.parts[0].text
    try:
        response_dict = json.loads(raw_response)
        formatted = json.loads(response_dict["response"])
        return {"claims": formatted}
    except Exception as e:
        return {
            "error": "Failed to parse postprocessed output",
            "details": str(e),
            "raw_output": raw_response
        }
