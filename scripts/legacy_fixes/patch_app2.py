import re

with open("frontend/src/App.jsx", "r", encoding="utf-8") as f:
    content = f.read()

# Add streaming logic to performSearch after fetching
search_logic = """
      if (res.ok) {
        const data = await res.json()
        setResults(data.results || [])
        setTotal(data.total_results || 0)
        setOffset(currentOffset)
        setCurrentQuery(searchQuery)
        setHasSearched(true)
        setTiming(data.timing || null)
        setBlockedCount(data.blocked_count || 0)
        setFallbackTriggered(data.fallback_triggered || false)

        if (synthesize) {
            setRagAnswer('');
            setIsSynthesizing(true);
            
            const eventSource = new EventSource(`${baseUrl}/rag/stream?q=${encodeURIComponent(searchQuery)}&role=${encodeURIComponent(simulatedRole)}`);
            
            eventSource.onmessage = (event) => {
                if (event.data === '[DONE]') {
                    eventSource.close();
                    setIsSynthesizing(false);
                    return;
                }
                try {
                    const data = JSON.parse(event.data);
                    if (data.token) {
                        setRagAnswer(prev => prev + data.token);
                    }
                } catch (e) {
                    console.error(e);
                }
            };
            
            eventSource.onerror = (err) => {
                console.error("SSE Error", err);
                eventSource.close();
                setIsSynthesizing(false);
            };
        }
      }
"""
content = re.sub(r'if \(res\.ok\) \{[\s\S]*?setFallbackTriggered\(data\.fallback_triggered \|\| false\)\s*\}', search_logic, content)

with open("frontend/src/App.jsx", "w", encoding="utf-8") as f:
    f.write(content)
print("Patched App.jsx again")
