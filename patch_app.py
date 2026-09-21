with open("frontend/src/App.jsx", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add states
states = """  const [timing, setTiming]         = useState(null)
  const [fallbackTriggered, setFallbackTriggered] = useState(false)
  const [synthesize, setSynthesize] = useState(false)
  const [ragAnswer, setRagAnswer] = useState('')
  const [isSynthesizing, setIsSynthesizing] = useState(false)"""
content = content.replace("  const [timing, setTiming]         = useState(null)", states)

# 2. Add sim role state
role_state = """  const [simulatedRole, setSimulatedRole] = useState('Public')"""
if "simulatedRole" not in content:
    content = content.replace("  const [loading, setLoading]       = useState(false)", "  const [loading, setLoading]       = useState(false)\n" + role_state)

# 3. Add to params
params_inject = """      let params = new URLSearchParams({
          q: searchQuery,
          top_k: currentPageSize,
          offset: currentOffset,
          role: simulatedRole
      })"""
content = content.replace("""      let params = new URLSearchParams({
          q: searchQuery,
          top_k: currentPageSize,
          offset: currentOffset
      })""", params_inject)

# 4. Add fetching logic
fetch_logic = """      const data = await res.json()
      setResults(data.results || [])
      setTotal(data.total_results || 0)
      setOffset(currentOffset)
      setCurrentQuery(searchQuery)
      setHasSearched(true)
      setTiming(data.timing || null)
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
      }"""
content = content.replace("""      const data = await res.json()
      setResults(data.results || [])
      setTotal(data.total_results || 0)
      setOffset(currentOffset)
      setCurrentQuery(searchQuery)
      setHasSearched(true)
      setTiming(data.timing || null)""", fetch_logic)

# 5. UI elements
ui_toggle = """            <button type="submit" className="search-submit" disabled={loading}>
                    {loading ? '...' : 'Search'}
                  </button>
                </div>
                <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', color: '#495057' }}>
                  <input 
                    type="checkbox" 
                    id="synthesizeToggle" 
                    checked={synthesize} 
                    onChange={(e) => setSynthesize(e.target.checked)} 
                    style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                  />
                  <label htmlFor="synthesizeToggle" style={{ cursor: 'pointer', fontWeight: '500' }}>
                    ? Synthesize Answer with RAG
                  </label>
                  <span style={{ marginLeft: '12px', color: '#6c757d' }}>Role:</span>
                  <select 
                    value={simulatedRole} 
                    onChange={(e) => setSimulatedRole(e.target.value)}
                    style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #ced4da', fontSize: '14px' }}
                  >
                    <option value="Public">Public</option>
                    <option value="Engineering">Engineering</option>
                    <option value="HR">HR</option>
                    <option value="Finance">Finance</option>
                    <option value="Admin">Admin</option>
                  </select>
                </div>"""
content = content.replace("""            <button type="submit" className="search-submit" disabled={loading}>
                    {loading ? '...' : 'Search'}
                  </button>
                </div>""", ui_toggle)

ui_rag_box = """            </form>
            
            <div className="search-results-container">
              {hasSearched && !error && fallbackTriggered && (
                <div className="crag-warning-banner" style={{ background: '#fff3cd', color: '#856404', padding: '12px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #ffeeba', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>??</span>
                  <span><strong>Low Confidence:</strong> Retrieved passages do not meet internal grounding thresholds for your clearance level.</span>
                </div>
              )}

              {hasSearched && !error && (synthesize || ragAnswer) && (
                <div className="rag-answer-box" style={{ background: '#f8f9fa', border: '1px solid #e9ecef', borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', borderBottom: '1px solid #dee2e6', paddingBottom: '12px' }}>
                    <span style={{ fontSize: '18px' }}>?</span>
                    <h3 style={{ margin: 0, color: '#212529', fontSize: '16px' }}>Synthesized Answer</h3>
                    {isSynthesizing && <span style={{ fontSize: '12px', color: '#6c757d', marginLeft: 'auto' }}>Generating...</span>}
                  </div>
                  <div style={{ color: '#495057', lineHeight: '1.6', fontSize: '15px', whiteSpace: 'pre-wrap' }}>
                    {ragAnswer.split(/(\[Doc [a-zA-Z0-9-]+\])/).map((part, i) => {
                      if (part.startsWith('[Doc ')) {
                        const docId = part.slice(5, -1);
                        return (
                          <span key={i} className="citation-chip" style={{ background: '#e2e3e5', padding: '2px 8px', borderRadius: '12px', fontSize: '12px', color: '#383d41', cursor: 'pointer', margin: '0 4px', border: '1px solid #d6d8db' }} onClick={() => {
                            const el = document.getElementById(`doc-${docId}`);
                            if (el) {
                              el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                              el.style.backgroundColor = '#fff3cd';
                              setTimeout(() => el.style.backgroundColor = '', 2000);
                            }
                          }}>
                            {part}
                          </span>
                        );
                      }
                      return <span key={i}>{part}</span>;
                    })}
                  </div>
                </div>
              )}"""
content = content.replace("""            </form>
            
            <div className="search-results-container">""", ui_rag_box)

results_list = """              <div className="results-list">
                {results.map((res, i) => (
                  <div key={`${res.doc_id || res.url}-${i}`} id={`doc-${res.doc_id}`} className="result-card" style={{ transition: 'background-color 0.5s' }}>"""
content = content.replace("""              <div className="results-list">
                {results.map((res, i) => (
                  <div key={`${res.doc_id || res.url}-${i}`} className="result-card">""", results_list)

with open("frontend/src/App.jsx", "w", encoding="utf-8") as f:
    f.write(content)
print("Patched successfully")
