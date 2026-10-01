import asyncio
from src.rag.generator import StreamingRAGGenerator

class DummyDoc:
    def __init__(self, t, s):
        self.title = t
        self.snippet = s

async def test():
    generator = StreamingRAGGenerator()
    docs = [
        DummyDoc("Company Handbook", "The wifi password in the NY office is 'Guest2026!'. Keep it secure.")
    ]
    print("Testing RAG generation stream...")
    async for chunk in generator.generate_stream("What is the NY wifi password?", docs):
        print(chunk, end="")

if __name__ == "__main__":
    asyncio.run(test())
