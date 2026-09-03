import React from 'react';
import { IconSearch, IconGlobe, IconCode, IconDocument } from './Icons';

const RightPanel = ({ searchMode, handleModeChange, pageSize, handlePageSizeChange, totalResults, timing, healthStats, healthLoading, healthError }) => {

  const methodMap = {
    'lexical': 'BM25',
    'dense': 'Dense',
    'hybrid-rrf': 'Hybrid',
    'hybrid-weighted': 'Hybrid',
    'reranked': 'Reranked'
  };
  const currentMethod = methodMap[searchMode] || 'Unknown';
  
  let docsIndexed = 'N/A';
  let indexStatus = 'Unknown';
  
  if (healthLoading) {
    indexStatus = 'Checking...';
    docsIndexed = '...';
  } else if (healthError) {
    indexStatus = 'Offline';
    docsIndexed = 'N/A';
  } else if (healthStats) {
    indexStatus = healthStats.status === 'ok' ? 'Healthy' : 'Degraded';
    docsIndexed = healthStats.db_doc_count != null ? healthStats.db_doc_count.toLocaleString() : 'N/A';
  }
  const latency = timing?.total != null ? (timing.total * 1000).toFixed(1) + ' ms' : 'N/A';

  return (
    <aside className="right-panel">
      <div className="panel-section">
        <h3 className="panel-heading"><IconSearch /> Search Modes</h3>
        <div className="mode-selector">
          <label className={`mode-option ${searchMode === 'lexical' ? 'active' : ''}`}>
            <input 
              type="radio" 
              name="mode" 
              value="lexical" 
              checked={searchMode === 'lexical'} 
              onChange={handleModeChange} 
            />
            <div className="mode-content">
              <strong>BM25</strong>
              <span>Keyword search</span>
            </div>
          </label>
          <label className={`mode-option ${searchMode === 'dense' ? 'active' : ''}`}>
            <input 
              type="radio" 
              name="mode" 
              value="dense" 
              checked={searchMode === 'dense'} 
              onChange={handleModeChange} 
            />
            <div className="mode-content">
              <strong>Dense</strong>
              <span>Semantic search</span>
            </div>
          </label>
          <label className={`mode-option ${searchMode === 'hybrid-rrf' ? 'active' : ''}`}>
            <input 
              type="radio" 
              name="mode" 
              value="hybrid-rrf" 
              checked={searchMode === 'hybrid-rrf'} 
              onChange={handleModeChange} 
            />
            <div className="mode-content">
              <strong>Hybrid (RRF)</strong>
              <span>Balanced results</span>
            </div>
          </label>
          <label className={`mode-option ${searchMode === 'hybrid-weighted' ? 'active' : ''}`}>
            <input 
              type="radio" 
              name="mode" 
              value="hybrid-weighted" 
              checked={searchMode === 'hybrid-weighted'} 
              onChange={handleModeChange} 
            />
            <div className="mode-content">
              <strong>Hybrid (Weighted)</strong>
              <span>Balanced scoring</span>
            </div>
          </label>
          <label className={`mode-option ${searchMode === 'reranked' ? 'active' : ''}`}>
            <input 
              type="radio" 
              name="mode" 
              value="reranked" 
              checked={searchMode === 'reranked'} 
              onChange={handleModeChange} 
            />
            <div className="mode-content">
              <strong>Reranked</strong>
              <span>Most accurate</span>
            </div>
          </label>
        </div>
      </div>


      <div className="panel-section">
        <h3 className="panel-heading"><IconDocument /> Results per Page</h3>
        <select value={pageSize} onChange={handlePageSizeChange} style={{width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd'}}>
          <option value={10}>10</option>
          <option value={20}>20</option>
          <option value={50}>50</option>
        </select>
      </div>

      <div className="panel-section">
        <h3 className="panel-heading"><IconDocument /> Quick Stats</h3>
        <div className="stats-list">
          <div className="stat-row">
            <span>Index Status</span>
            <strong className={indexStatus === 'Healthy' ? 'status-healthy' : 'status-degraded'}>{indexStatus}</strong>
          </div>
          <div className="stat-row">
            <span>Docs Indexed</span>
            <strong>{docsIndexed}</strong>
          </div>
          <div className="stat-row">
            <span>Sources / Domains</span>
            <strong>N/A</strong>
          </div>
          <div className="stat-row">
            <span>Results Found</span>
            <strong>{totalResults.toLocaleString()}</strong>
          </div>
          <div className="stat-row">
            <span>Search Method</span>
            <strong>{currentMethod}</strong>
          </div>
          <div className="stat-row">
            <span>Search Latency</span>
            <strong>{latency}</strong>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default RightPanel;
