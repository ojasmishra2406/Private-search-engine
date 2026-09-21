import asyncio
import json

class StreamingRAGGenerator:
    """
    Simulated streaming LLM generator for RAG.
    In a real production environment, this would wrap an OpenAI/vLLM client.
    """
    async def generate_stream(self, query: str, docs: list):
        intro = "Based on the provided verified documents, here is the synthesized information:\n\n"
        for word in intro.split():
            yield f"data: {json.dumps({'token': word + ' '})}\n\n"
            await asyncio.sleep(0.01)
            
        for doc in docs:
            # Simulated synthesis: extracting a fact and attributing it
            sentence = f"According to {doc.title}, {doc.snippet[:60]}... [Doc {doc.doc_id}]\n\n"
            for word in sentence.split():
                yield f"data: {json.dumps({'token': word + ' '})}\n\n"
                await asyncio.sleep(0.01)
                
        yield "data: [DONE]\n\n"
        
    async def fallback_stream(self):
        msg = "I cannot answer this query based on the verified documents available to your clearance level."
        for word in msg.split():
            yield f"data: {json.dumps({'token': word + ' '})}\n\n"
            await asyncio.sleep(0.01)
        yield "data: [DONE]\n\n"
