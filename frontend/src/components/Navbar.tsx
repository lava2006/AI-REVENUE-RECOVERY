import React, { useState, useRef, useEffect } from 'react';
import { 
  ShieldCheck, 
  Cpu, 
  Sliders, 
  LogOut, 
  Layers, 
  BarChart3, 
  Terminal, 
  Award, 
  Bot, 
  ChevronDown 
} from 'lucide-react';

interface NavbarProps {
  activeTab: 'queue' | 'benchmark' | 'decision-card' | 'audit-trail' | 'eval-report' | 'buyer-agent';
  setActiveTab: (tab: 'queue' | 'benchmark' | 'decision-card' | 'audit-trail' | 'eval-report' | 'buyer-agent') => void;
  onOpenArchitecture: () => void;
  onOpenPolicy: () => void;
  onRefreshBatch: () => void;
  onLogout: () => void;
  merchantName: string;
  isBatchRunning: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  onOpenArchitecture,
  onOpenPolicy,
  onRefreshBatch,
  onLogout,
  merchantName,
  isBatchRunning,
}) => {
  const [isMoreOpen, setIsMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (moreRef.current && !moreRef.current.contains(event.target as Node)) {
        setIsMoreOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const isMoreActive = activeTab === 'benchmark' || activeTab === 'eval-report';

  return (
    <header className="border-b border-slate-200 bg-white/95 backdrop-blur sticky top-0 z-40 px-6 py-3 shadow-sm">
      <div className="flex items-center justify-between">
        {/* Left: Branding & Exactly One Short Status Pill */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center font-bold text-white shadow-md">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold tracking-tight text-slate-900 text-base font-mono">
                  REBOUND
                </span>
                <span className="px-1.5 py-0.5 text-[10px] font-mono font-semibold bg-blue-50 text-blue-700 border border-blue-200 rounded">
                  TRACK 3 · RAZORPAY
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-mono">Autonomous Revenue Recovery</p>
            </div>
          </div>

          <div className="hidden lg:flex items-center space-x-2 pl-4 border-l border-slate-200">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-[11px] font-mono text-emerald-700 font-semibold tracking-wide">
              Sentinel: Rules-Only
            </span>
          </div>
        </div>

        {/* Center: Prioritized Primary Tabs + More Dropdown */}
        <nav className="flex items-center space-x-1 bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs font-medium">
          <button
            onClick={() => setActiveTab('queue')}
            className={`px-3.5 py-1.5 rounded-lg transition-all flex items-center space-x-1.5 ${
              activeTab === 'queue'
                ? 'bg-white text-blue-700 shadow-sm font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Triage Queue</span>
          </button>

          <button
            onClick={() => setActiveTab('audit-trail')}
            className={`px-3.5 py-1.5 rounded-lg transition-all flex items-center space-x-1.5 ${
              activeTab === 'audit-trail'
                ? 'bg-white text-blue-700 shadow-sm font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>Audit Trail</span>
          </button>

          <button
            onClick={() => setActiveTab('buyer-agent')}
            className={`px-3.5 py-1.5 rounded-lg transition-all flex items-center space-x-1.5 ${
              activeTab === 'buyer-agent'
                ? 'bg-white text-blue-700 shadow-sm font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Bot className="w-3.5 h-3.5 text-blue-600" />
            <span>Sentinel Reuse Demo</span>
          </button>

          {/* More Dropdown */}
          <div className="relative" ref={moreRef}>
            <button
              onClick={() => setIsMoreOpen(!isMoreOpen)}
              className={`px-3 py-1.5 rounded-lg transition-all flex items-center space-x-1 ${
                isMoreActive || isMoreOpen
                  ? 'bg-white text-blue-700 shadow-sm font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span>More</span>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${isMoreOpen ? 'rotate-180' : ''}`} />
            </button>

            {isMoreOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-white border border-slate-200 rounded-2xl shadow-xl py-2 z-50 text-xs">
                <div className="px-3 py-1 text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">
                  Analytics & Reports
                </div>
                <button
                  onClick={() => {
                    setActiveTab('benchmark');
                    setIsMoreOpen(false);
                  }}
                  className={`w-full px-3 py-2 text-left flex items-center space-x-2.5 transition-colors ${
                    activeTab === 'benchmark' ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <BarChart3 className="w-4 h-4 text-slate-500" />
                  <span>55-Record Benchmark</span>
                </button>

                <button
                  onClick={() => {
                    setActiveTab('eval-report');
                    setIsMoreOpen(false);
                  }}
                  className={`w-full px-3 py-2 text-left flex items-center space-x-2.5 transition-colors ${
                    activeTab === 'eval-report' ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <Award className="w-4 h-4 text-slate-500" />
                  <span>FAQ &amp; Calibration</span>
                </button>

                <div className="my-1.5 border-t border-slate-100" />

                <div className="px-3 py-1 text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">
                  Governance &amp; Blueprint
                </div>
                <button
                  onClick={() => {
                    onOpenPolicy();
                    setIsMoreOpen(false);
                  }}
                  className="w-full px-3 py-2 text-left flex items-center space-x-2.5 text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  <Sliders className="w-4 h-4 text-slate-500" />
                  <span>Policy Rules</span>
                </button>

                <button
                  onClick={() => {
                    onOpenArchitecture();
                    setIsMoreOpen(false);
                  }}
                  className="w-full px-3 py-2 text-left flex items-center space-x-2.5 text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  <Cpu className="w-4 h-4 text-slate-500" />
                  <span>Architecture</span>
                </button>
              </div>
            )}
          </div>
        </nav>

        {/* Right: Merchant Account & Logout */}
        <div className="flex items-center space-x-3">
          <button
            onClick={onOpenPolicy}
            className="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 text-xs text-slate-700 font-medium transition-colors"
            title="Configure dynamic policy rules & merchant catalog"
          >
            <Sliders className="w-3.5 h-3.5 text-slate-600" />
            <span>Policy Rules</span>
          </button>

          <div className="flex items-center space-x-2 pl-2 border-l border-slate-200">
            <div className="text-right hidden sm:block">
              <span className="block text-xs font-semibold text-slate-900">{merchantName}</span>
              <span className="block text-[10px] font-mono text-emerald-600">Enterprise Merchant</span>
            </div>
            <button
              onClick={onLogout}
              className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
