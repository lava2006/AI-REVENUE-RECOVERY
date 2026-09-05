import React, { useState, useEffect } from 'react';
import { 
  Inbox, 
  Layers, 
  CheckCircle2, 
  ChevronDown, 
  ChevronRight, 
  Play, 
  Sparkles, 
  Bot, 
  AlertTriangle, 
  ShieldCheck, 
  TrendingUp, 
  DollarSign, 
  RotateCcw,
  Zap,
  ArrowRight
} from 'lucide-react';
import { QueueGroup, QueueItem, RecoveryDecisionCardData } from '../types';
import { RecoveryDecisionCard } from './RecoveryDecisionCard';

interface QueueViewProps {
  onSelectPaymentForAudit?: (paymentId: string) => void;
}

export const QueueView: React.FC<QueueViewProps> = ({ onSelectPaymentForAudit }) => {
  const [firstRunLoaded, setFirstRunLoaded] = useState(false);
  const [queueCleared, setQueueCleared] = useState(false);
  const [groups, setGroups] = useState<QueueGroup[]>([]);
  const [autoHandledCount, setAutoHandledCount] = useState(0);
  const [autoHandledAmount, setAutoHandledAmount] = useState(0);
  const [sessionRecoveredCount, setSessionRecoveredCount] = useState(0);
  const [sessionRecoveredAmount, setSessionRecoveredAmount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [expandedGroupKey, setExpandedGroupKey] = useState<string | null>(null);
  const [selectedCard, setSelectedCard] = useState<RecoveryDecisionCardData | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  useEffect(() => {
    fetchQueue();
  }, []);

  const fetchQueue = async () => {
    try {
      const res = await fetch('/api/queue');
      const data = await res.json();
      setFirstRunLoaded(data.first_run_loaded);
      setQueueCleared(data.queue_cleared);
      setGroups(data.groups);
      setAutoHandledCount(data.auto_handled_count);
      setAutoHandledAmount(data.auto_handled_amount);
      setSessionRecoveredCount(data.session_recovered_count);
      setSessionRecoveredAmount(data.session_recovered_amount);

      if (data.groups.length > 0 && !expandedGroupKey) {
        setExpandedGroupKey(data.groups[0].group_key);
      }
    } catch (err) {
      console.error('Failed to fetch queue', err);
    }
  };

  const handleLoadPayments = async () => {
    setLoading(true);
    setActionNotice('Running autonomous pipeline over pending payments...');
    try {
      const res = await fetch('/api/queue/load', { method: 'POST' });
      const data = await res.json();
      setFirstRunLoaded(data.first_run_loaded);
      setQueueCleared(data.queue_cleared);
      setGroups(data.groups);
      setAutoHandledCount(data.auto_handled_count);
      setAutoHandledAmount(data.auto_handled_amount);
      setSessionRecoveredCount(data.session_recovered_count);
      setSessionRecoveredAmount(data.session_recovered_amount);
      if (data.groups.length > 0) {
        setExpandedGroupKey(data.groups[0].group_key);
      }
      setActionNotice(null);
    } catch (err) {
      console.error('Failed to load payments', err);
      setActionNotice('Failed to load payments.');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveItem = async (itemId: string) => {
    try {
      const res = await fetch('/api/queue/approve-item', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: itemId })
      });
      const data = await res.json();
      setActionNotice(`Card evaluated by Sentinel: ${data.sentinel_approved ? 'APPROVED' : 'BLOCKED'} (${data.policy_code})`);
      fetchQueue();
      if (selectedCard?.payment.payment_id === itemId.replace('q_', '')) {
        setSelectedCard(null);
      }
      setTimeout(() => setActionNotice(null), 4000);
    } catch (err) {
      console.error('Failed to approve item', err);
    }
  };

  const handleApproveGroup = async (groupKey: string) => {
    try {
      const res = await fetch('/api/queue/approve-group', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group_key: groupKey })
      });
      const data = await res.json();
      setActionNotice(
        `Group batch processed: ${data.sentinel_approved_count} items cleared through Sentinel individually (₹${data.total_recovered_inr.toLocaleString('en-IN')} recovered, ${data.audit_entries_generated} audit logs written).`
      );
      fetchQueue();
      setTimeout(() => setActionNotice(null), 5000);
    } catch (err) {
      console.error('Failed to approve group', err);
    }
  };

  const handleSimulateFailure = async () => {
    try {
      await fetch('/api/queue/simulate-failure', { method: 'POST' });
      setActionNotice('Seeded 1 borderline enterprise decline into the triage queue.');
      fetchQueue();
      setTimeout(() => setActionNotice(null), 3000);
    } catch (err) {
      console.error('Failed to simulate failure', err);
    }
  };

  const handleSimulateBuyerAgent = async () => {
    try {
      await fetch('/api/queue/simulate-buyer-agent', { method: 'POST' });
      setActionNotice('Seeded 1 Agent Commerce purchase request into the triage queue.');
      fetchQueue();
      setTimeout(() => setActionNotice(null), 3000);
    } catch (err) {
      console.error('Failed to simulate buyer agent', err);
    }
  };

  // FIRST-RUN STATE
  if (!firstRunLoaded) {
    return (
      <div className="py-12 max-w-2xl mx-auto text-center font-sans">
        <div className="bg-white border border-slate-200 rounded-3xl p-10 shadow-xl">
          <div className="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-5 shadow-sm">
            <Inbox className="w-8 h-8" />
          </div>

          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Today's Revenue Recovery Queue</h2>
          <p className="text-xs text-slate-500 mt-2 max-w-md mx-auto leading-relaxed">
            55 recurring subscription payments declined in the last cycle. Sensible default policy thresholds are active.
          </p>

          <div className="my-8 p-4 bg-slate-50 border border-slate-200 rounded-2xl text-left font-mono text-xs space-y-2">
            <div className="flex items-center justify-between text-slate-700">
              <span className="flex items-center space-x-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Default Sentinel Policy:</span>
              </span>
              <span className="font-bold text-slate-900">Max 3 retries · 4.0h cooldown · Positive EV only</span>
            </div>
            <div className="flex items-center justify-between text-slate-600">
              <span className="flex items-center space-x-2">
                <Zap className="w-4 h-4 text-indigo-600" />
                <span>Autonomous Handling:</span>
              </span>
              <span>High-confidence items auto-heal; borderline drops into queue</span>
            </div>
          </div>

          <button
            onClick={handleLoadPayments}
            disabled={loading}
            className="w-full py-3 px-6 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold flex items-center justify-center space-x-2 shadow-lg hover:shadow-indigo-500/25 transition-all"
          >
            <Play className="w-4 h-4 fill-white" />
            <span>{loading ? 'Processing Pipeline...' : "Load Today's Payments"}</span>
          </button>
        </div>
      </div>
    );
  }

  // QUEUE CLEARED PAYOFF STATE
  if (queueCleared || groups.length === 0) {
    return (
      <div className="py-10 max-w-3xl mx-auto text-center font-sans space-y-6">
        <div className="bg-white border border-emerald-200 rounded-3xl p-10 shadow-xl relative overflow-hidden">
          <div className="w-16 h-16 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-9 h-9" />
          </div>

          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Queue Cleared!</h2>
          <p className="text-xs text-slate-600 mt-1">
            All borderline subscription payment declines have been reviewed and resolved.
          </p>

          {/* Payoff Stats */}
          <div className="grid grid-cols-3 gap-4 mt-8">
            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 text-center">
              <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">Auto-Recovered Today</span>
              <div className="text-xl font-bold text-slate-900 mt-1">
                ₹{autoHandledAmount.toLocaleString('en-IN')}
              </div>
              <span className="text-[10px] text-emerald-600 font-semibold">{autoHandledCount} accounts saved silently</span>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 text-center">
              <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">Your Queue Approvals</span>
              <div className="text-xl font-bold text-indigo-600 mt-1">
                ₹{sessionRecoveredAmount.toLocaleString('en-IN')}
              </div>
              <span className="text-[10px] text-indigo-600 font-semibold">{sessionRecoveredCount} borderline payments cleared</span>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 text-center">
              <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">Total Revenue Saved</span>
              <div className="text-xl font-bold text-emerald-600 mt-1">
                ₹{(autoHandledAmount + sessionRecoveredAmount).toLocaleString('en-IN')}
              </div>
              <span className="text-[10px] text-emerald-700 font-semibold">100% compliant with Sentinel</span>
            </div>
          </div>

          {/* Seeded Demo Actions */}
          <div className="mt-8 pt-6 border-t border-slate-100 flex flex-wrap items-center justify-center gap-3">
            <button
              onClick={handleSimulateFailure}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl text-xs font-semibold flex items-center space-x-2 transition-colors"
            >
              <Sparkles className="w-4 h-4 text-indigo-600" />
              <span>Simulate a New Failure</span>
            </button>
            <button
              onClick={handleSimulateBuyerAgent}
              className="px-4 py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-xl text-xs font-semibold flex items-center space-x-2 transition-colors"
            >
              <Bot className="w-4 h-4" />
              <span>Simulate Agent Purchase Request (Closing Demo)</span>
            </button>
            <button
              onClick={handleLoadPayments}
              className="px-4 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-xl text-xs font-medium flex items-center space-x-2 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset & Reload Benchmark</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ACTIVE QUEUE WITH SMART GROUPING
  const totalPendingItems = groups.reduce((acc, g) => acc + g.item_count, 0);

  return (
    <div className="space-y-6 font-sans">
      {/* Silent Auto-Handling Informational Banner */}
      <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-emerald-50 text-emerald-600 rounded-xl">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-900 flex items-center space-x-2">
              <span>{autoHandledCount} high-confidence payments handled automatically in background</span>
              <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-[10px]">
                Silent Execution
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Recovered <strong className="text-slate-800">₹{autoHandledAmount.toLocaleString('en-IN')}</strong> without operator interruption. Only borderline cases require human attention below.
            </p>
          </div>
        </div>

        {/* Demo Triggers */}
        <div className="flex items-center space-x-2">
          <button
            onClick={handleSimulateFailure}
            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium flex items-center space-x-1.5 transition-colors"
            title="Inject a seeded borderline failure"
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>Simulate Failure</span>
          </button>
          <button
            onClick={handleSimulateBuyerAgent}
            className="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-lg text-xs font-medium flex items-center space-x-1.5 transition-colors"
            title="Simulate Autonomous Buyer Agent request gated by the Sentinel"
          >
            <Bot className="w-3.5 h-3.5" />
            <span>Simulate Agent Commerce</span>
          </button>
        </div>
      </div>

      {/* Action Notification */}
      {actionNotice && (
        <div className="p-3 bg-indigo-50 border border-indigo-200 text-indigo-900 rounded-xl text-xs flex items-center justify-between shadow-sm">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-indigo-600 flex-shrink-0" />
            <span>{actionNotice}</span>
          </div>
          <button onClick={() => setActionNotice(null)} className="text-indigo-400 hover:text-indigo-700 font-bold">&times;</button>
        </div>
      )}

      {/* Queue Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">Review Queue</h2>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-amber-50 text-amber-800 border border-amber-200 shadow-sm">
              {totalPendingItems} items remaining
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Auto-grouped by shared diagnosed cause &amp; recommended recovery strategy.
          </p>
        </div>
      </div>

      {/* Smart Grouped Stacks */}
      <div className="space-y-4">
        {groups.map((group) => {
          const isExpanded = expandedGroupKey === group.group_key;
          const isAgentGroup = group.item_type === 'agent_commerce';

          return (
            <div
              key={group.group_key}
              className={`bg-white border rounded-2xl shadow-sm transition-all overflow-hidden ${
                isAgentGroup ? 'border-indigo-300 ring-1 ring-indigo-200' : 'border-slate-200'
              }`}
            >
              {/* Group Header Card */}
              <div className="p-4 flex flex-wrap items-center justify-between gap-3 bg-slate-50/70 border-b border-slate-100">
                <div 
                  onClick={() => setExpandedGroupKey(isExpanded ? null : group.group_key)}
                  className="flex items-center space-x-3 cursor-pointer flex-1"
                >
                  <button className="text-slate-400 hover:text-slate-700">
                    {isExpanded ? <ChevronDown className="w-5 h-5 text-indigo-600" /> : <ChevronRight className="w-5 h-5" />}
                  </button>

                  <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
                    {isAgentGroup ? <Bot className="w-4 h-4" /> : <Layers className="w-4 h-4" />}
                  </div>

                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-slate-900 font-mono">
                        {group.label}
                      </span>
                      <span className="px-2 py-0.5 bg-slate-200/60 text-slate-700 text-[10px] font-mono font-semibold rounded-full">
                        {group.item_count} items
                      </span>
                      {isAgentGroup && (
                        <span className="px-2 py-0.5 bg-indigo-100 text-indigo-800 text-[10px] font-semibold rounded-full">
                          Agent Commerce Reveal
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Total value in stack: <strong className="text-slate-900">₹{group.total_amount.toLocaleString('en-IN')}</strong> · Sentinel gates each item individually
                    </p>
                  </div>
                </div>

                {/* Group Action Buttons */}
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setExpandedGroupKey(isExpanded ? null : group.group_key)}
                    className="px-3 py-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-medium transition-colors"
                  >
                    {isExpanded ? 'Collapse Stack' : 'Review Cards (Stack)'}
                  </button>
                  <button
                    onClick={() => handleApproveGroup(group.group_key)}
                    className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow-sm transition-all"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Approve All in Group ({group.item_count})</span>
                  </button>
                </div>
              </div>

              {/* Expanded Stack Items */}
              {isExpanded && (
                <div className="p-4 bg-slate-50/30 divide-y divide-slate-100 space-y-3">
                  <div className="text-[11px] text-slate-500 font-mono mb-2">
                    Reviewing individual cards in pattern group. Click "Inspect Full Decision Card" to view complete AI diagnosis, candidate matrix, and Sentinel policy checklist:
                  </div>

                  {group.items.map((item) => (
                    <div
                      key={item.item_id}
                      className="pt-3 first:pt-0 flex flex-wrap items-center justify-between gap-3 bg-white p-3 rounded-xl border border-slate-200 shadow-sm"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center font-mono text-xs font-bold text-slate-700">
                          {item.item_type === 'agent_commerce' ? 'AI' : '₹'}
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="font-mono text-xs font-bold text-slate-900">{item.payment_id}</span>
                            <span className="text-xs text-slate-600 font-medium">· {item.customer_name}</span>
                            <span className="px-1.5 py-0.5 bg-slate-100 text-slate-600 text-[10px] rounded">
                              {item.customer_tier}
                            </span>
                          </div>
                          <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                            Amount: <strong className="text-slate-800">₹{item.amount.toLocaleString('en-IN')}</strong> · Top action: <span className="text-indigo-600 font-semibold">{item.top_ranked_strategy}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => setSelectedCard(item.card_data)}
                          className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium transition-colors"
                        >
                          Inspect Decision Card &rarr;
                        </button>
                        <button
                          onClick={() => handleApproveItem(item.item_id)}
                          className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-1 shadow-sm transition-all"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Approve Item</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Decision Card Modal / Inspector */}
      {selectedCard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
          <div className="bg-white border border-slate-200 rounded-3xl shadow-2xl max-w-4xl w-full max-h-[92vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center space-x-2">
                <span className="text-xs font-mono font-bold text-slate-900">
                  Detailed Recovery Decision Card: {selectedCard.payment.payment_id}
                </span>
                <span className="px-2 py-0.5 bg-amber-50 text-amber-700 text-[10px] font-bold rounded-full">
                  Borderline Queue Item
                </span>
              </div>
              <button
                onClick={() => setSelectedCard(null)}
                className="text-slate-400 hover:text-slate-700 p-1.5 rounded-lg hover:bg-slate-200/60"
              >
                &times;
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex-1">
              <RecoveryDecisionCard
                card={selectedCard}
                onSelectPaymentForAudit={onSelectPaymentForAudit}
              />
            </div>

            <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
              <span className="text-xs text-slate-500 font-mono">
                Approve will invoke Sentinel rule verification for this item individually.
              </span>
              <button
                onClick={() => {
                  handleApproveItem(`q_${selectedCard.payment.payment_id}`);
                }}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold flex items-center space-x-2 shadow-sm"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Approve This Payment</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
