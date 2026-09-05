"""
Database & Persistence Layer for Rebound — AI Revenue Recovery Agent
Supports:
1. Supabase (PostgreSQL via official Supabase client) when SUPABASE_URL and SUPABASE_KEY are provided.
2. File-based SQLite (backend/data/rebound.db) for local offline/testing execution.
Persists payments, diagnoses, strategies, gate decisions, outcomes, audit logs,
policy configuration, merchant catalog, and queue session state across restarts.
"""

import os
import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger("rebound.db")

# Path configuration for SQLite fallback
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SQLITE_PATH = os.path.join(DATA_DIR, "rebound.db")

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


class DatabaseManager:
    """Unified Database Manager handling persistence across Supabase and SQLite."""

    def __init__(self):
        self.backend = "supabase" if (SUPABASE_URL and SUPABASE_KEY) else "sqlite"
        self._supabase_client = None
        if self.backend == "supabase":
            try:
                from supabase import create_client, Client
                self._supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("Connected to Supabase PostgreSQL at %s", SUPABASE_URL)
            except Exception as e:
                logger.error("Failed to connect to Supabase: %s. Falling back to local SQLite.", e)
                self.backend = "sqlite"

        if self.backend == "sqlite":
            self._init_sqlite()

    def _get_sqlite_conn(self) -> sqlite3.Connection:
        os.makedirs(DATA_DIR, exist_ok=True)
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_sqlite(self):
        """Initializes SQLite tables matching the Supabase schema."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS policy_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            max_retries INTEGER NOT NULL DEFAULT 3,
            cooldown_hours REAL NOT NULL DEFAULT 4.0,
            min_ev REAL NOT NULL DEFAULT 0.0,
            max_recovery_amount REAL NOT NULL DEFAULT 500000.0,
            min_amount REAL NOT NULL DEFAULT 1.0,
            max_escalations INTEGER NOT NULL DEFAULT 2,
            max_permissible_risk REAL NOT NULL DEFAULT 0.70,
            updated_at TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS merchant_catalog (
            sku TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            in_stock INTEGER NOT NULL DEFAULT 1,
            category TEXT NOT NULL,
            requires_permission TEXT NOT NULL,
            description TEXT,
            updated_at TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id TEXT PRIMARY KEY,
            subscription_id TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'INR',
            timestamp TEXT NOT NULL,
            decline_code TEXT NOT NULL,
            raw_signal TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            customer_tier TEXT NOT NULL,
            tenure_months INTEGER NOT NULL,
            past_failed_retries INTEGER NOT NULL,
            dunning_attempts INTEGER NOT NULL,
            last_attempt_at TEXT,
            preferred_payment_method TEXT NOT NULL,
            true_cause TEXT NOT NULL,
            true_recoverable INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS diagnoses (
            payment_id TEXT PRIMARY KEY,
            diagnosed_cause TEXT NOT NULL,
            confidence REAL NOT NULL,
            reasoning TEXT NOT NULL,
            key_signals TEXT NOT NULL,
            provider TEXT NOT NULL,
            model_name TEXT NOT NULL,
            is_llm_derived INTEGER NOT NULL,
            raw_model_response TEXT,
            diagnosed_at TEXT NOT NULL,
            FOREIGN KEY (payment_id) REFERENCES payments (payment_id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            rank INTEGER NOT NULL,
            probability REAL NOT NULL,
            expected_value REAL NOT NULL,
            cost REAL NOT NULL,
            reasoning_text TEXT NOT NULL,
            recommended_delay_hours INTEGER NOT NULL DEFAULT 0,
            formula_applied TEXT NOT NULL,
            FOREIGN KEY (payment_id) REFERENCES payments (payment_id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS gate_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id TEXT NOT NULL,
            strategy_chosen TEXT NOT NULL,
            approved INTEGER NOT NULL,
            policy_code TEXT NOT NULL,
            reason TEXT NOT NULL,
            confidence REAL NOT NULL,
            expected_value REAL NOT NULL,
            constraints_evaluated TEXT NOT NULL,
            evaluated_at TEXT NOT NULL,
            FOREIGN KEY (payment_id) REFERENCES payments (payment_id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id TEXT NOT NULL,
            action TEXT NOT NULL,
            final_status TEXT NOT NULL,
            recovered_amount REAL NOT NULL DEFAULT 0.0,
            transaction_id TEXT,
            gateway_code TEXT NOT NULL,
            gateway_message TEXT NOT NULL,
            execution_backend TEXT NOT NULL,
            executed_at TEXT NOT NULL,
            FOREIGN KEY (payment_id) REFERENCES payments (payment_id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            event_id TEXT PRIMARY KEY,
            payment_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            human_readable_reasoning TEXT NOT NULL,
            decision TEXT,
            details TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_payment ON audit_log (payment_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_time ON audit_log (timestamp DESC)")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS queue_items (
            item_id TEXT PRIMARY KEY,
            payment_id TEXT NOT NULL,
            diagnosed_cause TEXT NOT NULL,
            top_ranked_strategy TEXT NOT NULL,
            group_key TEXT NOT NULL,
            amount REAL NOT NULL,
            customer_name TEXT NOT NULL,
            customer_tier TEXT NOT NULL,
            item_type TEXT NOT NULL,
            is_borderline INTEGER NOT NULL,
            advisory_note TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING',
            created_at TEXT NOT NULL,
            FOREIGN KEY (payment_id) REFERENCES payments (payment_id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS queue_session_stats (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            first_run_loaded INTEGER NOT NULL DEFAULT 0,
            auto_handled_count INTEGER NOT NULL DEFAULT 0,
            auto_handled_amount REAL NOT NULL DEFAULT 0.0,
            auto_handled_net REAL NOT NULL DEFAULT 0.0,
            session_recovered_count INTEGER NOT NULL DEFAULT 0,
            session_recovered_amount REAL NOT NULL DEFAULT 0.0,
            updated_at TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            subscription_id TEXT PRIMARY KEY,
            internal_customer_id TEXT NOT NULL,
            razorpay_customer_id TEXT NOT NULL,
            plan_name TEXT NOT NULL,
            razorpay_plan_id TEXT NOT NULL,
            status TEXT NOT NULL,
            short_url TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            raw_response TEXT NOT NULL
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_cust ON subscriptions (internal_customer_id)")

        cursor.execute("""
        INSERT OR IGNORE INTO policy_config (id, max_retries, cooldown_hours, min_ev, max_recovery_amount, min_amount, max_escalations, max_permissible_risk, updated_at)
        VALUES (1, 3, 4.0, 0.0, 500000.0, 1.0, 2, 0.70, ?)
        """, (datetime.now(timezone.utc).isoformat(),))

        cursor.execute("""
        INSERT OR IGNORE INTO queue_session_stats (id, first_run_loaded, auto_handled_count, auto_handled_amount, auto_handled_net, session_recovered_count, session_recovered_amount, updated_at)
        VALUES (1, 0, 0, 0.0, 0.0, 0, 0.0, ?)
        """, (datetime.now(timezone.utc).isoformat(),))

        conn.commit()
        conn.close()

    # ------------------------------------------------------------------------
    # Persistence Methods (Supabase with SQLite fallback)
    # ------------------------------------------------------------------------

    def save_payment(self, payment_dict: Dict[str, Any]):
        """Persists a payment record."""
        if self.backend == "supabase" and self._supabase_client:
            try:
                self._supabase_client.table("payments").upsert(payment_dict).execute()
                return
            except Exception as e:
                logger.error("Supabase write error on payments: %s", e)

        # SQLite fallback / default
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO payments (
            payment_id, subscription_id, amount, currency, timestamp, decline_code,
            raw_signal, customer_id, customer_name, customer_tier, tenure_months,
            past_failed_retries, dunning_attempts, last_attempt_at, preferred_payment_method,
            true_cause, true_recoverable, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payment_dict["payment_id"], payment_dict["subscription_id"], payment_dict["amount"],
            payment_dict.get("currency", "INR"), payment_dict["timestamp"], payment_dict["decline_code"],
            payment_dict["raw_signal"], payment_dict["customer_id"], payment_dict["customer_name"],
            payment_dict["customer_tier"], payment_dict["tenure_months"], payment_dict["past_failed_retries"],
            payment_dict["dunning_attempts"], payment_dict.get("last_attempt_at"),
            payment_dict.get("preferred_payment_method", "card_recurring"),
            str(payment_dict.get("true_cause", "")),
            1 if payment_dict.get("true_recoverable", True) else 0,
            datetime.now(timezone.utc).isoformat()
        ))
        conn.commit()
        conn.close()

    def save_diagnosis(self, diag_dict: Dict[str, Any]):
        """Persists a diagnosis record."""
        if self.backend == "supabase" and self._supabase_client:
            try:
                self._supabase_client.table("diagnoses").upsert(diag_dict).execute()
                return
            except Exception as e:
                logger.error("Supabase write error on diagnoses: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO diagnoses (
            payment_id, diagnosed_cause, confidence, reasoning, key_signals,
            provider, model_name, is_llm_derived, raw_model_response, diagnosed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            diag_dict["payment_id"], diag_dict["diagnosed_cause"], diag_dict["confidence"],
            diag_dict["reasoning"], json.dumps(diag_dict.get("key_signals", [])),
            diag_dict.get("provider", "unknown"), diag_dict.get("model_name", "unknown"),
            1 if diag_dict.get("is_llm_derived", False) else 0,
            diag_dict.get("raw_model_response"),
            diag_dict.get("diagnosed_at", datetime.now(timezone.utc).isoformat())
        ))
        conn.commit()
        conn.close()

    def save_strategy(self, strat_dict: Dict[str, Any]):
        """Persists a strategy candidate record."""
        if self.backend == "supabase" and self._supabase_client:
            try:
                self._supabase_client.table("strategies").insert(strat_dict).execute()
                return
            except Exception as e:
                logger.error("Supabase write error on strategies: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO strategies (
            payment_id, strategy_name, rank, probability, expected_value,
            cost, reasoning_text, recommended_delay_hours, formula_applied
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            strat_dict["payment_id"], strat_dict["strategy_name"], strat_dict["rank"],
            strat_dict["probability"], strat_dict["expected_value"], strat_dict["cost"],
            strat_dict["reasoning_text"], strat_dict.get("recommended_delay_hours", 0),
            strat_dict.get("formula_applied", "")
        ))
        conn.commit()
        conn.close()

    def save_gate_decision(self, dec_dict: Dict[str, Any]):
        """Persists a Sentinel gate decision record."""
        if self.backend == "supabase" and self._supabase_client:
            try:
                self._supabase_client.table("gate_decisions").insert(dec_dict).execute()
                return
            except Exception as e:
                logger.error("Supabase write error on gate_decisions: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO gate_decisions (
            payment_id, strategy_chosen, approved, policy_code, reason,
            confidence, expected_value, constraints_evaluated, evaluated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dec_dict["payment_id"], dec_dict["strategy_chosen"],
            1 if dec_dict["approved"] else 0, dec_dict["policy_code"],
            dec_dict["reason"], dec_dict["confidence"], dec_dict["expected_value"],
            json.dumps(dec_dict.get("constraints_evaluated", {})),
            dec_dict.get("evaluated_at", datetime.now(timezone.utc).isoformat())
        ))
        conn.commit()
        conn.close()

    def save_outcome(self, outcome_dict: Dict[str, Any]):
        """Persists a gateway execution outcome."""
        if self.backend == "supabase" and self._supabase_client:
            try:
                self._supabase_client.table("outcomes").insert(outcome_dict).execute()
                return
            except Exception as e:
                logger.error("Supabase write error on outcomes: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO outcomes (
            payment_id, action, final_status, recovered_amount, transaction_id,
            gateway_code, gateway_message, execution_backend, executed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            outcome_dict["payment_id"], outcome_dict["action"], outcome_dict["final_status"],
            outcome_dict.get("recovered_amount", 0.0), outcome_dict.get("transaction_id"),
            outcome_dict.get("gateway_code", "200_OK"), outcome_dict.get("gateway_message", ""),
            outcome_dict.get("execution_backend", "razorpay_test_stub"),
            outcome_dict.get("executed_at", datetime.now(timezone.utc).isoformat())
        ))
        conn.commit()
        conn.close()

    def save_audit_log(self, log_dict: Dict[str, Any]):
        """Persists an individual audit trail event."""
        if self.backend == "supabase" and self._supabase_client:
            try:
                self._supabase_client.table("audit_log").upsert(log_dict).execute()
                return
            except Exception as e:
                logger.error("Supabase write error on audit_log: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO audit_log (
            event_id, payment_id, stage, action, status, human_readable_reasoning,
            decision, details, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_dict["event_id"], log_dict["payment_id"], log_dict["stage"],
            log_dict["action"], log_dict["status"], log_dict["human_readable_reasoning"],
            log_dict.get("decision"), json.dumps(log_dict.get("details", {})),
            log_dict["timestamp"]
        ))
        conn.commit()
        conn.close()

    def get_all_audit_logs(self, payment_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves audit logs from persistent storage."""
        if self.backend == "supabase" and self._supabase_client:
            try:
                query = self._supabase_client.table("audit_log").select("*")
                if payment_id:
                    query = query.eq("payment_id", payment_id)
                res = query.order("timestamp", desc=True).execute()
                return res.data or []
            except Exception as e:
                logger.error("Supabase read error on audit_log: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        if payment_id:
            cursor.execute("SELECT * FROM audit_log WHERE payment_id = ? ORDER BY timestamp DESC", (payment_id,))
        else:
            cursor.execute("SELECT * FROM audit_log ORDER BY timestamp DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        for r in rows:
            if isinstance(r.get("details"), str):
                try:
                    r["details"] = json.loads(r["details"])
                except Exception:
                    pass
        return rows

    # ------------------------------------------------------------------------
    # Queue Items Persistence (survives restart)
    # ------------------------------------------------------------------------

    def upsert_queue_item(self, item_dict: Dict[str, Any]):
        """Saves a review queue item into persistent storage."""
        if self.backend == "supabase" and self._supabase_client:
            try:
                self._supabase_client.table("queue_items").upsert(item_dict).execute()
                return
            except Exception as e:
                logger.error("Supabase write error on queue_items: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO queue_items (
            item_id, payment_id, diagnosed_cause, top_ranked_strategy,
            group_key, amount, customer_name, customer_tier, item_type,
            is_borderline, advisory_note, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item_dict["item_id"], item_dict["payment_id"], item_dict["diagnosed_cause"],
            item_dict["top_ranked_strategy"], item_dict["group_key"], item_dict["amount"],
            item_dict["customer_name"], item_dict["customer_tier"], item_dict.get("item_type", "recovery"),
            1 if item_dict.get("is_borderline", True) else 0,
            item_dict.get("advisory_note"), item_dict.get("status", "PENDING"),
            item_dict.get("created_at", datetime.now(timezone.utc).isoformat())
        ))
        conn.commit()
        conn.close()

    def remove_queue_item(self, item_id: str):
        """Deletes or marks resolved a review queue item."""
        if self.backend == "supabase" and self._supabase_client:
            try:
                self._supabase_client.table("queue_items").delete().eq("item_id", item_id).execute()
                return
            except Exception as e:
                logger.error("Supabase delete error on queue_items: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM queue_items WHERE item_id = ?", (item_id,))
        conn.commit()
        conn.close()

    def get_all_queue_items(self) -> List[Dict[str, Any]]:
        """Loads all pending queue items from persistent storage."""
        if self.backend == "supabase" and self._supabase_client:
            try:
                res = self._supabase_client.table("queue_items").select("*").eq("status", "PENDING").execute()
                return res.data or []
            except Exception as e:
                logger.error("Supabase read error on queue_items: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM queue_items WHERE status = 'PENDING' ORDER BY created_at ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def clear_queue_items(self):
        """Empties queue items table."""
        if self.backend == "supabase" and self._supabase_client:
            try:
                self._supabase_client.table("queue_items").delete().neq("item_id", "none").execute()
                return
            except Exception as e:
                logger.error("Supabase clear error on queue_items: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM queue_items")
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------------
    # Queue Session Stats Persistence
    # ------------------------------------------------------------------------

    def get_queue_session_stats(self) -> Dict[str, Any]:
        """Gets persistent queue session stats."""
        if self.backend == "supabase" and self._supabase_client:
            try:
                res = self._supabase_client.table("queue_session_stats").select("*").eq("id", 1).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                logger.error("Supabase read error on queue_session_stats: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM queue_session_stats WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return {
            "first_run_loaded": 0, "auto_handled_count": 0, "auto_handled_amount": 0.0,
            "session_recovered_count": 0, "session_recovered_amount": 0.0
        }

    def update_queue_session_stats(self, stats: Dict[str, Any]):
        """Updates persistent queue session stats."""
        stats["updated_at"] = datetime.now(timezone.utc).isoformat()
        stats["id"] = 1
        if self.backend == "supabase" and self._supabase_client:
            try:
                self._supabase_client.table("queue_session_stats").upsert(stats).execute()
                return
            except Exception as e:
                logger.error("Supabase write error on queue_session_stats: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE queue_session_stats SET
            first_run_loaded = ?, auto_handled_count = ?, auto_handled_amount = ?,
            auto_handled_net = ?, session_recovered_count = ?, session_recovered_amount = ?,
            updated_at = ?
        WHERE id = 1
        """, (
            1 if stats.get("first_run_loaded", False) else 0,
            stats.get("auto_handled_count", 0),
            stats.get("auto_handled_amount", 0.0),
            stats.get("auto_handled_net", 0.0),
            stats.get("session_recovered_count", 0),
            stats.get("session_recovered_amount", 0.0),
            stats["updated_at"]
        ))
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------------
    # Policy Config & Catalog Persistence
    # ------------------------------------------------------------------------

    def get_policy_config(self) -> Dict[str, Any]:
        """Gets merchant policy configuration."""
        if self.backend == "supabase" and self._supabase_client:
            try:
                res = self._supabase_client.table("policy_config").select("*").eq("id", 1).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                logger.error("Supabase read error on policy_config: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM policy_config WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else {}

    def update_policy_config(self, cfg: Dict[str, Any]):
        """Updates merchant policy configuration."""
        cfg["id"] = 1
        cfg["updated_at"] = datetime.now(timezone.utc).isoformat()
        if self.backend == "supabase" and self._supabase_client:
            try:
                self._supabase_client.table("policy_config").upsert(cfg).execute()
                return
            except Exception as e:
                logger.error("Supabase write error on policy_config: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE policy_config SET
            max_retries = ?, cooldown_hours = ?, min_ev = ?, max_recovery_amount = ?,
            min_amount = ?, max_escalations = ?, max_permissible_risk = ?, updated_at = ?
        WHERE id = 1
        """, (
            cfg.get("max_retries", 3), cfg.get("cooldown_hours", 4.0), cfg.get("min_ev", 0.0),
            cfg.get("max_recovery_amount", 500000.0), cfg.get("min_amount", 1.0),
            cfg.get("max_escalations", 2), cfg.get("max_permissible_risk", 0.70), cfg["updated_at"]
        ))
        conn.commit()
        conn.close()

    def get_catalog(self) -> List[Dict[str, Any]]:
        """Gets active merchant catalog items."""
        if self.backend == "supabase" and self._supabase_client:
            try:
                res = self._supabase_client.table("merchant_catalog").select("*").execute()
                if res.data:
                    return res.data
            except Exception as e:
                logger.error("Supabase read error on merchant_catalog: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM merchant_catalog")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def upsert_catalog(self, items: List[Dict[str, Any]]):
        """Updates catalog items in database."""
        now_str = datetime.now(timezone.utc).isoformat()
        for item in items:
            item["updated_at"] = now_str
            if self.backend == "supabase" and self._supabase_client:
                try:
                    self._supabase_client.table("merchant_catalog").upsert(item).execute()
                    continue
                except Exception as e:
                    logger.error("Supabase write error on merchant_catalog: %s", e)

            conn = self._get_sqlite_conn()
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO merchant_catalog (
                sku, name, price, in_stock, category, requires_permission, description, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item["sku"], item["name"], item["price"], 1 if item.get("in_stock", True) else 0,
                item.get("category", "General"), item.get("requires_permission", "procurement.saas.basic"),
                item.get("description", ""), now_str
            ))
            conn.commit()
            conn.close()

    def save_subscription(self, data: Dict[str, Any]):
        """Persists a provisioned subscription record."""
        now_str = datetime.now(timezone.utc).isoformat()
        raw_resp = data.get("raw_response", {})
        raw_str = json.dumps(raw_resp) if isinstance(raw_resp, dict) else str(raw_resp)

        if self.backend == "supabase" and self._supabase_client:
            try:
                sub_payload = {
                    "subscription_id": data["subscription_id"],
                    "internal_customer_id": data["internal_customer_id"],
                    "razorpay_customer_id": data["razorpay_customer_id"],
                    "plan_name": data["plan_name"],
                    "razorpay_plan_id": data["razorpay_plan_id"],
                    "status": data["status"],
                    "short_url": data["short_url"],
                    "created_at": data.get("created_at", now_str),
                    "updated_at": now_str,
                    "raw_response": raw_str,
                }
                self._supabase_client.table("subscriptions").upsert(sub_payload).execute()
                return
            except Exception as e:
                logger.error("Supabase write error on subscriptions: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO subscriptions (
            subscription_id, internal_customer_id, razorpay_customer_id, plan_name,
            razorpay_plan_id, status, short_url, created_at, updated_at, raw_response
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["subscription_id"], data["internal_customer_id"], data["razorpay_customer_id"],
            data["plan_name"], data["razorpay_plan_id"], data["status"], data["short_url"],
            data.get("created_at", now_str), now_str, raw_str
        ))
        conn.commit()
        conn.close()

    def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a subscription by its Razorpay subscription_id."""
        if self.backend == "supabase" and self._supabase_client:
            try:
                res = self._supabase_client.table("subscriptions").select("*").eq("subscription_id", subscription_id).execute()
                if res.data:
                    row = res.data[0]
                    if isinstance(row.get("raw_response"), str):
                        try:
                            row["raw_response"] = json.loads(row["raw_response"])
                        except Exception:
                            pass
                    return row
            except Exception as e:
                logger.error("Supabase read error on subscriptions: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions WHERE subscription_id = ?", (subscription_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            res = dict(row)
            try:
                res["raw_response"] = json.loads(res["raw_response"])
            except Exception:
                pass
            return res
        return None

    def get_all_subscriptions(self) -> List[Dict[str, Any]]:
        """Retrieves all persisted subscriptions."""
        if self.backend == "supabase" and self._supabase_client:
            try:
                res = self._supabase_client.table("subscriptions").select("*").order("created_at", desc=True).execute()
                if res.data:
                    for row in res.data:
                        if isinstance(row.get("raw_response"), str):
                            try:
                                row["raw_response"] = json.loads(row["raw_response"])
                            except Exception:
                                pass
                    return res.data
            except Exception as e:
                logger.error("Supabase read error on subscriptions: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions ORDER BY created_at DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        for r in rows:
            try:
                r["raw_response"] = json.loads(r["raw_response"])
            except Exception:
                pass
        return rows

    def update_subscription_status(self, subscription_id: str, status: str):
        """Updates subscription status on webhook or polling events."""
        now_str = datetime.now(timezone.utc).isoformat()
        if self.backend == "supabase" and self._supabase_client:
            try:
                self._supabase_client.table("subscriptions").update({"status": status, "updated_at": now_str}).eq("subscription_id", subscription_id).execute()
                return
            except Exception as e:
                logger.error("Supabase update error on subscriptions: %s", e)

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE subscriptions SET status = ?, updated_at = ? WHERE subscription_id = ?
        """, (status, now_str, subscription_id))
        conn.commit()
        conn.close()


# Global database manager instance
db_manager = DatabaseManager()

