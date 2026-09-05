import React, { useState, useMemo } from 'react';
import { Terminal, Search, Filter, ChevronDown, ChevronRight, CheckCircle2, XCircle, AlertCircle, Info, ShieldCheck } from 'lucide-react';
import { AuditLogEntry } from '../types';

interface AuditTrailViewerProps {
  logs: AuditLogEntry[];
  activePaymentFilter: string | null;
  onSelectPayment: (paymentId: string) => void;
}

export const AuditTrailViewer: React.FC<AuditTrailViewerProps> = ({
  logs,
  activePaymentFilter,
  onSelectPayment,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [stageFilter, setStageFilter] = useState<string>('ALL');
  const [expandedEntryId, setExpandedEntryId] = useState<string | null>(null);

  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      const matchPayment = !activePaymentFilter || log.payment_id === activePaymentFilter;
      const matchStage = stageFilter === 'ALL' || log.stage.toUpperCase() === stageFilter.toUpperCase();
      const matchSearch =
        log.payment_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.stage.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (log.reasoning && log.reasoning.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (log.decision && log.decision.toLowerCase().includes(searchTerm.toLowerCase()));

      return matchPayment && matchStage && matchSearch;
    });
  }, [logs, activePaymentFilter, stageFilter, searchTerm]);

  const getStageBadge = (stage: string) => {
    switch (stage) {
      case 'DETECT': return 'bg-slate-100 text-slate-700 border-slate-200';
      case 'DIAGNOSE': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'RANK': return 'bg-sky-50 text-sky-700 border-sky-200';
      case 'SENTINEL_GATE': return 'bg-amber-50 text-amber-800 border-amber-300 font-bold';
      case 'EXECUTE': return 'bg-indigo-50 text-indigo-700 border-indigo-200';
      case 'OBSERVE': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'FALLBACK': return 'bg-orange-50 text-orange-700 border-orange-200';
      case 'STOP': return 'bg-rose-50 text-rose-700 border-rose-200';
      default: return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'SUCCESS': return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />;
      case 'REJECTED': return <XCircle className="w-3.5 h-3.5 text-rose-600" />;
      case 'FAILED': return <AlertCircle className="w-3.5 h-3.5 text-amber-600" />;
      default: return <Info className="w-3.5 h-3.5 text-slate-500" />;
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm font-sans">
      {/* Header & Filters */}
      <div className="p-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 bg-slate-50">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 bg-blue-50 text-blue-600 rounded-lg">
            <Terminal className="w-4 h-4" />
          </div>
          <div>
            <span className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono">
              Immutable Pipeline Audit Trail
            </span>
            <span className="text-xs text-slate-500 ml-2 font-mono">
              ({filteredLogs.length} events logged)
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
          {activePaymentFilter && (
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-blue-50 border border-blue-200 text-blue-700">
              <span>Filter: {activePaymentFilter}</span>
              <button 
                onClick={() => onSelectPayment('')}
                className="hover:text-blue-900 font-bold ml-1"
              >
                &times;
              </button>
            </div>
          )}

          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search audit trail..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 pr-3 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <select
            value={stageFilter}
            onChange={(e) => setStageFilter(e.target.value)}
            className="bg-white border border-slate-200 text-slate-700 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Stages</option>
            <option value="DETECT">DETECT</option>
            <option value="DIAGNOSE">DIAGNOSE</option>
            <option value="RANK">RANK</option>
            <option value="SENTINEL_GATE">SENTINEL_GATE</option>
            <option value="EXECUTE">EXECUTE</option>
            <option value="OBSERVE">OBSERVE</option>
            <option value="FALLBACK">FALLBACK</option>
            <option value="STOP">STOP</option>
          </select>
        </div>
      </div>

      {/* Events Stream */}
      <div className="overflow-y-auto max-h-[620px] divide-y divide-slate-100 text-xs">
        {filteredLogs.length === 0 ? (
          <div className="p-8 text-center text-slate-400 font-mono">
            No audit events matched your filters.
          </div>
        ) : (
          filteredLogs.map((entry) => {
            const isExpanded = expandedEntryId === entry.entry_id;
            const hasReasoning = Boolean(entry.reasoning);

            return (
              <div 
                key={entry.entry_id}
                className={`p-3 transition-colors ${
                  isExpanded ? 'bg-slate-50' : 'hover:bg-slate-50/60'
                }`}
              >
                <div 
                  onClick={() => setExpandedEntryId(isExpanded ? null : entry.entry_id)}
                  className="flex items-center justify-between cursor-pointer"
                >
                  <div className="flex items-center space-x-3">
                    <button className="text-slate-400 hover:text-slate-700">
                      {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                    </button>

                    <span className="text-slate-400 text-[11px] font-mono">
                      {new Date(entry.timestamp).toLocaleTimeString()}
                    </span>

                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border font-mono ${getStageBadge(entry.stage)}`}>
                      {entry.stage}
                    </span>

                    <span 
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectPayment(entry.payment_id);
                      }}
                      className="font-bold text-indigo-600 hover:text-indigo-800 hover:underline cursor-pointer font-mono"
                    >
                      {entry.payment_id}
                    </span>

                    <span className="text-slate-900 font-medium">
                      {entry.action}
                    </span>

                    {entry.decision && (
                      <span className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 text-slate-700 text-[10px] font-mono rounded">
                        {entry.decision}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-2 font-mono">
                    {getStatusIcon(entry.status)}
                    <span className="text-[11px] text-slate-500 font-semibold">{entry.status}</span>
                  </div>
                </div>

                {/* Structured Human-Readable Reasoning (Change 3: Raw JSON Dump Removed) */}
                {isExpanded && (
                  <div className="mt-3 ml-7 bg-white p-3.5 rounded-xl border border-slate-200 text-xs space-y-2 shadow-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold font-mono text-slate-400 uppercase tracking-wider">
                        Human-Readable Pipeline Reasoning
                      </span>
                      {entry.decision && (
                        <span className="text-[11px] font-mono font-semibold text-indigo-600">
                          Verdict: {entry.decision}
                        </span>
                      )}
                    </div>

                    <p className="text-slate-700 leading-relaxed font-sans">
                      {entry.reasoning || entry.details?.reason || entry.details?.reasoning || 'Standard step execution recorded in audit state log.'}
                    </p>

                    {entry.stage === 'SENTINEL_GATE' && entry.details?.policy_code && (
                      <div className="pt-2 border-t border-slate-100 flex items-center space-x-2 text-[11px] font-mono text-slate-500">
                        <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
                        <span>Policy Code Enforced: <strong>{entry.details.policy_code}</strong></span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
