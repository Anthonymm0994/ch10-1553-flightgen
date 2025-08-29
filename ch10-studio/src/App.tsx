import React, { useState } from 'react';
import { Build } from './pages/Build';

import Tools from './pages/Tools';
import Validation from './pages/Validation';
import { Zap, Radio, Wrench, CheckCircle } from 'lucide-react';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('build');

  const tabs = [
    { id: 'build', label: 'Build', icon: Zap, component: Build },
    
    { id: 'validation', label: 'Validation', icon: CheckCircle, component: Validation },
    { id: 'tools', label: 'Tools', icon: Wrench, component: Tools },
  ];

  const ActiveComponent = tabs.find(t => t.id === activeTab)?.component || Build;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex flex-col">
      {/* Animated background - more subtle */}
      <div className="fixed inset-0 overflow-hidden opacity-30">
        <div className="absolute -top-40 -left-40 w-80 h-80 bg-purple-500/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute -bottom-40 -right-40 w-80 h-80 bg-blue-500/20 rounded-full blur-3xl animate-pulse animation-delay-2000" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse animation-delay-4000" />
      </div>

      {/* Content - flex-col to stack header and main properly */}
      <div className="relative z-10 flex flex-col flex-1">
        {/* Header - Compact */}
        <header className="border-b border-white/10 backdrop-blur-xl bg-black/20 flex-shrink-0">
          <div className="max-w-7xl mx-auto px-4 py-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg">
                  <Zap className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h1 className="text-base font-bold text-white">CH10 Studio</h1>
                  <p className="text-xs text-gray-400">GUI for CH10/1553 Generator</p>
                </div>
              </div>

              {/* Navigation - Compact with spacing */}
              <nav className="flex gap-2">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`
                        px-3 py-1.5 rounded-lg font-medium text-sm
                        transition-all duration-300
                        flex items-center gap-1.5
                        ${activeTab === tab.id
                          ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg shadow-blue-500/20'
                          : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white border border-white/10'
                        }
                      `}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      {tab.label}
                    </button>
                  );
                })}
              </nav>
            </div>
          </div>
        </header>

        {/* Main Content - flex-1 to fill remaining space, overflow-auto for scrolling if needed */}
        <main className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <ActiveComponent />
          </div>
        </main>
      </div>
    </div>
  );
}