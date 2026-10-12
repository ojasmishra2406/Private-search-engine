# Private Enterprise Search Engine - Demo Script

This script is designed for a 2-3 minute video demonstration of the engine, highlighting its enterprise-grade features: Role-Based Access Control (RBAC), Hybrid Search, and Streaming RAG with Citation Grounding.

## Setup Before Recording
1. Ensure both the backend and frontend are running.
2. Have the web app open in your browser (`http://localhost:5173`).
3. Ensure the database is populated with the default set of mock enterprise documents.

---

## Scene 1: Introduction & Web Crawler
**Visual:** Screen recording starts on the main Search UI.
**Action:** Click the "Web Crawler" tab on the left sidebar.
**Voiceover / Text Overlay:** 
"Welcome to the Private Enterprise Search Engine. We'll start by ingesting some live documentation directly into our vector database using the built-in web crawler."
**Action:** 
- Type `https://dev.java/learn/` into the crawler input.
- Set Depth to `1` and Max Pages to `5`.
- Click "Start Crawling".
- Wait for the success message to appear, demonstrating that pages were fetched, chunked, and vectorized locally.

## Scene 2: Hybrid Search & Reranking
**Visual:** Switch back to the "Search" tab.
**Action:** 
- Ensure the Role is set to `Public`.
- Ensure "Synthesize Answer with RAG" is **unchecked**.
- Search for a general query like: `What is inheritance in Java?`
**Voiceover / Text Overlay:** 
"Our hybrid search combines dense vector embeddings with lexical BM25 matching, and passes candidates through an ONNX INT8 Cross-Encoder to guarantee highly relevant results in under 300ms."
**Action:** 
- Scroll through the results to show the highlighted snippets and fast response times.

## Scene 3: Role-Based Access Control (RBAC) Security
**Visual:** Still on the search page.
**Action:** 
- Clear the search bar.
- Type: `Executive bonuses and compensation`
- Leave the Role as `Public`. Hit Search.
**Voiceover / Text Overlay:** 
"Enterprise security is built-in. If a Public user searches for highly confidential information like executive bonuses, the system completely redacts those documents at the database level."
**Action:** 
- The results should return nothing (or unrelated public documents).
- Now, change the Role dropdown from `Public` to `Admin`.
- Hit Search again.
**Voiceover / Text Overlay:** 
"But when we switch to an Admin clearance level, the exact same query instantly retrieves the confidential financial documents."
**Action:** 
- The confidential documents regarding Q3 bonuses appear in the results.

## Scene 4: Streaming RAG Synthesis & CRAG Gate
**Visual:** Still on the search page with `Admin` role selected.
**Action:** 
- Check the box for **"✨ Synthesize Answer with RAG"**.
- Hit Search for `Executive bonuses and compensation` again.
**Voiceover / Text Overlay:** 
"When we enable RAG synthesis, the engine leverages the retrieved context to stream an answer. Crucially, every claim is strictly attributed to the source documents."
**Action:** 
- The RAG answer box appears and text streams in.
- Click on one of the `[Doc X]` citation chips to show the page smoothly scrolling down to highlight the exact source document.
**Voiceover / Text Overlay:** 
"If we switch back to the Public role and try to synthesize an answer about bonuses..."
**Action:** 
- Change Role to `Public`. Hit Search.
**Voiceover / Text Overlay:** 
"...our CRAG (Corrective RAG) fallback gate instantly detects that the retrieved documents do not have sufficient confidence, and securely refuses to answer, preventing any LLM hallucinations or data leaks."
**Action:** 
- The UI shows the yellow `⚠️ Low Confidence` banner and the streamed answer says: *"I cannot answer this query based on the verified documents available to your clearance level."*

## Scene 5: Outro
**Visual:** Slowly scroll through the clean UI one last time.
**Voiceover / Text Overlay:** 
"A fully local, zero-leakage search engine—built for enterprise scale."
**Action:** Fade to black.
