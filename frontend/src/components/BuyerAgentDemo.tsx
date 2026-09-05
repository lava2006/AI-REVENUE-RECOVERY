import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  ShieldAlert, 
  Cpu, 
  ShoppingCart, 
  CheckCircle2, 
  XCircle, 
  Zap, 
  ArrowRight, 
  Bot, 
  Sparkles, 
  RotateCcw,
  Sliders,
  Layers,
  ChevronDown,
  ChevronRight,
  Info
} from 'lucide-react';
import { MerchantCatalogItem } from '../types';

export const BuyerAgentDemo: React.FC = () => {
  const [catalog, setCatalog] = useState<MerchantCatalogItem[]>([]);
  const [selectedSku, setSelectedSku] = useState<string>('sku_gpu_cluster');
  const [selectedAgent, setSelectedAgent] = useState<'apollo' | 'titan'>('apollo');
  const [customAmount, setCustomAmount] = useState<number>(48000);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
  const [evaluationResult, setEvaluationResult] = useState<any | null>(null);
  const [showTechnicalBreakdown, setShowTechnicalBreakdown] = useState<boolean>(false);

  useEffect(() => {
    fetchCatalog();
  }, []);

  const fetchCatalog = async () => {
    try {
      const res = await fetch('/api/buyer-agent/catalog');
      const data = await res.json();
      setCatalog(data);
      if (data.length > 0) {
        setSelectedSku(data[0].sku);
        setCustomAmount(data[0].price);
      }
    } catch (err) {
      console.error('Failed to fetch catalog', err);
    }
  };

  const agents = {
    apollo: {
      id: 'agent_procure_apollo',
      name: 'ApolloDevOps (Autonomous Cluster Provisioner)',
      scopes: ['procurement.saas.basic', 'procurement.infra.high_value'],
      budget: 100000.0,
      currentSpend: 32000.0,
      priorOrders: 1,
    },
    titan: {
      id: 'agent_titan_junior',
      name: 'TitanJuniorBot (Restricted CI/CD Worker)',
      scopes: ['procurement.saas.basic'],
      budget: 25000.0,
      currentSpend: 18000.0,
      priorOrders: 2,
    },
  };

  const handleSkuChange = (sku: string) => {
    setSelectedSku(sku);
    const item = catalog.find((i) => i.sku === sku);
    if (item) setCustomAmount(item.price);
  };

  const handleEvaluate = async () => {
    setIsEvaluating(true);
    setEvaluationResult(null);
    setShowTechnicalBreakdown(false);

    const activeAgent = agents[selectedAgent];
    const payload = {
      agent_id: activeAgent.id,
      agent_name: activeAgent.name,
      sku_id: selectedSku,
      amount: customAmount,
      requested_units: 1,
      business_justification: `Autonomous procurement of ${selectedSku} for infrastructure workload.`,
      granted_scopes: activeAgent.scopes,
      monthly_budget_inr: activeAgent.budget,
      current_month_spend_inr: activeAgent.currentSpend,
      prior_orders_today: activeAgent.priorOrders,
      advisory_note: 'Demonstrating unmodified Sentinel reuse on agent commerce',
    };

    try {
      const res = await fetch('/api/buyer-agent/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      setEvaluationResult(data);
    } catch (err) {
      console.error('Failed to evaluate purchase', err);
    } finally {
      setIsEvaluating(false);
    }
  };

  const activeAgent = agents[selectedAgent];
  const selectedItem = catalog.find((i) => i.sku === selectedSku);

  // Friendly human-readable label mapping for technical rules
  const getRuleDisplayName = (ruleKey: string): string => {
    const map: Record<string, string> = {
      expected_value_check: 'Expected Value',
      amount_check: 'Purchase Amount',
      budget_check: 'Monthly Budget',
      catalog_check: 'Catalog Match',
      stock_check: 'Stock Availability',
      price_check: 'Catalog Price Match',
      permission_check: 'Permission Scope',
      risk_check: 'Risk Score',
      retry_limit_check: 'Retry Limit',
      cooldown_check: 'Cooldown Window',
      escalation_check: 'Customer Notification Frequency',
    };
    return map[ruleKey] || ruleKey.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  };

  // Plain-English lay merchant explanation (Layer 1)
  const getPlainEnglishReason = (result: any): string => {
    const dec = result.sentinel_decision;
    if (dec.approved) {
      return 'Approved — this purchase is within the agent’s monthly budget, pricing matches your active catalog, and required permissions are verified.';
    }

    const code = dec.policy_code;
    if (code === 'POLICY_BUDGET_EXCEEDED') {
      const current = result.current_spend_inr || 0;
      const requested = result.requested_amount_inr || 0;
      const total = current + requested;
      const budget = result.monthly_budget_inr || 0;
      return `Blocked — this purchase would push the agent's monthly spend to ₹${total.toLocaleString('en-IN')}, which is over its ₹${budget.toLocaleString('en-IN')} budget.`;
    }

    if (code === 'POLICY_PERMISSION_DENIED') {
      return `Blocked — this agent only has basic permissions and is not authorized to purchase '${result.item_name || 'this item'}'.`;
    }

    if (code === 'POLICY_OUT_OF_STOCK') {
      return `Blocked — '${result.item_name || 'this item'}' is currently marked out of stock in your merchant catalog.`;
    }

    if (code === 'POLICY_PRICE_MISMATCH') {
      const reqAmt = result.requested_amount_inr || 0;
      return `Blocked — the requested price of ₹${reqAmt.toLocaleString('en-IN')} does not match the price in your active catalog.`;
    }

    if (code === 'POLICY_AMOUNT_EXCEEDS_LIMIT') {
      return `Blocked — the requested amount of ₹${(result.requested_amount_inr || 0).toLocaleString('en-IN')} exceeds your allowable single-purchase safety limit.`;
    }

    if (code === 'POLICY_EV_NEGATIVE') {
      return 'Blocked — the expected return from this transaction does not meet your positive expected value threshold.';
    }

    return `Blocked — ${dec.reason.replace(/^Rejected:\s*/i, '')}`;
  };

  return (
    <div className="space-y-6 font-sans">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <div className="flex items-center space-x-2 text-xs font-mono font-bold text-slate-500 uppercase tracking-wider mb-2">
          <Sparkles className="w-4 h-4 text-emerald-600" />
          <span>The Closing Reveal · Autonomous Agent Commerce</span>
        </div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">
          One Sentinel. Any Agent Touching Money.
        </h2>
        <p className="text-xs text-slate-500 mt-1 max-w-3xl leading-relaxed">
          The Sentinel is action-agnostic. The exact same deterministic policy engine that protects subscription revenue can evaluate an autonomous AI Buyer Agent purchasing SaaS tools — without changing any safety logic.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Config Panel: 5 Cols */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex items-center space-x-2 text-xs font-mono font-bold text-slate-900 uppercase tracking-wider border-b border-slate-100 pb-3">
              <Bot className="w-4 h-4 text-slate-700" />
              <span>1. Select Autonomous Buyer Agent</span>
            </div>

            <div className="space-y-2">
              <button
                onClick={() => setSelectedAgent('apollo')}
                className={`w-full p-3 rounded-xl border text-left text-xs transition-all ${
                  selectedAgent === 'apollo'
                    ? 'bg-slate-50 border-slate-400 ring-1 ring-slate-300'
                    : 'bg-white border-slate-200 hover:bg-slate-50'
                }`}
              >
                <div className="font-bold text-slate-900">{agents.apollo.name}</div>
                <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                  Budget: ₹1,00,000 (Current spend: ₹32,000) · Elevated Scopes
                </div>
              </button>

              <button
                onClick={() => setSelectedAgent('titan')}
                className={`w-full p-3 rounded-xl border text-left text-xs transition-all ${
                  selectedAgent === 'titan'
                    ? 'bg-slate-50 border-slate-400 ring-1 ring-slate-300'
                    : 'bg-white border-slate-200 hover:bg-slate-50'
                }`}
              >
                <div className="font-bold text-slate-900">{agents.titan.name}</div>
                <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                  Budget: ₹25,000 (Current spend: ₹18,000) · Basic Scopes Only
                </div>
              </button>
            </div>

            <div className="pt-2 border-t border-slate-100 space-y-3">
              <div className="flex items-center space-x-2 text-xs font-mono font-bold text-slate-900 uppercase tracking-wider">
                <ShoppingCart className="w-4 h-4 text-slate-700" />
                <span>2. Select Merchant Catalog Item</span>
              </div>

              <select
                value={selectedSku}
                onChange={(e) => handleSkuChange(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono text-slate-800 focus:outline-none focus:border-slate-400"
              >
                {catalog.map((item) => (
                  <option key={item.sku} value={item.sku}>
                    {item.name} — ₹{item.price.toLocaleString('en-IN')} {item.in_stock ? '' : '(OUT OF STOCK)'}
                  </option>
                ))}
              </select>

              <div>
                <label className="block text-[11px] font-mono font-semibold text-slate-700 mb-1">
                  Requested Amount (₹)
                </label>
                <input
                  type="number"
                  value={customAmount}
                  onChange={(e) => setCustomAmount(parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono text-slate-900 focus:outline-none focus:border-slate-400"
                />
              </div>

              {selectedItem && (
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-[11px] font-mono space-y-1 text-slate-600">
                  <div className="flex justify-between">
                    <span>Stock Status:</span>
                    <strong className={selectedItem.in_stock ? 'text-emerald-700' : 'text-rose-700'}>
                      {selectedItem.in_stock ? 'IN_STOCK' : 'OUT_OF_STOCK'}
                    </strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Required Scope:</span>
                    <strong className="text-slate-800">{selectedItem.requires_permission}</strong>
                  </div>
                </div>
              )}

              <button
                onClick={handleEvaluate}
                disabled={isEvaluating}
                className="w-full py-2.5 px-4 bg-slate-900 hover:bg-slate-800 text-white font-semibold rounded-xl text-xs flex items-center justify-center space-x-2 shadow-sm transition-all"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>{isEvaluating ? 'Evaluating Decision...' : 'Evaluate with The Sentinel'}</span>
              </button>
            </div>
          </div>
        </div>

        {/* Right Output Panel: 7 Cols (Section 2 Progressive Disclosure) */}
        <div className="lg:col-span-7">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm min-h-[440px] flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
                <div className="flex items-center space-x-2 text-xs font-mono font-bold text-slate-900 uppercase tracking-wider">
                  <ShieldCheck className="w-4 h-4 text-slate-700" />
                  <span>Sentinel Evaluation Result</span>
                </div>
                {evaluationResult && (
                  <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                    evaluationResult.sentinel_decision.approved
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : 'bg-rose-50 text-rose-700 border border-rose-200'
                  }`}>
                    {evaluationResult.sentinel_decision.approved ? 'Approved' : 'Blocked'}
                  </span>
                )}
              </div>

              {!evaluationResult ? (
                <div className="py-20 text-center text-slate-400 font-sans text-xs">
                  <Cpu className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                  Select an agent and catalog item, then click "Evaluate with The Sentinel".
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Layer 1: Layman Merchant Plain-English View */}
                  <div className={`p-4 rounded-xl border ${
                    evaluationResult.sentinel_decision.approved
                      ? 'bg-emerald-50/60 border-emerald-200'
                      : 'bg-rose-50/60 border-rose-200'
                  }`}>
                    <div className="flex items-start space-x-2.5">
                      {evaluationResult.sentinel_decision.approved ? (
                        <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                      ) : (
                        <XCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
                      )}
                      <div>
                        <div className="text-xs font-bold text-slate-900 mb-1">
                          {evaluationResult.sentinel_decision.approved ? 'Purchase Authorization Approved' : 'Purchase Authorization Blocked'}
                        </div>
                        <p className="text-xs text-slate-700 leading-relaxed font-sans">
                          {getPlainEnglishReason(evaluationResult)}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Summary Details Strip */}
                  <div className="grid grid-cols-3 gap-3 p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs font-sans">
                    <div>
                      <span className="block text-[10px] text-slate-500 uppercase tracking-wider font-mono">Agent</span>
                      <span className="font-semibold text-slate-800">{activeAgent.name.split(' ')[0]}</span>
                    </div>
                    <div>
                      <span className="block text-[10px] text-slate-500 uppercase tracking-wider font-mono">Item</span>
                      <span className="font-semibold text-slate-800">{selectedItem?.name || selectedSku}</span>
                    </div>
                    <div>
                      <span className="block text-[10px] text-slate-500 uppercase tracking-wider font-mono">Requested</span>
                      <span className="font-semibold text-slate-900 font-mono">₹{customAmount.toLocaleString('en-IN')}</span>
                    </div>
                  </div>

                  {/* Layer 2: Expandable Technical Breakdown (Collapsed by default) */}
                  <div className="pt-2">
                    <button
                      onClick={() => setShowTechnicalBreakdown(!showTechnicalBreakdown)}
                      className="flex items-center space-x-1.5 text-xs text-slate-600 hover:text-slate-900 font-mono font-medium py-1 transition-colors"
                    >
                      {showTechnicalBreakdown ? (
                        <ChevronDown className="w-4 h-4 text-slate-500" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-slate-500" />
                      )}
                      <span>{showTechnicalBreakdown ? 'Hide technical policy breakdown' : 'See full policy breakdown'}</span>
                    </button>

                    {showTechnicalBreakdown && (
                      <div className="mt-3 p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3 animate-in fade-in duration-150">
                        <div className="flex items-center justify-between text-[11px] font-mono text-slate-600 border-b border-slate-200 pb-2">
                          <span>Policy Decision Code:</span>
                          <strong className="text-slate-900">{evaluationResult.sentinel_decision.policy_code}</strong>
                        </div>

                        <div className="space-y-2">
                          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider">
                            Policy Rule Checklist:
                          </span>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
                            {Object.entries(evaluationResult.sentinel_decision.constraints_evaluated || {}).map(([r, s]: any) => (
                              <div key={r} className="p-2.5 bg-white rounded-lg border border-slate-200 flex items-center justify-between">
                                <span className="text-slate-700">{getRuleDisplayName(r)}:</span>
                                <span className={`font-bold ${s.includes('PASS') ? 'text-emerald-700' : 'text-rose-700'}`}>
                                  {s.includes('PASS') ? 'PASS' : 'FAIL'}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>

                        <div className="pt-2 text-[11px] font-mono text-slate-500 space-y-1">
                          <div>Granted Scopes: <span className="text-slate-800">{evaluationResult.granted_scopes.join(', ')}</span></div>
                          <div>Required Scope: <span className="text-slate-800">{evaluationResult.required_scope || 'None'}</span></div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
