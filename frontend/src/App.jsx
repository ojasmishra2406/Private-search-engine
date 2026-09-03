import React, { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import RightPanel from './components/RightPanel'
import WebCrawlerUI from './components/WebCrawlerUI'
import { IconSearch, IconUser, IconGlobe } from './components/Icons'


function escapeHtml(unsafe) {
  if (typeof unsafe !== 'string') return '';
  return unsafe
       .replace(/&/g, "&amp;")
       .replace(/</g, "&lt;")
       .replace(/>/g, "&gt;")
       .replace(/"/g, "&quot;")
       .replace(/'/g, "&#039;");
}

function highlightSnippet(snippet, matches) {
  if (!snippet) return "";
  let safeSnippet = escapeHtml(snippet);
  if (!matches || matches.length === 0) return safeSnippet;
  
  // We must escape the matches too because the text we are matching against has been escaped
  const escapedMatches = matches.map(t => escapeHtml(t).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const pattern = new RegExp(`(${escapedMatches.join('|')})`, 'gi');
  return safeSnippet.replace(pattern, '<mark>$1</mark>');
}

function getHostname(urlStr) {
  if (!urlStr) return '';
  try {
    return new URL(urlStr).hostname;
  } catch (e) {
    return '';
  }
}

function getSafeHref(urlStr) {
  if (!urlStr) return '#';
  if (urlStr.startsWith('http://') || urlStr.startsWith('https://')) return urlStr;
  if (/^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}(\/.*)?$/.test(urlStr) && !urlStr.match(/\.(py|md|txt|json|csv|js|jsx|ts|tsx)$/i)) {
    return 'https://' + urlStr;
  }
  return '#';
}

function handleLocalClick(e, href) {
  if (href === '#' || href === '') {
    e.preventDefault();
  }
}

function App() {
  const [activeTab, setActiveTab] = useState('search')
  
  const [query, setQuery]           = useState('')
  const [searchMode, setSearchMode] = useState('hybrid-weighted')
  const [pageSize, setPageSize]       = useState(20)
  const [results, setResults]       = useState([])
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState(null)
  const [total, setTotal]           = useState(0)
  const [offset, setOffset]         = useState(0)
  const [currentQuery, setCurrentQuery] = useState('') 
  const [hasSearched, setHasSearched]   = useState(false)
  const [timing, setTiming]         = useState(null)

  const [crawlUrl, setCrawlUrl] = useState('')
  const [crawlMaxPages, setCrawlMaxPages] = useState(20)
  const [crawlMaxDepth, setCrawlMaxDepth] = useState(1)
  const [crawlSameDomain, setCrawlSameDomain] = useState(true)
  const [crawling, setCrawling] = useState(false)

  const [crawlStatus, setCrawlStatus] = useState(null)
  const [healthStats, setHealthStats] = useState(null)
  const [healthLoading, setHealthLoading] = useState(true)
  const [healthError, setHealthError] = useState(null)

  const fetchHealth = async () => {
    setHealthLoading(true)
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${baseUrl}/health`);
      if (res.ok) {
        const data = await res.json();
        setHealthStats(data);
        setHealthError(null);
      } else {
        setHealthError("Failed to fetch");
      }
    } catch(e) {
       console.error("Failed to fetch health stats", e);
       setHealthError(e.message);
    } finally {
      setHealthLoading(false);
    }
  }

  useEffect(() => {
    fetchHealth();
  }, [])


  const performCrawl = async () => {
    if (!crawlUrl.trim()) return;
    setCrawling(true);
    setCrawlStatus(null);
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${baseUrl}/crawl`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: crawlUrl,
          max_pages: parseInt(crawlMaxPages),
          max_depth: parseInt(crawlMaxDepth),
          same_domain_only: crawlSameDomain
        })
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Crawl failed");
      }
      const data = await res.json();
      setCrawlStatus(`Crawled ${data.pages_crawled} pages successfully. Search index updated.`);
    } catch (err) {
      setCrawlStatus(`Crawl failed: ${err.message}`);
    } finally {
      setCrawling(false);
    }
  }

  const performSearch = async (searchQuery, currentOffset, mode, currentPageSize = pageSize) => {
    if (!searchQuery.trim()) return
    setLoading(true)
    setError(null)
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
      let endpoint = `${baseUrl}/search`
      let params = new URLSearchParams({
          q: searchQuery,
          top_k: currentPageSize,
          offset: currentOffset
      })

      if (mode === 'dense') {
          endpoint = `${baseUrl}/dense-search`
      } else if (mode.startsWith('hybrid')) {
          endpoint = `${baseUrl}/hybrid-search`
          const method = mode.split('-')[1] // 'rrf' or 'weighted'
          params.append('method', method)
          if (method === 'weighted') params.append('alpha', '0.40')
      } else if (mode === 'reranked') {
          endpoint = `${baseUrl}/reranked-search`
          params.append('method', 'weighted')
          params.append('alpha', '0.40')
      }

      const res = await fetch(`${endpoint}?${params.toString()}`)
      if (!res.ok) {
        const text = await res.text()
        throw new Error(text || "Search failed")
      }
      
      const data = await res.json()
      setResults(data.results || [])
      setTotal(data.total_results || 0)
      setOffset(currentOffset)
      setCurrentQuery(searchQuery)
      setHasSearched(true)
      setTiming(data.timing || null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e) => {
    e.preventDefault()
    performSearch(query, 0, searchMode)
  }

  const handleModeChange = (e) => {
    const newMode = e.target.value;
    setSearchMode(newMode);
    if (hasSearched) {
      performSearch(currentQuery, 0, newMode, pageSize);
    }
  }

  const handlePageSizeChange = (e) => {
    const newSize = parseInt(e.target.value);
    setPageSize(newSize);
    if (hasSearched) {
      performSearch(currentQuery, 0, searchMode, newSize);
    }
  }

  const handlePrev = () => {
    const newOffset = Math.max(0, offset - pageSize)
    performSearch(currentQuery, newOffset, searchMode)
  }

  const handleNext = () => {
    const newOffset = offset + pageSize
    if (newOffset < total) {
      performSearch(currentQuery, newOffset, searchMode)
    }
  }

  const currentPage = Math.floor(offset / pageSize) + 1
  const totalPages  = Math.ceil(total / pageSize)

  return (
    <div className="app-layout">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} healthStats={healthStats} healthLoading={healthLoading} healthError={healthError} />
      
      <main className="main-content">
        {activeTab === 'search' && (
          <div className="search-view">
            <header className="search-header">
              <h1>Search your knowledge base</h1>
              <p className="subtitle">Fast, relevant, and intelligent search across all your documents.</p>
              
              <form onSubmit={handleSearch} className="search-box-form">
                <div className="search-input-wrapper">
                  <span className="search-icon"><IconSearch /></span>
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search for anything..."
                    autoFocus
                  />
                  <span className="shortcut-key">/</span>
                  <button type="submit" className="search-submit" disabled={loading}>
                    {loading ? '...' : 'Search'}
                  </button>
                </div>
              </form>
              
              <div className="filters-bar">
                <button className="filter-tab active"><IconUser /> All</button>
                {/* Note: Documents, Web Pages, Code, and Filters buttons were removed because the backend API 
                    only supports 'domain' filtering, making those category filters purely decorative/fake. */}
              </div>
            </header>

            <div className="results-area">
              {error && <div className="error-banner">{error}</div>}

              {hasSearched && !error && (
                <div className="results-header">
                  <h2>Top Results</h2>
                  <span className="meta">
                    {total.toLocaleString()} results 
                    {timing && timing.total ? ` (${(timing.total).toFixed(2)}s)` : ''}
                  </span>
                </div>
              )}

              <div className="results-list">
                {results.map((res, i) => (
                  <div key={`${res.doc_id}-${i}`} className="result-card">
                    <div className="card-meta">
                      <IconGlobe /> {getHostname(res.url) || 'document'}
                    </div>
                    <h3>
                      <a 
                        href={getSafeHref(res.url)} 
                        target={getSafeHref(res.url) !== '#' ? "_blank" : "_self"} 
                        rel="noopener noreferrer"
                        onClick={(e) => handleLocalClick(e, getSafeHref(res.url))}
                      >
                        {res.title || 'Untitled Document'}
                      </a>
                    </h3>
                    <div
                      className="result-snippet"
                      dangerouslySetInnerHTML={{
                        __html: highlightSnippet(res.snippet, res.matches)
                      }}
                    />
                    <div className="card-footer">
                      <div className="tags">
                        <span className="tag">Document</span>
                      </div>
                      <div className="score">
                        <strong>{(res.score * 100).toFixed(1)}</strong>
                        <span>score</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {hasSearched && total > pageSize && (
                <div className="pagination">
                  <button onClick={handlePrev} disabled={offset === 0 || loading}>
                    &larr; Previous
                  </button>
                  <span className="page-info">Page {currentPage} of {totalPages || 1}</span>
                  <button onClick={handleNext} disabled={offset + pageSize >= total || loading}>
                    Next &rarr;
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'crawl' && (
          <WebCrawlerUI 
            crawlUrl={crawlUrl}
            setCrawlUrl={setCrawlUrl}
            crawlMaxPages={crawlMaxPages}
            setCrawlMaxPages={setCrawlMaxPages}
            crawlMaxDepth={crawlMaxDepth}
            setCrawlMaxDepth={setCrawlMaxDepth}
            crawlSameDomain={crawlSameDomain}
            setCrawlSameDomain={setCrawlSameDomain}
            crawling={crawling}
            crawlStatus={crawlStatus}
            performCrawl={performCrawl}
          />
        )}
      </main>

      <RightPanel 
        searchMode={searchMode} 
        handleModeChange={handleModeChange} 
        pageSize={pageSize}
        handlePageSizeChange={handlePageSizeChange}
        totalResults={total}
        timing={timing}
        healthStats={healthStats}
        healthLoading={healthLoading}
        healthError={healthError}
      />
    </div>
  )
}

export default App
