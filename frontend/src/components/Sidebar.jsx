import React from 'react';
import { 
  IconSearch, 
  IconGlobe 
} from './Icons';

const Sidebar = ({ activeTab, setActiveTab, healthStats, healthLoading, healthError }) => {

  let statusText = "Checking...";
  let statusClass = "status-dot loading";
  let statusSub = "Connecting to backend";

  if (!healthLoading) {
    if (healthError) {
      statusText = "Offline";
      statusClass = "status-dot error";
      statusSub = "Backend unreachable";
    } else if (healthStats?.status === 'ok') {
      statusText = "Healthy";
      statusClass = "status-dot";
      statusSub = "All systems operational";
    } else {
      statusText = "Degraded";
      statusClass = "status-dot warning";
      statusSub = "Some indexes missing";
    }
  }

  const tabs = [
    { id: 'search', label: 'Search', icon: <IconSearch /> },
    { id: 'crawl', label: 'Web Crawl', icon: <IconGlobe /> }
  ];

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-title">PALLADIAN</div>
        <div className="brand-subtitle">PRIVATE SEARCH</div>
      </div>
      
      <nav className="sidebar-nav">
        {tabs.map(tab => (
          <button 
            key={tab.id}
            className={`nav-item ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="nav-icon">{tab.icon}</span>
            <span className="nav-label">{tab.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="system-status">
          <div className="status-header">
            <span className={statusClass}></span> {statusText}
          </div>
          <div className="status-sub">{statusSub}</div>

        </div>
        <div className="user-profile">
          <div className="avatar">P</div>
          <div className="user-info">
            <div className="user-name">Private User</div>
            <div className="user-email">user@example.com</div>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
