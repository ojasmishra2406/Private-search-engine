with open("frontend/src/App.jsx", "r", encoding="utf-8") as f:
    content = f.read()

stream_func = """
  // Ref to hold the current EventSource
  const eventSourceRef = React.useRef(null);

  const startRagStream = (searchQuery, role) => {
      if (eventSourceRef.current) {
          eventSourceRef.current.close();
      }
      setRagAnswer('');
      setIsSynthesizing(true);
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
      const eventSource = new EventSource(`${baseUrl}/rag/stream?q=${encodeURIComponent(searchQuery)}&role=${encodeURIComponent(role)}`);
      eventSourceRef.current = eventSource;
      
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
  
  const handleSynthesizeToggle = (e) => {
      const isChecked = e.target.checked;
      setSynthesize(isChecked);
      if (hasSearched && currentQuery) {
          if (isChecked) {
              startRagStream(currentQuery, simulatedRole);
          } else {
              if (eventSourceRef.current) {
                  eventSourceRef.current.close();
              }
              setRagAnswer('');
              setIsSynthesizing(false);
          }
      }
  }

  const handleRoleChange = (e) => {
      const newRole = e.target.value;
      setSimulatedRole(newRole);
      if (hasSearched && currentQuery) {
          performSearch(currentQuery, 0, searchMode, pageSize, newRole);
      }
  }
"""
content = content.replace("  const fetchHealth = async () => {", stream_func + "\n  const fetchHealth = async () => {")

# Update performSearch to use startRagStream and accept role as optional
content = content.replace("const performSearch = async (searchQuery, currentOffset, mode, currentPageSize = pageSize) => {", "const performSearch = async (searchQuery, currentOffset, mode, currentPageSize = pageSize, overrideRole = null) => {\n      const activeRole = overrideRole || simulatedRole;")

# Update params in performSearch
content = content.replace("role: simulatedRole", "role: activeRole")

# Replace inline stream logic
old_stream_logic = """      if (synthesize) {
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
content = content.replace(old_stream_logic, "      if (synthesize) {\n          startRagStream(searchQuery, activeRole);\n      }")

# Replace UI event handlers
content = content.replace("onChange={(e) => setSynthesize(e.target.checked)}", "onChange={handleSynthesizeToggle}")
content = content.replace("onChange={(e) => setSimulatedRole(e.target.value)}", "onChange={handleRoleChange}")


with open("frontend/src/App.jsx", "w", encoding="utf-8") as f:
    f.write(content)
print("Patched RAG toggle")
