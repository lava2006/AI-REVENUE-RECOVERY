import React from 'react';
import { X, ShieldCheck, Cpu, Database, CreditCard, ArrowRight, CheckCircle2 } from 'lucide-react';

interface ArchitectureModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ArchitectureModal: React.FC<ArchitectureModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm font-sans">
      <div className="bg-white border border-slate-200 rounded-3xl w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-2xl p-6 text-slate-800">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div>
            <span className="text-[10px] font-mono text-blue-600 font-bold uppercase tracking-widest">Architectural Blueprint</span>
            <h3 className="text-lg font-bold text-slate-900 tracking-tight">The AI / Deterministic Boundary & The Sentinel</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="py-6 space-y-6">
          {/* Prime Directive Banner */}
          <div className="bg-blue-50/70 border border-blue-200 rounded-2xl p-4">
            <div className="text-xs font-mono font-bold text-blue-700 uppercase tracking-wider mb-1">
              Prime Directive
            </div>
            <p className="text-xs text-blue-950 leading-relaxed font-mono">
              "Diagnose why one specific kind of payment failed, rank the known recovery playbook by expected value, and let a deterministic, standalone gate — the Sentinel — be the only thing that ever touches money."
            </p>
          </div>

          {/* 8-Stage Pipeline Diagram */}
          <div>
            <div className="text-xs font-mono font-bold text-slate-500 uppercase tracking-wider mb-3">
              The 8-Stage Recovery Pipeline
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 text-xs font-mono">
              <div className="bg-slate-50 border border-slate-200 p-3 rounded-xl">
                <span className="text-blue-600 font-bold block mb-1">1. DETECT</span>
                <p className="text-slate-500 text-[11px]">Capture decline code, raw gateway signal, customer tenure & retry state.</p>
              </div>
              <div className="bg-blue-50/50 border border-blue-200 p-3 rounded-xl">
                <span className="text-blue-700 font-bold block mb-1">2. DIAGNOSE [AI]</span>
                <p className="text-slate-600 text-[11px]">Classify cause + confidence score across the 5 canonical failure types.</p>
              </div>
              <div className="bg-blue-50/50 border border-blue-200 p-3 rounded-xl">
                <span className="text-blue-700 font-bold block mb-1">3. RANK [AI]</span>
                <p className="text-slate-600 text-[11px]">Score fixed 5-action playbook with Expected Value (₹) = (P*Amt) - Cost.</p>
              </div>
              <div className="bg-amber-50 border border-amber-300 p-3 rounded-xl shadow-sm">
                <span className="text-amber-800 font-bold block mb-1">4. GATE [Sentinel]</span>
                <p className="text-amber-900 text-[11px]">Pure deterministic rules engine: Bounds, Cooldown, Retries, EV & Risk.</p>
              </div>

              <div className="bg-slate-50 border border-slate-200 p-3 rounded-xl">
                <span className="text-blue-600 font-bold block mb-1">5. EXECUTE</span>
                <p className="text-slate-500 text-[11px]">Razorpay Test API or Test Simulator. Never bypassed by AI.</p>
              </div>
              <div className="bg-slate-50 border border-slate-200 p-3 rounded-xl">
                <span className="text-blue-600 font-bold block mb-1">6. OBSERVE & FALLBACK</span>
                <p className="text-slate-500 text-[11px]">If rejected or failed, gracefully step down to candidate #2, stopping cleanly.</p>
              </div>
              <div className="bg-slate-50 border border-slate-200 p-3 rounded-xl">
                <span className="text-blue-600 font-bold block mb-1">7. AUDIT TRAIL</span>
                <p className="text-slate-500 text-[11px]">Append-only state log tracking every candidate, verdict, and timestamp.</p>
              </div>
              <div className="bg-slate-50 border border-slate-200 p-3 rounded-xl">
                <span className="text-blue-600 font-bold block mb-1">8. REPORT</span>
                <p className="text-slate-500 text-[11px]">Rebound vs Baseline comparison, precision, uplift and counterfactual EV.</p>
              </div>
            </div>
          </div>

          {/* AI vs Deterministic Split Table */}
          <div>
            <div className="text-xs font-mono font-bold text-slate-500 uppercase tracking-wider mb-3">
              Strict Component Responsibility Boundary
            </div>
            <div className="border border-slate-200 rounded-xl overflow-hidden text-xs">
              <table className="w-full text-left font-mono">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 text-[11px]">
                  <tr>
                    <th className="p-3">Component</th>
                    <th className="p-3">Engine Type</th>
                    <th className="p-3">Allowed Actions</th>
                    <th className="p-3">Forbidden Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr className="bg-white">
                    <td className="p-3 font-bold text-slate-900">Diagnosis Engine</td>
                    <td className="p-3 text-blue-600 font-semibold">LLM + Semantic Fallback</td>
                    <td className="p-3 text-slate-600">Classify error string into 5 causes + confidence</td>
                    <td className="p-3 text-rose-600">Directly calling APIs or moving money</td>
                  </tr>
                  <tr className="bg-white">
                    <td className="p-3 font-bold text-slate-900">Ranking Engine</td>
                    <td className="p-3 text-blue-600 font-semibold">Playbook Ranker (EV Formula)</td>
                    <td className="p-3 text-slate-600">Rank fixed 5 actions with (P*Amt) - Cost</td>
                    <td className="p-3 text-rose-600">Inventing novel unreviewed action types</td>
                  </tr>
                  <tr className="bg-amber-50/50">
                    <td className="p-3 font-bold text-amber-900">The Sentinel</td>
                    <td className="p-3 text-amber-700 font-bold">100% Deterministic Python</td>
                    <td className="p-3 text-amber-900">Evaluate retries, cooldown, min EV, amount bounds</td>
                    <td className="p-3 text-rose-600">Using LLMs or prompt heuristics (0 LLM Calls)</td>
                  </tr>
                  <tr className="bg-white">
                    <td className="p-3 font-bold text-slate-900">Razorpay Executor</td>
                    <td className="p-3 text-slate-600">Test API / Simulator Stub</td>
                    <td className="p-3 text-slate-600">Execute Sentinel-approved recovery actions</td>
                    <td className="p-3 text-rose-600">Executing unapproved AI recommendations</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Architectural Proof: Zero-Code Reuse Section */}
          <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 space-y-3">
            <div className="flex items-center space-x-2">
              <ShieldCheck className="w-5 h-5 text-emerald-600 flex-shrink-0" />
              <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900">
                Architectural Proof: Zero Code Changes in Sentinel for Buyer Agent Reuse
              </h4>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed font-sans">
              The exact same deterministic Sentinel gating engine evaluates autonomous purchases using the identical policy-rule architecture. Both recovery actions and autonomous buyer agent commerce pass through the same pure Python rule validator: bounds checks, budget limits, catalog matches, permission scope, and cooldown enforcement.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 text-xs font-mono">
              <div className="bg-white border border-slate-200 rounded-xl p-3 space-y-1.5">
                <span className="text-blue-600 font-bold block">1. Revenue Recovery Flow</span>
                <p className="text-slate-500 text-[11px]">
                  Failed Payment &rarr; AI Diagnosis &rarr; Candidate EV Ranking &rarr; <strong>Sentinel Gate</strong> &rarr; Razorpay Recovery API
                </p>
                <div className="text-[10px] text-slate-400">Rules: Max retries, cooldown, positive EV, amount ceiling.</div>
              </div>
              <div className="bg-white border border-slate-200 rounded-xl p-3 space-y-1.5">
                <span className="text-emerald-600 font-bold block">2. Autonomous Buyer Agent Flow</span>
                <p className="text-slate-500 text-[11px]">
                  Agent Intent &rarr; Catalog Search &rarr; Purchase Request &rarr; <strong>Same Sentinel Gate</strong> &rarr; Razorpay Order Execution
                </p>
                <div className="text-[10px] text-slate-400">Rules: SKU catalog match, price ceiling, monthly budget, scope permissions.</div>
              </div>
            </div>
            <div className="text-[11px] font-mono text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-xl px-3 py-2 flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>Zero LLM calls in the money path across both modes. Gating is 100% deterministic and auditable.</span>
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-slate-100 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold"
          >
            Close Blueprint
          </button>
        </div>
      </div>
    </div>
  );
};
