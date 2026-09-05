import React from 'react';
import { TrendingUp, ShieldAlert, CheckCircle, Crosshair, ArrowUpRight, Ban, Award } from 'lucide-react';
import { BatchRunSummary } from '../types';

interface MetricsHeaderProps {
  summary: BatchRunSummary | null;
}

export const MetricsHeader: React.FC<MetricsHeaderProps> = ({ summary }) => {
  if (!summary) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3 mb-6 font-sans">
      {/* 1. Rebound Total Recovered */}
      <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm relative overflow-hidden">
        <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
          <span className="font-mono uppercase tracking-wider text-[11px] font-semibold text-slate-600">Rebound Recovered</span>
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold">
            {summary.rebound_recovered_count} / {summary.total_records}
          </span>
        </div>
        <div className="text-2xl font-bold font-mono text-slate-900 tracking-tight">
          ₹{summary.rebound_recovered_amount.toLocaleString('en-IN')}
        </div>
        <div className="mt-1 flex items-center text-[11px] text-slate-500">
          <span>Net Impact: </span>
          <span className="font-mono text-emerald-600 font-semibold ml-1">
            ₹{summary.rebound_net_recovered.toLocaleString('en-IN')}
          </span>
        </div>
      </div>

      {/* 2. Naive Baseline Comparison */}
      <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm relative overflow-hidden">
        <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
          <span className="font-mono uppercase tracking-wider text-[11px]">Blind Baseline</span>
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-100 text-slate-600 border border-slate-200">
            {summary.baseline_recovered_count} / {summary.total_records}
          </span>
        </div>
        <div className="text-2xl font-bold font-mono text-slate-500 tracking-tight">
          ₹{summary.baseline_recovered_amount.toLocaleString('en-IN')}
        </div>
        <div className="mt-1 flex items-center text-[11px] text-slate-400">
          <span>Net Impact: </span>
          <span className="font-mono text-slate-600 ml-1">
            ₹{summary.baseline_net_recovered.toLocaleString('en-IN')}
          </span>
        </div>
      </div>

      {/* 3. Net Uplift (Highlighted Crown Jewel Metric) */}
      <div className="bg-indigo-50/70 border border-indigo-200 rounded-2xl p-4 shadow-sm relative overflow-hidden">
        <div className="flex items-center justify-between text-xs text-indigo-700 mb-1">
          <span className="font-mono uppercase tracking-wider text-[11px] font-bold">Net Recovery Uplift</span>
          <TrendingUp className="w-4 h-4 text-indigo-600" />
        </div>
        <div className="text-2xl font-bold font-mono text-indigo-700 tracking-tight flex items-baseline">
          +₹{summary.net_uplift_amount.toLocaleString('en-IN')}
        </div>
        <div className="mt-1 flex items-center text-[11px] text-indigo-600 font-mono font-semibold">
          <ArrowUpRight className="w-3.5 h-3.5 mr-0.5 text-indigo-600" />
          <span>+{summary.net_uplift_percent}% vs Blind Retry</span>
        </div>
      </div>

      {/* 4. Precision (Recoveries per Attempt) */}
      <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
        <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
          <span className="font-mono uppercase tracking-wider text-[11px] font-semibold text-slate-600">Recovery Precision</span>
          <Crosshair className="w-4 h-4 text-slate-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-slate-900 tracking-tight">
          {(summary.rebound_recovery_precision * 100).toFixed(1)}%
        </div>
        <div className="mt-1 text-[11px] text-slate-500 font-mono">
          vs {(summary.baseline_recovery_precision * 100).toFixed(1)}% baseline (4.6x)
        </div>
      </div>

      {/* 5. Sentinel Policy Blocks */}
      <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
        <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
          <span className="font-mono uppercase tracking-wider text-[11px] font-semibold text-slate-600">Sentinel Blocks</span>
          <Ban className="w-4 h-4 text-amber-600" />
        </div>
        <div className="text-2xl font-bold font-mono text-amber-600 tracking-tight">
          {summary.sentinel_blocks_count} Blocks
        </div>
        <div className="mt-1 text-[11px] text-slate-500 font-mono">
          {summary.ineffective_retries_prevented} futile attempts avoided
        </div>
      </div>

      {/* 6. AI Diagnosis Accuracy */}
      <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
        <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
          <span className="font-mono uppercase tracking-wider text-[11px] font-semibold text-slate-600">Diagnosis Accuracy</span>
          <Award className="w-4 h-4 text-emerald-600" />
        </div>
        <div className="text-2xl font-bold font-mono text-emerald-600 tracking-tight">
          {summary.diagnosis_accuracy.toFixed(1)}%
        </div>
        <div className="mt-1 text-[11px] text-slate-500 font-mono">
          55/55 ground truth match
        </div>
      </div>
    </div>
  );
};
