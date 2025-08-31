import React, { useState } from 'react';
import { Build } from './pages/Build';
import Tools from './pages/Tools';
import Validation from './pages/Validation';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('build');

  const tabs = [
    { id: 'build', label: 'Build', component: Build },
    { id: 'validation', label: 'Validation', component: Validation },
    { id: 'tools', label: 'Tools', component: Tools },
  ];

  const ActiveComponent = tabs.find(t => t.id === activeTab)?.component || Build;

  return (
    <div style={{ 
      minHeight: '100vh',
      background: '#0a0a0a',
      color: '#ffffff'
    }}>
      {/* Header */}
      <div style={{
        background: '#1a1a1a',
        borderBottom: '1px solid #333',
        padding: '16px 32px'
      }}>
        <div style={{ 
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          maxWidth: '1200px',
          margin: '0 auto'
        }}>
          <div>
            <h1 style={{ 
              fontSize: '20px',
              fontWeight: '600',
              margin: 0
            }}>
              CH10 Studio
            </h1>
            <p style={{ 
              fontSize: '12px',
              color: '#666',
              margin: '4px 0 0 0'
            }}>
              CH10/1553 File Generator
            </p>
          </div>

          {/* Navigation */}
          <nav style={{ display: 'flex', gap: '4px' }}>
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  padding: '8px 16px',
                  background: activeTab === tab.id ? '#0066cc' : 'transparent',
                  border: 'none',
                  borderRadius: '4px',
                  color: activeTab === tab.id ? '#fff' : '#999',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '500'
                }}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main>
        <ActiveComponent />
      </main>
    </div>
  );
}