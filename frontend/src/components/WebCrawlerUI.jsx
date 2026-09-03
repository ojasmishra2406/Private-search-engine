import React from 'react';
import { IconGlobe } from './Icons';

const WebCrawlerUI = ({
  crawlUrl, setCrawlUrl,
  crawlMaxPages, setCrawlMaxPages,
  crawlMaxDepth, setCrawlMaxDepth,
  crawlSameDomain, setCrawlSameDomain,
  crawling, crawlStatus, performCrawl
}) => {

  const handleSubmit = (e) => {
    e.preventDefault();
    performCrawl();
  };

  return (
    <div className="crawler-container">
      <div className="crawler-header">
        <h2><IconGlobe /> Web Crawl</h2>
        <p>Ingest real web pages directly into your private index.</p>
      </div>
      
      <form onSubmit={handleSubmit} className="crawler-form">
        <div className="form-group">
          <label>Target URL</label>
          <input 
            type="url" 
            placeholder="https://example.com" 
            value={crawlUrl}
            onChange={(e) => setCrawlUrl(e.target.value)}
            required
          />
        </div>
        
        <div className="form-row">
          <div className="form-group">
            <label>Max Pages</label>
            <input 
              type="number" 
              min="1"
              value={crawlMaxPages}
              onChange={(e) => setCrawlMaxPages(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Max Depth</label>
            <input 
              type="number" 
              min="1"
              value={crawlMaxDepth}
              onChange={(e) => setCrawlMaxDepth(e.target.value)}
            />
          </div>
        </div>
        
        <div className="form-group checkbox-group">
          <label>
            <input 
              type="checkbox" 
              checked={crawlSameDomain}
              onChange={(e) => setCrawlSameDomain(e.target.checked)}
            />
            <span>Restrict to same domain</span>
          </label>
        </div>
        
        <button type="submit" className="btn-primary" disabled={crawling || !crawlUrl.trim()}>
          {crawling ? 'Crawling...' : 'Start Crawl'}
        </button>
      </form>

      {crawlStatus && (
        <div className={`crawler-status ${crawlStatus.includes('failed') ? 'error' : 'success'}`}>
          {crawlStatus}
        </div>
      )}
    </div>
  );
};

export default WebCrawlerUI;
