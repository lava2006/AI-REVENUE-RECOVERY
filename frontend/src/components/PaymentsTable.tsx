import React, { useState, useMemo } from 'react';
import { Search, Filter, CheckCircle2, XCircle, ShieldAlert, ArrowRight, Layers } from 'lucide-react';
import { RecoveryDecisionCardData, FailureCause, CustomerTier } from '../types';

interface PaymentsTableProps {
  records: RecoveryDecisionCardData[];
  selectedPaymentId: string | null;
  onSelectPayment: (paymentId: string) => void;
}

export const PaymentsTable: React.FC<PaymentsTableProps> = ({
  records,
  selectedPaymentId,
  onSelectPayment,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [causeFilter, setCauseFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [tierFilter, setTierFilter] = useState<string>('ALL');

  const filteredRecords = useMemo(() => {
    return records.filter((r) => {
      const matchSearch = 
        r.payment.payment_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        r.payment.customer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        r.payment.decline_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
        r.diagnosis.cause.toLowerCase().includes(searchTerm.toLowerCase());

      const matchCause = causeFilter === 'ALL' || r.diagnosis.cause === causeFilter;
      const matchStatus = 
        statusFilter === 'ALL' ||
        (statusFilter === 'RECOVERED' && r.recovered) ||
        (statusFilter === 'BLOCKED' && !r.recovered);
      const matchTier = tierFilter === 'ALL' || r.payment.customer_tier === tierFilter;

      return matchSearch && matchCause && matchStatus && matchTier;
    });
  }, [records, searchTerm, causeFilter, statusFilter, tierFilter]);

  const getCauseColor = (cause: FailureCause) => {
    switch (cause) {
      case 'INSUFFICIENT_FUNDS': return 'text-amber-700 bg-amber-50 border-amber-200';
      case 'CARD_EXPIRED': return 'text-orange-700 bg-orange-50 border-orange-200';
      case 'ISSUER_DECLINE': return 'text-blue-700 bg-blue-50 border-blue-200';
      case 'BANK_DOWNTIME': return 'text-sky-700 bg-sky-50 border-sky-200';
      case 'RISK_BLOCK': return 'text-rose-700 bg-rose-50 border-rose-200';
      default: return 'text-slate-600 bg-slate-100 border-slate-200';
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm font-sans">
      {/* Controls Bar */}
      <div className="p-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 bg-slate-50">
        <div className="flex items-center space-x-2 flex-1 min-w-[240px] max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search payments, customers, decline codes..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <select
            value={causeFilter}
            onChange={(e) => setCauseFilter(e.target.value)}
            className="bg-white border border-slate-200 text-slate-700 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Diagnoses</option>
            <option value="INSUFFICIENT_FUNDS">Insufficient Funds</option>
            <option value="CARD_EXPIRED">Card Expired</option>
            <option value="ISSUER_DECLINE">Issuer Policy Decline</option>
            <option value="BANK_DOWNTIME">Bank Downtime</option>
            <option value="RISK_BLOCK">Risk / Fraud Block</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-white border border-slate-200 text-slate-700 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Outcomes</option>
            <option value="RECOVERED">Recovered Only</option>
            <option value="BLOCKED">Blocked / Halted Only</option>
          </select>

          <select
            value={tierFilter}
            onChange={(e) => setTierFilter(e.target.value)}
            className="bg-white border border-slate-200 text-slate-700 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Customer Tiers</option>
            <option value="Enterprise">Enterprise</option>
            <option value="Growth_SMB">Growth SMB</option>
            <option value="Pro_Consumer">Pro Consumer</option>
            <option value="Free_Trial">Free Trial</option>
          </select>
        </div>
      </div>

      {/* Dense Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono divide-y divide-slate-200">
          <thead className="bg-slate-50 text-slate-500 text-[11px] uppercase tracking-wider">
            <tr>
              <th className="py-3 px-4">Payment ID</th>
              <th className="py-3 px-4">Customer</th>
              <th className="py-3 px-4">Amount (₹)</th>
              <th className="py-3 px-4">AI Diagnosis</th>
              <th className="py-3 px-4">Top Action & EV</th>
              <th className="py-3 px-4">Sentinel Policy Code</th>
              <th className="py-3 px-4">Outcome</th>
              <th className="py-3 px-4 text-right">Inspect</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {filteredRecords.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center py-8 text-slate-400">
                  No records match the current filter criteria.
                </td>
              </tr>
            ) : (
              filteredRecords.map((r) => {
                const isSelected = selectedPaymentId === r.payment.payment_id;
                const topAction = r.ranked_candidates[0];

                return (
                  <tr
                    key={r.payment.payment_id}
                    onClick={() => onSelectPayment(r.payment.payment_id)}
                    className={`cursor-pointer transition-colors ${
                      isSelected 
                        ? 'bg-indigo-50/70 font-semibold' 
                        : 'hover:bg-slate-50'
                    }`}
                  >
                    <td className="py-2.5 px-4 font-bold text-slate-900">
                      {r.payment.payment_id}
                    </td>
                    <td className="py-2.5 px-4">
                      <div className="font-medium text-slate-800 font-sans">{r.payment.customer_name}</div>
                      <div className="text-[10px] text-slate-400">{r.payment.customer_tier} · {r.payment.tenure_months}mo</div>
                    </td>
                    <td className="py-2.5 px-4 font-bold text-slate-900">
                      ₹{r.payment.amount.toLocaleString('en-IN')}
                    </td>
                    <td className="py-2.5 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${getCauseColor(r.diagnosis.cause)}`}>
                        {r.diagnosis.cause}
                      </span>
                    </td>
                    <td className="py-2.5 px-4">
                      <div className="text-slate-800">{topAction.action}</div>
                      <div className="text-[10px] text-emerald-600 font-bold">
                        EV ₹{topAction.expected_value.toFixed(2)}
                      </div>
                    </td>
                    <td className="py-2.5 px-4">
                      <span className={`text-[11px] font-bold ${
                        r.final_sentinel_decision.approved ? 'text-emerald-600' : 'text-rose-600'
                      }`}>
                        {r.final_sentinel_decision.policy_code}
                      </span>
                    </td>
                    <td className="py-2.5 px-4">
                      <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                        r.recovered 
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' 
                          : 'bg-rose-50 text-rose-700 border border-rose-200'
                      }`}>
                        {r.recovered ? <CheckCircle2 className="w-3 h-3 text-emerald-600" /> : <XCircle className="w-3 h-3 text-rose-600" />}
                        <span>{r.recovered ? 'RECOVERED' : 'UNRECOVERED'}</span>
                      </span>
                    </td>
                    <td className="py-2.5 px-4 text-right">
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectPayment(r.payment.payment_id);
                        }}
                        className="text-indigo-600 hover:text-indigo-800 text-xs font-bold"
                      >
                        Inspect &rarr;
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
