import React, { useState, useEffect } from 'react';
import { X, Sliders, Database, Save, RotateCcw, Upload, CheckCircle2, AlertCircle, ShoppingCart } from 'lucide-react';
import { MerchantPolicyConfig, MerchantCatalogItem } from '../types';

interface PolicyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPolicyUpdated?: () => void;
}

export const PolicyModal: React.FC<PolicyModalProps> = ({ isOpen, onClose, onPolicyUpdated }) => {
  const [activeTab, setActiveTab] = useState<'rules' | 'catalog'>('rules');
  const [config, setConfig] = useState<MerchantPolicyConfig>({
    max_retries: 3,
    cooldown_hours: 4.0,
    max_escalations: 2,
    min_ev: 0.01,
    max_recovery_amount: 250000.0,
    min_amount: 1.0,
    max_permissible_risk: 0.70,
  });
  const [catalog, setCatalog] = useState<MerchantCatalogItem[]>([]);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [csvInput, setCsvInput] = useState('');
  const [showCsvBox, setShowCsvBox] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchPolicy();
      fetchCatalog();
    }
  }, [isOpen]);

  const fetchPolicy = async () => {
    try {
      const res = await fetch('/api/policy-config');
      const data = await res.json();
      setConfig(data);
    } catch (err) {
      console.error('Failed to load policy config', err);
    }
  };

  const fetchCatalog = async () => {
    try {
      const res = await fetch('/api/buyer-agent/catalog');
      const data = await res.json();
      setCatalog(data);
    } catch (err) {
      console.error('Failed to load catalog', err);
    }
  };

  const handleSavePolicy = async () => {
    setSaving(true);
    setSaveSuccess(null);
    setErrorMessage(null);
    try {
      const res = await fetch('/api/policy-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      if (!res.ok) {
        throw new Error('Validation failed');
      }
      const data = await res.json();
      setConfig(data);
      setSaveSuccess('Policy rules updated and active in Sentinel!');
      if (onPolicyUpdated) onPolicyUpdated();
      setTimeout(() => setSaveSuccess(null), 3000);
    } catch (err: any) {
      setErrorMessage('Validation error: please check thresholds.');
    } finally {
      setSaving(false);
    }
  };

  const handleUploadCsv = async () => {
    if (!csvInput.trim()) return;
    setSaving(true);
    try {
      const res = await fetch('/api/buyer-agent/catalog/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' },
        body: csvInput
      });
      const data = await res.json();
      setCatalog(data.catalog);
      setShowCsvBox(false);
      setCsvInput('');
      setSaveSuccess(`Uploaded ${data.catalog_size} catalog items!`);
      setTimeout(() => setSaveSuccess(null), 3000);
    } catch (err: any) {
      setErrorMessage('Failed to parse and upload catalog CSV.');
    } finally {
      setSaving(false);
    }
  };

  const handleResetCatalog = async () => {
    setSaving(true);
    try {
      const res = await fetch('/api/buyer-agent/catalog/reset', { method: 'POST' });
      const data = await res.json();
      setCatalog(data.catalog);
      setSaveSuccess('Catalog reset to default items.');
      setTimeout(() => setSaveSuccess(null), 3000);
    } catch (err) {
      setErrorMessage('Failed to reset catalog.');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
      <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">Governance & Sentinel Policies</h3>
              <p className="text-xs text-slate-500">Configurable merchant safety bounds evaluated at runtime</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 p-1.5 rounded-lg hover:bg-slate-200/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Controls */}
        <div className="px-6 pt-3 border-b border-slate-200 flex space-x-4 text-xs font-medium">
          <button
            onClick={() => setActiveTab('rules')}
            className={`pb-2.5 flex items-center space-x-1.5 border-b-2 transition-colors ${
              activeTab === 'rules'
                ? 'border-indigo-600 text-indigo-600 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Sentinel Rules & Thresholds</span>
          </button>
          <button
            onClick={() => setActiveTab('catalog')}
            className={`pb-2.5 flex items-center space-x-1.5 border-b-2 transition-colors ${
              activeTab === 'catalog'
                ? 'border-indigo-600 text-indigo-600 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <ShoppingCart className="w-3.5 h-3.5" />
            <span>Merchant Catalog & Gating ({catalog.length} SKUs)</span>
          </button>
        </div>

        {/* Notifications */}
        {saveSuccess && (
          <div className="mx-6 mt-4 p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{saveSuccess}</span>
          </div>
        )}
        {errorMessage && (
          <div className="mx-6 mt-4 p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Body Content */}
        <div className="p-6 overflow-y-auto flex-1 text-xs">
          {activeTab === 'rules' ? (
            <div className="space-y-4">
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-600 leading-relaxed">
                <span className="font-semibold text-slate-800">Deterministic Safety Principle:</span> Changes made here immediately update the Sentinel rules engine in memory. No code rebuild or model retraining needed.
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Max Retry Limit (Attempts)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={config.max_retries}
                    onChange={(e) => setConfig({ ...config, max_retries: parseInt(e.target.value) || 3 })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-mono focus:outline-none focus:border-indigo-500 focus:bg-white"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">Default: 3 attempts per invoice cycle</p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Mandatory Cooldown (Hours)
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    max="72"
                    value={config.cooldown_hours}
                    onChange={(e) => setConfig({ ...config, cooldown_hours: parseFloat(e.target.value) || 4.0 })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-mono focus:outline-none focus:border-indigo-500 focus:bg-white"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">Minimum pause between retries (e.g. 4.0h)</p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Max Customer Dunning Escalations
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="10"
                    value={config.max_escalations}
                    onChange={(e) => setConfig({ ...config, max_escalations: parseInt(e.target.value) || 2 })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-mono focus:outline-none focus:border-indigo-500 focus:bg-white"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">Anti-spam cap on SMS/WhatsApp messages</p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Minimum Expected Value Cutoff (₹)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={config.min_ev}
                    onChange={(e) => setConfig({ ...config, min_ev: parseFloat(e.target.value) || 0.01 })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-mono focus:outline-none focus:border-indigo-500 focus:bg-white"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">Actions below this threshold are blocked</p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Auto-Recovery Ceiling Amount (₹)
                  </label>
                  <input
                    type="number"
                    step="1000"
                    value={config.max_recovery_amount}
                    onChange={(e) => setConfig({ ...config, max_recovery_amount: parseFloat(e.target.value) || 250000 })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-mono focus:outline-none focus:border-indigo-500 focus:bg-white"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">Maximum single transaction bound (₹2,50,000)</p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Max Permissible Risk Score
                  </label>
                  <input
                    type="number"
                    step="0.05"
                    min="0.1"
                    max="1.0"
                    value={config.max_permissible_risk}
                    onChange={(e) => setConfig({ ...config, max_permissible_risk: parseFloat(e.target.value) || 0.70 })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-mono focus:outline-none focus:border-indigo-500 focus:bg-white"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">Gateway risk score threshold (0.70)</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-900">Uploadable Merchant SKU Catalog</h4>
                  <p className="text-[11px] text-slate-500">Autonomous Buyer Agents are gated against these exact SKUs & stock status</p>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setShowCsvBox(!showCsvBox)}
                    className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium flex items-center space-x-1 transition-colors"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    <span>Upload CSV</span>
                  </button>
                  <button
                    onClick={handleResetCatalog}
                    className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium flex items-center space-x-1 transition-colors"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Reset Defaults</span>
                  </button>
                </div>
              </div>

              {showCsvBox && (
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                  <div className="flex items-center justify-between text-[11px] text-slate-600 font-mono">
                    <span>Paste CSV with columns: sku,name,price,in_stock,category,requires_permission</span>
                    <button onClick={() => setShowCsvBox(false)} className="text-slate-400 hover:text-slate-700">&times;</button>
                  </div>
                  <textarea
                    rows={4}
                    value={csvInput}
                    onChange={(e) => setCsvInput(e.target.value)}
                    placeholder="sku,name,price,in_stock,category,requires_permission&#10;sku_vpn_tier,Enterprise Zero-Trust VPN,4500,true,Security,procurement.security.tools"
                    className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs font-mono text-slate-800 focus:outline-none focus:border-indigo-500"
                  />
                  <div className="flex justify-end">
                    <button
                      onClick={handleUploadCsv}
                      disabled={saving}
                      className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-medium shadow-sm transition-all"
                    >
                      Process & Upload Catalog
                    </button>
                  </div>
                </div>
              )}

              <div className="border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100 font-mono">
                {catalog.map((item) => (
                  <div key={item.sku} className="p-3 flex items-center justify-between bg-white hover:bg-slate-50 transition-colors">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-slate-900 text-xs">{item.name}</span>
                        <span className="text-[10px] text-slate-400">({item.sku})</span>
                        <span className={`px-1.5 py-0.2 rounded text-[10px] font-semibold ${
                          item.in_stock 
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' 
                            : 'bg-rose-50 text-rose-700 border border-rose-200'
                        }`}>
                          {item.in_stock ? 'IN_STOCK' : 'OUT_OF_STOCK'}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-0.5">{item.description || 'Standard catalog SKU'}</p>
                    </div>
                    <div className="text-right">
                      <span className="text-xs font-bold text-slate-900">₹{item.price.toLocaleString('en-IN')}</span>
                      <p className="text-[10px] text-indigo-600">{item.requires_permission || 'procurement.basic'}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="text-[11px] text-slate-500">
            {activeTab === 'rules' ? 'Policy changes apply dynamically to all subsequent Sentinel evaluations.' : 'Catalog prices are checked against buyer agent requests.'}
          </div>
          {activeTab === 'rules' && (
            <button
              onClick={handleSavePolicy}
              disabled={saving}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-2 shadow-sm transition-all"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? 'Saving...' : 'Save Policy Changes'}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
