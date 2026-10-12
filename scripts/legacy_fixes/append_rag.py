import sys
with open("src/api/main.py", "r", encoding="utf-8") as f:
    content = f.read()

if "/rag/stream" not in content:
    rag_code = """
from fastapi.responses import StreamingResponse
from src.rag.generator import StreamingRAGGenerator

@app.get("/rag/stream")
async def rag_stream(q: str = Query(...), role: str = Query("Public"), domain: Optional[str] = None):
    # 1. Reuse reranked-search logic to get candidates
    search_resp = await reranked_search(q, top_k=20, offset=0, role=role, method="weighted", alpha=0.40, domain=domain)
    
    generator = StreamingRAGGenerator()
    
    # 2. Check CRAG
    if search_resp.fallback_triggered or not search_resp.results:
        return StreamingResponse(generator.fallback_stream(), media_type="text/event-stream")
        
    # 3. Generate Answer
    top_docs = search_resp.results[:3]
    return StreamingResponse(generator.generate_stream(q, top_docs), media_type="text/event-stream")
"""
    with open("src/api/main.py", "a", encoding="utf-8") as f:
        f.write(rag_code)
    print("Appended /rag/stream to main.py")
else:
    print("Already appended")
