import React, { useState } from 'react';
import { ShieldCheck, ArrowRight, Lock, Building2, Sparkles, CheckCircle2 } from 'lucide-react';

interface LoginViewProps {
  onLogin: (merchantName: string) => void;
}

export const LoginView: React.FC<LoginViewProps> = ({ onLogin }) => {
  const [email, setEmail] = useState('billing-ops@acmesoftware.in');
  const [merchantId, setMerchantId] = useState('acc_rzp_live_9481');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onLogin('Acme SaaS Pvt Ltd');
  };

  return (
    <div className="min-h-screen flex flex-col justify-center items-center px-4 py-12">
      <div className="max-w-md w-full">
        {/* Brand Banner */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-blue-600 text-white shadow-lg mb-4">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Rebound</h1>
          <p className="text-xs font-mono font-semibold uppercase tracking-wider text-blue-600 mt-1">
            Autonomous AI Revenue Recovery Console
          </p>
          <p className="text-xs text-slate-500 mt-2">
            Razorpay AI Buildathon Track 3 · Autonomous Diagnosis & Deterministic Sentinel Gate
          </p>
        </div>

        {/* Card */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-xl p-8">
          <div className="flex items-center justify-between pb-4 mb-6 border-b border-slate-100">
            <div>
              <h2 className="text-base font-bold text-slate-900">Merchant Sign In</h2>
              <p className="text-xs text-slate-500">Access your daily recovery triage queue</p>
            </div>
            <span className="px-2.5 py-1 bg-emerald-50 border border-emerald-200 text-emerald-700 text-[11px] font-semibold rounded-full flex items-center space-x-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse mr-1"></span>
              Gateway Online
            </span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1 font-mono">
                Merchant Account / Razorpay ID
              </label>
              <div className="relative">
                <Building2 className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={merchantId}
                  onChange={(e) => setMerchantId(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono text-slate-800 focus:outline-none focus:border-blue-500 focus:bg-white"
                  placeholder="acc_rzp_live_XXXX"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1 font-mono">
                Operator Work Email
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono text-slate-800 focus:outline-none focus:border-blue-500 focus:bg-white"
                  placeholder="name@company.com"
                  required
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg text-xs flex items-center justify-center space-x-2 shadow-sm transition-all"
              >
                <span>Enter Recovery Queue</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </form>

          {/* Quick Demo Preload */}
          <div className="mt-6 pt-5 border-t border-slate-100">
            <button
              onClick={() => onLogin('Acme SaaS Pvt Ltd')}
              className="w-full py-2 px-3 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-xs text-slate-700 font-mono flex items-center justify-between transition-colors"
            >
              <span className="flex items-center space-x-1.5">
                <Sparkles className="w-3.5 h-3.5 text-blue-500" />
                <span className="font-semibold">Quick Demo Login:</span> Acme SaaS (Enterprise)
              </span>
              <span className="text-[10px] text-blue-600 font-bold">1-Click &rarr;</span>
            </button>
          </div>
        </div>
        
        <p className="mt-8 text-center text-xs text-slate-400 font-mono">
          Compliant Autonomous Revenue Recovery · Track 3
        </p>
      </div>
    </div>
  );
};
