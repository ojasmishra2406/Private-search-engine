import asyncio
import httpx
import json

async def test_streaming_rag():
    print("Testing unauthorized query (Executive bonuses as Public)...")
    
    async with httpx.AsyncClient(timeout=30) as client:
        # Unauthorized
        url = "http://127.0.0.1:8000/rag/stream?q=Executive%20bonuses&role=Public"
        async with client.stream("GET", url) as response:
            output = ""
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]": break
                    data = json.loads(data_str)
                    output += data["token"]
            
            print(f"Public Response: {output.strip()}")
            assert "I cannot answer this query" in output, "Should refuse based on CRAG gate."

        # Authorized
        print("\nTesting authorized query (Executive bonuses as Admin)...")
        url = "http://127.0.0.1:8000/rag/stream?q=Executive%20bonuses&role=Admin"
        async with client.stream("GET", url) as response:
            output = ""
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]": break
                    data = json.loads(data_str)
                    output += data["token"]
                    
            print(f"Admin Response: {output.strip()}")
            assert "According to" in output and "[Doc" in output, "Should stream generated answer with citations."

if __name__ == "__main__":
    asyncio.run(test_streaming_rag())
