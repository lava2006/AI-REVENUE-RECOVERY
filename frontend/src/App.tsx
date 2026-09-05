import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { MetricsHeader } from './components/MetricsHeader';
import { PaymentsTable } from './components/PaymentsTable';
import { RecoveryDecisionCard } from './components/RecoveryDecisionCard';
import { AuditTrailViewer } from './components/AuditTrailViewer';
import { BuyerAgentDemo } from './components/BuyerAgentDemo';
import { EvalReportView } from './components/EvalReportView';
import { ArchitectureModal } from './components/ArchitectureModal';
import { PolicyModal } from './components/PolicyModal';
import { QueueView } from './components/QueueView';
import { LoginView } from './components/LoginView';
import { BatchRunSummary, RecoveryDecisionCardData, AuditLogEntry } from './types';

export const App: React.FC = () => {
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(false);
  const [merchantName, setMerchantName] = useState<string>('Acme SaaS Pvt Ltd');
  const [activeTab, setActiveTab] = useState<'queue' | 'benchmark' | 'decision-card' | 'audit-trail' | 'eval-report' | 'buyer-agent'>('queue');
  const [summary, setSummary] = useState<BatchRunSummary | null>(null);
  const [selectedPaymentId, setSelectedPaymentId] = useState<string | null>(null);
  const [selectedCard, setSelectedCard] = useState<RecoveryDecisionCardData | null>(null);
  const [isBatchRunning, setIsBatchRunning] = useState<boolean>(false);
  const [isArchModalOpen, setIsArchModalOpen] = useState<boolean>(false);
  const [isPolicyModalOpen, setIsPolicyModalOpen] = useState<boolean>(false);

  // Fetch initial batch state
  const fetchBatchSummary = async () => {
    try {
      const res = await fetch('/api/pipeline/batch-summary');
      const data: BatchRunSummary = await res.json();
      setSummary(data);
      if (data.records.length > 0 && !selectedPaymentId) {
        setSelectedPaymentId(data.records[0].payment.payment_id);
        setSelectedCard(data.records[0]);
      }
    } catch (err) {
      console.error('Failed to fetch batch summary', err);
    }
  };

  useEffect(() => {
    fetchBatchSummary();
  }, []);

  // Trigger full benchmark run
  const handleRunBatch = async () => {
    setIsBatchRunning(true);
    try {
      const res = await fetch('/api/pipeline/run-batch', { method: 'POST' });
      const data: BatchRunSummary = await res.json();
      setSummary(data);
      if (selectedPaymentId) {
        const found = data.records.find(r => r.payment.payment_id === selectedPaymentId);
        if (found) setSelectedCard(found);
      } else if (data.records.length > 0) {
        setSelectedPaymentId(data.records[0].payment.payment_id);
        setSelectedCard(data.records[0]);
      }
    } catch (err) {
      console.error('Batch run failed', err);
    } finally {
      setIsBatchRunning(false);
    }
  };

  const handleSelectPayment = (paymentId: string) => {
    setSelectedPaymentId(paymentId);
    if (!paymentId) return;
    const found = summary?.records.find(r => r.payment.payment_id === paymentId);
    if (found) {
      setSelectedCard(found);
    }
  };

  const handleSelectPaymentForAudit = (paymentId: string) => {
    setSelectedPaymentId(paymentId);
    setActiveTab('audit-trail');
  };

  // If not logged in, show institutional Login Screen
  if (!isLoggedIn) {
    return (
      <LoginView
        onLogin={(name) => {
          setMerchantName(name);
          setIsLoggedIn(true);
          setActiveTab('queue');
        }}
      />
    );
  }

  return (
    <div className="min-h-screen text-slate-900 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* Top FinTech Nav */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenArchitecture={() => setIsArchModalOpen(true)}
        onOpenPolicy={() => setIsPolicyModalOpen(true)}
        onRefreshBatch={handleRunBatch}
        onLogout={() => setIsLoggedIn(false)}
        merchantName={merchantName}
        isBatchRunning={isBatchRunning}
      />

      {/* Main Surface */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {/* Tab 1: Primary Triage Queue */}
        {activeTab === 'queue' && (
          <QueueView onSelectPaymentForAudit={handleSelectPaymentForAudit} />
        )}

        {/* Tab 2: Full Benchmark & Batch Console */}
        {activeTab === 'benchmark' && (
          <div className="space-y-6">
            <MetricsHeader summary={summary} />
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
              <div className="xl:col-span-7">
                <PaymentsTable
                  records={summary?.records || []}
                  selectedPaymentId={selectedPaymentId}
                  onSelectPayment={handleSelectPayment}
                />
              </div>
              <div className="xl:col-span-5">
                <div className="sticky top-20">
                  <RecoveryDecisionCard
                    card={selectedCard}
                    onSelectPaymentForAudit={handleSelectPaymentForAudit}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Standalone Decision Card Inspector */}
        {activeTab === 'decision-card' && (
          <div className="max-w-4xl mx-auto">
            <RecoveryDecisionCard
              card={selectedCard}
              onSelectPaymentForAudit={handleSelectPaymentForAudit}
            />
          </div>
        )}

        {/* Tab 4: Immutable Audit Trail */}
        {activeTab === 'audit-trail' && (
          <AuditTrailViewer
            logs={summary?.audit_logs || []}
            activePaymentFilter={selectedPaymentId}
            onSelectPayment={handleSelectPayment}
          />
        )}

        {/* Tab 5: Pre-Submission Evaluation Report & FAQ */}
        {activeTab === 'eval-report' && (
          <EvalReportView summary={summary} />
        )}

        {/* Tab 6: The Closing Reveal — Autonomous Buyer Agent Demo */}
        {activeTab === 'buyer-agent' && (
          <BuyerAgentDemo />
        )}
      </main>

      {/* Architecture Spec Modal */}
      <ArchitectureModal
        isOpen={isArchModalOpen}
        onClose={() => setIsArchModalOpen(false)}
      />

      {/* Configurable Policy & Catalog Modal */}
      <PolicyModal
        isOpen={isPolicyModalOpen}
        onClose={() => setIsPolicyModalOpen(false)}
        onPolicyUpdated={fetchBatchSummary}
      />
    </div>
  );
};

export default App;
