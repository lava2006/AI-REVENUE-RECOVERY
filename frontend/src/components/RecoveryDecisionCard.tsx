import React, { useState } from 'react';
import { 
  ShieldCheck, 
  ShieldAlert, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Clock, 
  CreditCard, 
  Layers, 
  ExternalLink,
  Cpu,
  ArrowRight,
  TrendingUp,
  FileText,
  Building2,
  Lock,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Info
} from 'lucide-react';
import { RecoveryDecisionCardData, FailureCause, RecoveryAction } from '../types';

interface RecoveryDecisionCardProps {
  card: RecoveryDecisionCardData | null;
  onSelectPaymentForAudit?: (paymentId: string) => void;
}

export const RecoveryDecisionCard: React.FC<RecoveryDecisionCardProps> = ({ card, onSelectPaymentForAudit }) => {
  const [showAllCandidates, setShowAllCandidates] = useState<boolean>(false);

  if (!card) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center text-slate-400">
        <Cpu className="w-10 h-10 mx-auto text-indigo-400 mb-3 animate-pulse" />
        <p className="text-sm font-semibold text-slate-700">No Payment Selected</p>
        <p className="text-xs text-slate-500 mt-1 font-mono">Select a payment from the queue or benchmark table to inspect its Decision Card.</p>
      </div>
    );
  }

  const { payment, diagnosis, ranked_candidates, final_sentinel_decision, fallback_steps, final_outcome, counterfactual_paths, recovered, net_revenue_impact, advisory_note } = card;

  const getCauseBadge = (cause: FailureCause) => {
    switch (cause) {
      case 'INSUFFICIENT_FUNDS':
        return <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-amber-50 text-amber-700 border border-amber-200">INSUFFICIENT_FUNDS</span>;
      case 'CARD_EXPIRED':
        return <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-orange-50 text-orange-700 border border-orange-200">CARD_EXPIRED</span>;
      case 'ISSUER_DECLINE':
        return <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-blue-50 text-blue-700 border border-blue-200">ISSUER_DECLINE</span>;
      case 'BANK_DOWNTIME':
        return <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-sky-50 text-sky-700 border border-sky-200">BANK_DOWNTIME</span>;
      case 'RISK_BLOCK':
        return <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-rose-50 text-rose-700 border border-rose-200">RISK_BLOCK</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-xs font-mono text-slate-600 border border-slate-200">{cause}</span>;
    }
  };

  const getActionLabel = (action: RecoveryAction) => {
    switch (action) {
      case 'RETRY_NOW': return 'Immediate Smart Retry';
      case 'RETRY_LATER': return 'Scheduled Cooldown Retry';
      case 'NOTIFY_CUSTOMER': return 'Multi-Channel Dunning Alert';
      case 'OFFER_ALTERNATE_PAYMENT_METHOD': return 'Alternate Payment Rail (UPI/eNACH)';
      case 'PROMPT_CARD_UPDATE': return 'Card Token Renewal Prompt';
      default: return action;
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden font-sans">
      {/* 1. CARD TOP BANNER / TELEMETRY HEADER */}
      <div className="bg-slate-50 border-b border-slate-200 px-6 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-mono font-bold text-base shadow-sm">
              ₹
            </div>
            <div>
              <div className="flex items-center space-x-2.5">
                <span className="font-mono text-base font-bold text-slate-900 tracking-tight">{payment.payment_id}</span>
                <span className="text-xs text-slate-400 font-mono">({payment.subscription_id})</span>
                <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
                  {payment.customer_tier} Tier
                </span>
                {card.is_borderline && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                    Borderline Triage
                  </span>
                )}
              </div>
              <div className="flex items-center space-x-3 text-xs text-slate-500 mt-0.5">
                <span className="font-semibold text-slate-800">{payment.customer_name}</span>
                <span>•</span>
                <span>Tenure: {payment.tenure_months} mos</span>
                <span>•</span>
                <span>Prior Retries: {payment.past_failed_retries}</span>
                <span>•</span>
                <span>Dunning Count: {payment.dunning_attempts}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="text-right">
              <div className="text-[11px] text-slate-400 font-mono uppercase tracking-wider">Amount Due</div>
              <div className="text-xl font-bold font-mono text-slate-900">
                ₹{payment.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
            </div>

            <div className={`px-3 py-1.5 rounded-xl border text-xs font-mono font-bold flex items-center space-x-1.5 ${
              recovered 
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                : 'bg-rose-50 text-rose-700 border-rose-200'
            }`}>
              {recovered ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <XCircle className="w-4 h-4 text-rose-600" />}
              <span>{recovered ? 'RECOVERED' : 'UNRECOVERED'}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* 2. STAGE 1 & 2: INGESTION SIGNAL & AI ROOT-CAUSE DIAGNOSIS */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Signal Ingestion */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex items-center justify-between text-xs font-mono text-slate-500">
              <span className="uppercase tracking-wider font-semibold">Stage 1 · Ingestion Signal</span>
              <span className="text-slate-400">{new Date(payment.timestamp).toLocaleTimeString()}</span>
            </div>
            <div className="space-y-1">
              <div className="text-xs font-mono text-slate-800 font-bold flex items-center space-x-2">
                <span>Code:</span>
                <span className="text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200 text-[11px]">
                  {payment.decline_code}
                </span>
              </div>
              <div className="text-xs text-slate-600 italic bg-white p-2 rounded-lg border border-slate-200">
                "{payment.raw_signal}"
              </div>
            </div>
          </div>

          {/* AI Root-Cause Classification */}
          <div className="p-4 rounded-xl bg-indigo-50/50 border border-indigo-100 space-y-2">
            <div className="flex items-center justify-between text-xs font-mono text-indigo-600">
              <span className="uppercase tracking-wider font-bold flex items-center space-x-1">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Stage 2 · AI Root-Cause Diagnosis</span>
              </span>
              <span className="px-2 py-0.5 bg-indigo-100 text-indigo-800 text-[11px] font-bold rounded">
                {(diagnosis.confidence * 100).toFixed(0)}% Confidence
              </span>
            </div>

            <div className="flex items-center space-x-2 pt-1">
              {getCauseBadge(diagnosis.cause)}
              <span className="text-xs text-slate-500 font-mono">Ground truth verified</span>
            </div>

            <p className="text-xs text-slate-700 leading-relaxed">
              {diagnosis.reasoning}
            </p>
          </div>
        </div>

        {/* Advisory Note (Change 5) */}
        {advisory_note && (
          <div className="p-3 bg-amber-50/60 border border-amber-200 rounded-xl text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2 text-amber-800">
              <Info className="w-4 h-4 text-amber-600 flex-shrink-0" />
              <span><strong>Advisory Note (Audit Trail Only):</strong> {advisory_note}</span>
            </div>
            <span className="text-[10px] font-mono text-amber-700 font-semibold bg-amber-100/60 px-2 py-0.5 rounded">
              Excluded from Sentinel Logic
            </span>
          </div>
        )}

        {/* 3. STAGE 3: RANKED PLAYBOOK CANDIDATE MATRIX WITH REASONED EV */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Layers className="w-4 h-4 text-indigo-600" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 font-mono">
                Stage 3 · AI Playbook Candidate Ranking &amp; Expected Value
              </h4>
            </div>
            <span className="text-[11px] text-slate-400 font-mono">
              EV = (P × Amount) - Cost
            </span>
          </div>

          {/* Top Strategy Highlight Card (Always Visible) */}
          {ranked_candidates.length > 0 && (
            <div className="bg-indigo-50/40 border border-indigo-200 rounded-xl p-4 space-y-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-indigo-600 text-white">
                    #1 TOP STRATEGY
                  </span>
                  <span className="text-xs font-bold text-slate-900 font-mono">
                    {getActionLabel(ranked_candidates[0].action)}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">({ranked_candidates[0].action})</span>
                </div>
                <div className="flex items-center space-x-3 font-mono text-xs">
                  <span className="text-slate-600">
                    Prob: <strong className="text-slate-900">{(ranked_candidates[0].success_probability * 100).toFixed(0)}%</strong>
                  </span>
                  <span className="text-slate-400">·</span>
                  <span className="text-slate-600">
                    Cost: <strong className="text-slate-900">₹{ranked_candidates[0].estimated_cost.toFixed(2)}</strong>
                  </span>
                  <span className="text-slate-400">·</span>
                  <span className={`font-bold ${ranked_candidates[0].expected_value > 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                    EV: ₹{ranked_candidates[0].expected_value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </span>
                </div>
              </div>
              <p className="text-xs text-slate-600 font-sans leading-relaxed">
                {ranked_candidates[0].rationale}
              </p>
            </div>
          )}

          {/* Progressive Disclosure Toggle */}
          {ranked_candidates.length > 1 && (
            <button
              type="button"
              onClick={() => setShowAllCandidates(!showAllCandidates)}
              className="w-full py-2 px-3 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-xs font-mono font-medium text-slate-700 flex items-center justify-between transition-colors"
            >
              <span>
                {showAllCandidates 
                  ? 'Hide candidate comparison table' 
                  : `Compare all ${ranked_candidates.length} candidate strategies`}
              </span>
              {showAllCandidates ? (
                <ChevronUp className="w-4 h-4 text-slate-500" />
              ) : (
                <ChevronDown className="w-4 h-4 text-slate-500" />
              )}
            </button>
          )}

          {/* Full Candidate Comparison Matrix (Revealed via Toggle) */}
          {showAllCandidates && (
            <div className="border border-slate-200 rounded-xl overflow-hidden font-mono text-xs">
              <table className="w-full text-left divide-y divide-slate-200">
                <thead className="bg-slate-50 text-slate-500 text-[11px] uppercase tracking-wider">
                  <tr>
                    <th className="p-3">Rank & Strategy</th>
                    <th className="p-3">Probability</th>
                    <th className="p-3">Cost</th>
                    <th className="p-3">Expected Value (₹)</th>
                    <th className="p-3">Reasoned Context Rationale</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {ranked_candidates.map((cand, idx) => {
                    const isTop = idx === 0;
                    return (
                      <tr 
                        key={cand.action}
                        className={isTop ? 'bg-indigo-50/30 font-semibold' : 'hover:bg-slate-50 transition-colors'}
                      >
                        <td className="p-3">
                          <div className="flex items-center space-x-2">
                            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                              isTop ? 'bg-indigo-600 text-white font-bold' : 'bg-slate-200 text-slate-700'
                            }`}>
                              #{idx + 1}
                            </span>
                            <div>
                              <span className="text-slate-900">{getActionLabel(cand.action)}</span>
                              <span className="block text-[10px] text-slate-400">{cand.action}</span>
                            </div>
                          </div>
                        </td>
                        <td className="p-3 text-slate-700">
                          {(cand.success_probability * 100).toFixed(0)}%
                        </td>
                        <td className="p-3 text-slate-500">
                          ₹{cand.estimated_cost.toFixed(2)}
                        </td>
                        <td className="p-3">
                          <span className={`font-bold ${cand.expected_value > 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                            ₹{cand.expected_value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </span>
                        </td>
                        <td className="p-3 text-[11px] font-sans text-slate-600 leading-relaxed max-w-md">
                          {cand.rationale}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* 4. STAGE 4: THE SENTINEL DETERMINISTIC GATE VERDICT */}
        <div className="border border-slate-200 rounded-2xl p-5 bg-slate-50/70 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center space-x-2.5">
              <ShieldCheck className="w-5 h-5 text-indigo-600" />
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 font-mono">
                  Stage 4 · The Sentinel Governance Gate (Zero-AI Standalone Rules)
                </h4>
                <p className="text-[11px] text-slate-500">Sole authority permitted to touch money movement</p>
              </div>
            </div>

            <div className={`px-3 py-1 rounded-lg border text-xs font-mono font-bold flex items-center space-x-1.5 ${
              final_sentinel_decision.approved
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-rose-50 text-rose-700 border-rose-200'
            }`}>
              {final_sentinel_decision.approved ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <XCircle className="w-4 h-4 text-rose-600" />}
              <span>Policy Code: {final_sentinel_decision.policy_code}</span>
            </div>
          </div>

          <div className="p-3 bg-white rounded-xl border border-slate-200 text-xs text-slate-700 font-sans leading-relaxed">
            <strong className="text-slate-900 font-mono">Diagnostic Verdict: </strong>
            {final_sentinel_decision.reason}
          </div>

          {/* Evaluated Policy Constraints Log */}
          {final_sentinel_decision.constraints_evaluated && (
            <div className="space-y-1.5">
              <div className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider">
                Evaluated Policy Constraints Checklist:
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 font-mono text-[11px]">
                {Object.entries(final_sentinel_decision.constraints_evaluated).map(([rule, res]) => (
                  <div key={rule} className="p-2 bg-white rounded-lg border border-slate-200 flex items-center justify-between">
                    <span className="text-slate-600">{rule}:</span>
                    <span className={`font-semibold ${res.includes('PASS') ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {res}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 5. STAGES 5 & 6: EXECUTION & GRACEFUL FALLBACK STEP-DOWN */}
        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <TrendingUp className="w-4 h-4 text-indigo-600" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 font-mono">
              Stages 5 & 6 · Multi-Step Execution & Graceful Fallback Trace
            </h4>
          </div>

          <div className="space-y-2">
            {fallback_steps.map((step) => (
              <div 
                key={step.step_number}
                className="p-3 bg-white border border-slate-200 rounded-xl flex items-center justify-between text-xs font-mono"
              >
                <div className="flex items-center space-x-3">
                  <span className="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center text-[11px] font-bold text-slate-700">
                    {step.step_number}
                  </span>
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-slate-900">{getActionLabel(step.candidate_action)}</span>
                      <span className={`px-1.5 py-0.2 rounded text-[10px] ${
                        step.sentinel_approved ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
                      }`}>
                        {step.sentinel_approved ? 'Sentinel Approved' : 'Sentinel Blocked'}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 font-sans mt-0.5">{step.notes}</p>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-[10px] text-slate-400">EV: ₹{step.expected_value.toFixed(2)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 6. HONEST COUNTERFACTUAL MODELING */}
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <FileText className="w-4 h-4 text-slate-500" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 font-mono">
                Counterfactual Modeling · Expected Value of Paths Not Taken
              </h4>
            </div>
            {onSelectPaymentForAudit && (
              <button
                onClick={() => onSelectPaymentForAudit(payment.payment_id)}
                className="text-xs font-mono text-indigo-600 hover:text-indigo-800 underline"
              >
                View Audit Trail Entries &rarr;
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 font-mono text-xs">
            {counterfactual_paths.map((p) => (
              <div key={p.action} className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-800 text-[11px]">{p.action}</span>
                  <span className={`text-[10px] px-1.5 py-0.2 rounded font-semibold ${
                    p.status === 'executed' 
                      ? 'bg-emerald-100 text-emerald-800' 
                      : p.status === 'gated_by_sentinel' 
                        ? 'bg-rose-100 text-rose-800' 
                        : 'bg-slate-200 text-slate-700'
                  }`}>
                    {p.status}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500">
                  EV: ₹{p.expected_value.toFixed(2)} · Yield: {(p.success_probability * 100).toFixed(0)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
