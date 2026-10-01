import asyncio
import json
import os
from huggingface_hub import AsyncInferenceClient

class StreamingRAGGenerator:
    """
    Streaming LLM generator for RAG using HuggingFace Inference API.
    """
    def __init__(self):
        # Reads HF_TOKEN from environment (.env) automatically
        self.client = AsyncInferenceClient(
            model="HuggingFaceH4/zephyr-7b-beta",
            token=os.environ.get("HF_TOKEN")
        )
        
    async def generate_stream(self, query: str, docs: list):
        # Construct the context
        context_parts = []
        for i, doc in enumerate(docs):
            context_parts.append(f"Document [{i+1}] ({doc.title}): {doc.snippet}")
        context = "\n\n".join(context_parts)
        
        prompt = f"<|system|>\nYou are a highly accurate internal search assistant. Answer strictly using the provided documents. If the documents do not contain the answer, say 'I cannot answer this query based on the available documents.' Always cite your sources using [1], [2], etc.</s>\n<|user|>\nContext:\n{context}\n\nQuery: {query}</s>\n<|assistant|>\n"
        
        try:
            # Stream response from HF Inference API
            async for token_obj in await self.client.text_generation(prompt, max_new_tokens=256, stream=True, temperature=0.1, stop_sequences=["</s>"]):
                token = token_obj.token.text
                if token != "</s>":
                    yield f"data: {json.dumps({'token': token})}\n\n"
                    await asyncio.sleep(0.001)
                    
            yield "data: [DONE]\n\n"
        except Exception as e:
            # Fallback if API fails (e.g. rate limit or no token)
            error_msg = f" [API Error: Please verify your HF_TOKEN in .env. Details: {str(e)}]"
            for word in error_msg.split():
                yield f"data: {json.dumps({'token': word + ' '})}\n\n"
                await asyncio.sleep(0.01)
            yield "data: [DONE]\n\n"
        
    async def fallback_stream(self):
        msg = "I cannot answer this query based on the verified documents available to your clearance level."
        for word in msg.split():
            yield f"data: {json.dumps({'token': word + ' '})}\n\n"
            await asyncio.sleep(0.01)
        yield "data: [DONE]\n\n"
