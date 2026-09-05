"""
Synthetic Dataset Generator for Rebound — AI Revenue Recovery Agent
Generates 55+ labeled recurring subscription payment failures with realistic
Razorpay and banking decline codes, customer history, and ground-truth causes.
"""

from typing import List
from datetime import datetime, timezone, timedelta
from backend.models.schemas import PaymentRecord, FailureCause, CustomerTier


def generate_synthetic_dataset() -> List[PaymentRecord]:
    """
    Produces a calibrated benchmark dataset of 55 failed subscription payments.
    Each record includes realistic decline telemetry, customer tenure, retry state,
    and ground-truth diagnostic and recoverability labels.
    """
    now = datetime.now(timezone.utc)
    
    # Pre-defined base scenarios covering the 5 distinct subscription failure classes
    records: List[PaymentRecord] = []

    # --- CATEGORY 1: BANK DOWNTIME (Transient, high immediate recoverability) ---
    downtime_templates = [
        ("sub_h98a1", 2499.0, "GATEWAY_ERROR_ISSUER_DOWN", "Razorpay Error: HDFC Bank core switch timeout (HTTP 504 Gateway Timeout). Issuer unavailable.", CustomerTier.GROWTH_SMB, "TechCorp Pvt Ltd", 18, 0, 0, 15, True),
        ("sub_b41c2", 999.0, "GATEWAY_ERROR_NPCI_UNAVAILABLE", "NPCI UPI Mandate switch error: Timeout connecting to beneficiary bank gateway.", CustomerTier.PRO_CONSUMER, "Aarav Sharma", 8, 0, 0, 30, True),
        ("sub_f72d3", 14999.0, "GATEWAY_ERROR_ISSUER_DOWN", "ICICI Bank recurring debit switch down for scheduled core maintenance window.", CustomerTier.ENTERPRISE, "Nexus Logistics Ltd", 36, 1, 0, 120, True),
        ("sub_k12e4", 499.0, "GATEWAY_ERROR_PROCESSING_TIMEOUT", "Payment gateway connection reset by peer during mandate authorization.", CustomerTier.PRO_CONSUMER, "Priya Nair", 4, 0, 0, 10, True),
        ("sub_m33f5", 3499.0, "GATEWAY_ERROR_ISSUER_DOWN", "SBI e-mandate hub returned 503 Service Unavailable. Temporary bank network issue.", CustomerTier.GROWTH_SMB, "Apex Media Group", 14, 0, 0, 25, True),
        ("sub_n88g6", 4999.0, "GATEWAY_ERROR_SWITCH_LATENCY", "Kotak Mahindra Bank CBS response latency exceeded 8000ms threshold.", CustomerTier.GROWTH_SMB, "BluePeak Analytics", 22, 1, 0, 90, True),
        ("sub_o44h7", 1999.0, "GATEWAY_ERROR_NPCI_UNAVAILABLE", "NPCI AutoPay recurring debit failed due to switch transient overload.", CustomerTier.PRO_CONSUMER, "Vikram Patel", 11, 0, 0, 45, True),
        ("sub_p91i8", 29999.0, "GATEWAY_ERROR_ISSUER_DOWN", "Axis Bank corporate mandate debit failed: 504 Gateway Timeout on issuer host.", CustomerTier.ENTERPRISE, "Global Logistics India", 42, 0, 0, 20, True),
        ("sub_q23j9", 1299.0, "GATEWAY_ERROR_PROCESSING_TIMEOUT", "Timeout in mandate token validation with Visa gateway switch.", CustomerTier.PRO_CONSUMER, "Ananya Roy", 7, 1, 0, 60, True),
        ("sub_r77k1", 5499.0, "GATEWAY_ERROR_ISSUER_DOWN", "IndusInd Bank recurring debit gateway returned 502 Bad Gateway during settlement sync.", CustomerTier.GROWTH_SMB, "Kite Interactive", 19, 0, 0, 15, True),
    ]
    for idx, (sub_id, amt, code, signal, tier, name, tenure, retries, dunning, mins_ago, rec) in enumerate(downtime_templates, start=1):
        last_att = (now - timedelta(minutes=mins_ago)).isoformat() if retries > 0 else None
        records.append(PaymentRecord(
            payment_id=f"pay_rec_dt_{idx:03d}",
            subscription_id=sub_id,
            amount=amt,
            currency="INR",
            timestamp=(now - timedelta(minutes=mins_ago)).isoformat(),
            decline_code=code,
            raw_signal=signal,
            customer_id=f"cust_{tier.lower()[:3]}_{idx:03d}",
            customer_name=name,
            customer_tier=tier,
            tenure_months=tenure,
            past_failed_retries=retries,
            dunning_attempts=dunning,
            last_attempt_at=last_att,
            preferred_payment_method="card_recurring",
            true_cause=FailureCause.BANK_DOWNTIME,
            true_recoverable=rec,
        ))

    # --- CATEGORY 2: INSUFFICIENT FUNDS (Needs retry later on payday / customer alert) ---
    funds_templates = [
        ("sub_if_01", 1999.0, "BAD_REQUEST_PAYMENT_ACCOUNT_INSUFFICIENT_BALANCE", "Decline Code 51: Insufficient funds in customer bank account.", CustomerTier.PRO_CONSUMER, "Rohan Deshmukh", 12, 0, 0, 180, True),
        ("sub_if_02", 8999.0, "BAD_REQUEST_PAYMENT_ACCOUNT_INSUFFICIENT_BALANCE", "Issuer response 51: Account balance insufficient for auto-debit charge.", CustomerTier.GROWTH_SMB, "Veloce Design Studio", 16, 1, 0, 360, True),
        ("sub_if_03", 499.0, "BAD_REQUEST_PAYMENT_ACCOUNT_INSUFFICIENT_BALANCE", "UPI AutoPay execution rejected: Available balance lower than transaction value.", CustomerTier.PRO_CONSUMER, "Meera Joshi", 6, 0, 0, 240, True),
        ("sub_if_04", 45000.0, "BAD_REQUEST_PAYMENT_ACCOUNT_INSUFFICIENT_BALANCE", "Debit failed: Insufficient funds in current account. Payday expected in 48h.", CustomerTier.ENTERPRISE, "Zenith Software Labs", 28, 1, 1, 720, True),
        ("sub_if_05", 2999.0, "BAD_REQUEST_PAYMENT_ACCOUNT_INSUFFICIENT_BALANCE", "Core banking returned code 51. Low balance alert triggered.", CustomerTier.GROWTH_SMB, "Urban Crafts Retail", 9, 2, 1, 1440, True),
        ("sub_if_06", 999.0, "BAD_REQUEST_PAYMENT_ACCOUNT_INSUFFICIENT_BALANCE", "Balance insufficient for recurring debit of INR 999.00.", CustomerTier.PRO_CONSUMER, "Siddharth Verma", 5, 0, 0, 60, True),
        ("sub_if_07", 12999.0, "BAD_REQUEST_PAYMENT_ACCOUNT_INSUFFICIENT_BALANCE", "Current account overdraft limit exhausted. Debit rejected.", CustomerTier.GROWTH_SMB, "Alpha Infratech", 20, 1, 0, 480, True),
        ("sub_if_08", 499.0, "BAD_REQUEST_PAYMENT_ACCOUNT_INSUFFICIENT_BALANCE", "Prepaid card / savings account low balance.", CustomerTier.FREE_TRIAL, "Kavita Rao", 1, 2, 2, 2880, False),  # Exhausted dunning & retries
        ("sub_if_09", 3999.0, "BAD_REQUEST_PAYMENT_ACCOUNT_INSUFFICIENT_BALANCE", "Insufficient funds. Customer has 100% on-time historical payment record.", CustomerTier.GROWTH_SMB, "CloudMatrix Solutions", 24, 0, 0, 120, True),
        ("sub_if_10", 1499.0, "BAD_REQUEST_PAYMENT_ACCOUNT_INSUFFICIENT_BALANCE", "Card limit exceeded / account balance below minimum debit floor.", CustomerTier.PRO_CONSUMER, "Deepak Gupta", 15, 1, 1, 600, True),
        ("sub_if_11", 5999.0, "BAD_REQUEST_PAYMENT_ACCOUNT_INSUFFICIENT_BALANCE", "Insufficient balance on month-end recurring debit.", CustomerTier.GROWTH_SMB, "Prime Logistics", 11, 0, 0, 90, True),
        ("sub_if_12", 2499.0, "BAD_REQUEST_PAYMENT_ACCOUNT_INSUFFICIENT_BALANCE", "Balance low; customer requested salary date alignment.", CustomerTier.PRO_CONSUMER, "Neha Kapoor", 14, 1, 0, 300, True),
    ]
    for idx, (sub_id, amt, code, signal, tier, name, tenure, retries, dunning, mins_ago, rec) in enumerate(funds_templates, start=1):
        last_att = (now - timedelta(minutes=mins_ago)).isoformat() if retries > 0 else None
        records.append(PaymentRecord(
            payment_id=f"pay_rec_if_{idx:03d}",
            subscription_id=sub_id,
            amount=amt,
            currency="INR",
            timestamp=(now - timedelta(minutes=mins_ago)).isoformat(),
            decline_code=code,
            raw_signal=signal,
            customer_id=f"cust_if_{idx:03d}",
            customer_name=name,
            customer_tier=tier,
            tenure_months=tenure,
            past_failed_retries=retries,
            dunning_attempts=dunning,
            last_attempt_at=last_att,
            preferred_payment_method="card_recurring",
            true_cause=FailureCause.INSUFFICIENT_FUNDS,
            true_recoverable=rec,
        ))

    # --- CATEGORY 3: CARD EXPIRED (Requires card update prompt) ---
    expired_templates = [
        ("sub_exp_01", 1499.0, "BAD_REQUEST_PAYMENT_CARD_EXPIRED", "Decline Code 54: Card expired. Token authorization rejected by Mastercard switch.", CustomerTier.PRO_CONSUMER, "Aditya Iyer", 24, 0, 0, 300, True),
        ("sub_exp_02", 7999.0, "BAD_REQUEST_PAYMENT_CARD_EXPIRED", "Card expiration date 08/26 has lapsed. Tokenization lifecycle expired.", CustomerTier.GROWTH_SMB, "Silverline Media", 18, 1, 0, 600, True),
        ("sub_exp_03", 999.0, "BAD_REQUEST_PAYMENT_CARD_EXPIRED", "Visa Token Management Service returned token expired status.", CustomerTier.PRO_CONSUMER, "Pooja Hegde", 10, 0, 0, 150, True),
        ("sub_exp_04", 19999.0, "BAD_REQUEST_PAYMENT_CARD_EXPIRED", "Corporate Amex card expired on file. Renewal token not issued.", CustomerTier.ENTERPRISE, "Vertex Consulting", 32, 0, 1, 400, True),
        ("sub_exp_05", 2999.0, "BAD_REQUEST_PAYMENT_CARD_EXPIRED", "Decline 54: Expired card credentials. Customer needs to re-enter new expiry date.", CustomerTier.GROWTH_SMB, "Spark Digital", 13, 0, 0, 80, True),
        ("sub_exp_06", 499.0, "BAD_REQUEST_PAYMENT_CARD_EXPIRED", "Card validity period expired. RBI tokenized credential expired.", CustomerTier.PRO_CONSUMER, "Rajesh Khanna", 7, 1, 0, 500, True),
        ("sub_exp_07", 12499.0, "BAD_REQUEST_PAYMENT_CARD_EXPIRED", "Subscription mandate failed due to expired debit card on record.", CustomerTier.GROWTH_SMB, "InnoTech Systems", 21, 0, 0, 200, True),
        ("sub_exp_08", 499.0, "BAD_REQUEST_PAYMENT_CARD_EXPIRED", "Card expired. Trial user with inactive login session for 60 days.", CustomerTier.FREE_TRIAL, "Karan Singhal", 2, 2, 2, 1440, False),
        ("sub_exp_09", 3499.0, "BAD_REQUEST_PAYMENT_CARD_EXPIRED", "Payment token expired. Auto-renewal failed.", CustomerTier.GROWTH_SMB, "Harbor Solutions", 15, 0, 0, 90, True),
        ("sub_exp_10", 1899.0, "BAD_REQUEST_PAYMENT_CARD_EXPIRED", "Decline Code 54: Card expired at midnight.", CustomerTier.PRO_CONSUMER, "Sunita Menon", 19, 0, 0, 240, True),
    ]
    for idx, (sub_id, amt, code, signal, tier, name, tenure, retries, dunning, mins_ago, rec) in enumerate(expired_templates, start=1):
        last_att = (now - timedelta(minutes=mins_ago)).isoformat() if retries > 0 else None
        records.append(PaymentRecord(
            payment_id=f"pay_rec_exp_{idx:03d}",
            subscription_id=sub_id,
            amount=amt,
            currency="INR",
            timestamp=(now - timedelta(minutes=mins_ago)).isoformat(),
            decline_code=code,
            raw_signal=signal,
            customer_id=f"cust_exp_{idx:03d}",
            customer_name=name,
            customer_tier=tier,
            tenure_months=tenure,
            past_failed_retries=retries,
            dunning_attempts=dunning,
            last_attempt_at=last_att,
            preferred_payment_method="card_recurring",
            true_cause=FailureCause.CARD_EXPIRED,
            true_recoverable=rec,
        ))

    # --- CATEGORY 4: ISSUER DECLINE (Mandate limit, international restriction, alternate method needed) ---
    issuer_templates = [
        ("sub_iss_01", 15000.0, "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK", "Decline 05: Do Not Honor. Recurring debit amount exceeds RBI e-mandate limit without AFA.", CustomerTier.ENTERPRISE, "Paramount Global Labs", 30, 0, 0, 180, True),
        ("sub_iss_02", 4999.0, "BAD_REQUEST_PAYMENT_AUTHENTICATION_FAILED", "Mandate 3DS step-up authentication failed. Card issuer requires re-consent.", CustomerTier.GROWTH_SMB, "Brightwave Media", 14, 0, 0, 240, True),
        ("sub_iss_03", 2499.0, "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK", "Bank decline 57: Transaction not permitted on this debit card mandate tier.", CustomerTier.PRO_CONSUMER, "Gaurav Sen", 9, 1, 0, 400, True),
        ("sub_iss_04", 35000.0, "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK", "Issuer policy: International recurring mandate disabled on card by customer.", CustomerTier.ENTERPRISE, "Starlight Ventures", 26, 0, 0, 90, True),
        ("sub_iss_05", 1999.0, "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK", "Decline 05: Generic issuer decline. Customer needs to enable online e-mandates.", CustomerTier.PRO_CONSUMER, "Divya Suresh", 8, 1, 0, 320, True),
        ("sub_iss_06", 6499.0, "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK", "Transaction rejected: Merchant category code restricted by card issuer policy.", CustomerTier.GROWTH_SMB, "Enigma Software", 17, 0, 0, 110, True),
        ("sub_iss_07", 999.0, "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK", "Recurring mandate cancelled by user at bank netbanking portal.", CustomerTier.PRO_CONSUMER, "Nikhil Bhatt", 12, 1, 1, 700, True),
        ("sub_iss_08", 45000.0, "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK", "Corporate credit card policy restricts non-approved vendor recurrent mandates.", CustomerTier.ENTERPRISE, "Titanium Cloud Corp", 38, 0, 0, 150, True),
        ("sub_iss_09", 2999.0, "BAD_REQUEST_PAYMENT_AUTHENTICATION_FAILED", "Mandate notification sent to user but not acknowledged within 24h pre-debit window.", CustomerTier.GROWTH_SMB, "Crestview Labs", 11, 0, 0, 200, True),
        ("sub_iss_10", 1299.0, "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK", "Decline 57: Netbanking mandate mandate registration rejected by issuer.", CustomerTier.PRO_CONSUMER, "Varun Agarwal", 6, 0, 0, 60, True),
        ("sub_iss_11", 5499.0, "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK", "Daily transaction count ceiling hit on customer debit card account.", CustomerTier.GROWTH_SMB, "Zenith Studio", 15, 1, 0, 350, True),
    ]
    for idx, (sub_id, amt, code, signal, tier, name, tenure, retries, dunning, mins_ago, rec) in enumerate(issuer_templates, start=1):
        last_att = (now - timedelta(minutes=mins_ago)).isoformat() if retries > 0 else None
        records.append(PaymentRecord(
            payment_id=f"pay_rec_iss_{idx:03d}",
            subscription_id=sub_id,
            amount=amt,
            currency="INR",
            timestamp=(now - timedelta(minutes=mins_ago)).isoformat(),
            decline_code=code,
            raw_signal=signal,
            customer_id=f"cust_iss_{idx:03d}",
            customer_name=name,
            customer_tier=tier,
            tenure_months=tenure,
            past_failed_retries=retries,
            dunning_attempts=dunning,
            last_attempt_at=last_att,
            preferred_payment_method="card_recurring",
            true_cause=FailureCause.ISSUER_DECLINE,
            true_recoverable=rec,
        ))

    # --- CATEGORY 5: RISK BLOCK / FRAUD (Must be gated by Sentinel, zero blind retry) ---
    risk_templates = [
        ("sub_rsk_01", 19999.0, "RISK_FRAUD_CHECK_FAILED", "Razorpay Thirdwatch AI Risk Score 94/100: Suspicious velocity, high chargeback risk.", CustomerTier.FREE_TRIAL, "Anil Kumar (Suspicious)", 1, 0, 0, 45, False),
        ("sub_rsk_02", 4999.0, "BAD_REQUEST_PAYMENT_RISK_DECLINED", "Card flagged as stolen / lost by issuer fraud engine (Decline 43).", CustomerTier.FREE_TRIAL, "Shyam Sundar", 1, 0, 0, 120, False),
        ("sub_rsk_03", 29999.0, "RISK_FRAUD_CHECK_FAILED", "IP geolocation anomaly + card bin from sanctioned high-risk entity.", CustomerTier.FREE_TRIAL, "Bot Account 902", 0, 0, 0, 20, False),
        ("sub_rsk_04", 1499.0, "BAD_REQUEST_PAYMENT_RISK_DECLINED", "Multiple rapid mandate creations across 5 virtual cards within 10 minutes.", CustomerTier.FREE_TRIAL, "Test Bot 11", 0, 1, 0, 30, False),
        ("sub_rsk_05", 9999.0, "RISK_FRAUD_CHECK_FAILED", "Card velocity trigger: 8 consecutive failure attempts across unrelated merchant IDs.", CustomerTier.FREE_TRIAL, "Scammer Entity X", 1, 2, 0, 90, False),
        ("sub_rsk_06", 3500.0, "BAD_REQUEST_PAYMENT_RISK_DECLINED", "Chargeback threshold exceeded on card fingerprint. Auto-blocked by Risk Shield.", CustomerTier.PRO_CONSUMER, "Devendra P.", 2, 0, 0, 15, False),
        ("sub_rsk_07", 12000.0, "RISK_FRAUD_CHECK_FAILED", "Suspicious device fingerprint + spoofed user agent during payment verification.", CustomerTier.FREE_TRIAL, "Unknown Actor", 1, 1, 0, 50, False),
        ("sub_rsk_08", 45000.0, "RISK_FRAUD_CHECK_FAILED", "Account takeover suspected: registered email changed 1 hour before subscription renewal.", CustomerTier.ENTERPRISE, "Compromised Account Ltd", 12, 0, 0, 80, False),
        ("sub_rsk_09", 2499.0, "BAD_REQUEST_PAYMENT_RISK_DECLINED", "Issuer risk block: Card reported compromised in recent data breach alert.", CustomerTier.PRO_CONSUMER, "Kishore Jain", 5, 0, 0, 110, False),
        ("sub_rsk_10", 7999.0, "RISK_FRAUD_CHECK_FAILED", "High velocity fraudulent card testing pattern detected by gateway heuristic.", CustomerTier.FREE_TRIAL, "Shadow Entity 44", 0, 2, 0, 40, False),
        ("sub_rsk_11", 1500.0, "BAD_REQUEST_PAYMENT_RISK_DECLINED", "Mandate security token mismatch; flagged by network integrity filter.", CustomerTier.PRO_CONSUMER, "Vijay Shinde", 3, 0, 0, 65, False),
        ("sub_rsk_12", 50000.0, "RISK_FRAUD_CHECK_FAILED", "Critical risk alert: Unauthorized recurring charge attempt on corporate credit line.", CustomerTier.GROWTH_SMB, "Stolen Corp Card", 1, 0, 0, 10, False),
    ]
    for idx, (sub_id, amt, code, signal, tier, name, tenure, retries, dunning, mins_ago, rec) in enumerate(risk_templates, start=1):
        last_att = (now - timedelta(minutes=mins_ago)).isoformat() if retries > 0 else None
        records.append(PaymentRecord(
            payment_id=f"pay_rec_rsk_{idx:03d}",
            subscription_id=sub_id,
            amount=amt,
            currency="INR",
            timestamp=(now - timedelta(minutes=mins_ago)).isoformat(),
            decline_code=code,
            raw_signal=signal,
            customer_id=f"cust_rsk_{idx:03d}",
            customer_name=name,
            customer_tier=tier,
            tenure_months=tenure,
            past_failed_retries=retries,
            dunning_attempts=dunning,
            last_attempt_at=last_att,
            preferred_payment_method="card_recurring",
            true_cause=FailureCause.RISK_BLOCK,
            true_recoverable=rec,
        ))

    return records


# Pre-generated in-memory singleton dataset
BENCHMARK_DATASET: List[PaymentRecord] = generate_synthetic_dataset()
