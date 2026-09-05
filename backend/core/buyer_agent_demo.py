"""
The Sentinel Reuse Demo — Autonomous Buyer Agent Demonstration
Evaluates autonomous AI buyer agent purchase requests against an uploadable merchant catalog
using the EXACT SAME UNMODIFIED Sentinel policy engine.
Demonstrates structural generality: The Sentinel gates any agent touching money.
"""

from typing import List, Dict, Any, Optional
import re
from backend.models.schemas import (
    MerchantCatalogItem,
    BuyerCatalogItem,
    BuyerAgentPurchaseRequest,
    ParsedBuyerIntent,
    PolicyRequest,
    SentinelDecision,
)
from backend.core.sentinel import the_sentinel


DEFAULT_CATALOG_ITEMS: List[MerchantCatalogItem] = [
    MerchantCatalogItem(
        sku="sku_saas_seat",
        name="Developer IDE & Copilot Seat (1 Month)",
        price=3500.0,
        in_stock=True,
        category="SaaS_Tools",
        requires_permission="procurement.saas.basic",
        description="Standard developer tooling subscription seat.",
    ),
    MerchantCatalogItem(
        sku="sku_gpu_cluster",
        name="On-Demand H100 GPU Cluster (24h Burst)",
        price=48000.0,
        in_stock=True,
        category="Cloud_Compute",
        requires_permission="procurement.infra.high_value",
        description="High-throughput GPU instance for fine-tuning workloads.",
    ),
    MerchantCatalogItem(
        sku="sku_enterprise_llm",
        name="Enterprise LLM Token Allocation (100M Tokens)",
        price=125000.0,
        in_stock=True,
        category="AI_Inference",
        requires_permission="procurement.ai_compute.enterprise",
        description="Tier-1 foundation model inference volume.",
    ),
    MerchantCatalogItem(
        sku="sku_security_scan",
        name="Automated Cloud Security Audit Suite",
        price=18000.0,
        in_stock=True,
        category="Security",
        requires_permission="procurement.security.tools",
        description="SOC2 compliance scanning & continuous pen-testing tool.",
    ),
    MerchantCatalogItem(
        sku="sku_analytics_out_of_stock",
        name="Enterprise Real-Time Stream Processor",
        price=22000.0,
        in_stock=False,
        category="Data_Pipelines",
        requires_permission="procurement.saas.basic",
        description="High-throughput Apache Kafka / Flink managed connector.",
    ),
]


class CatalogStore:
    """Persistent catalog store with runtime upload capability."""
    def __init__(self):
        self._catalog: List[MerchantCatalogItem] = list(DEFAULT_CATALOG_ITEMS)

    def get_catalog(self) -> List[MerchantCatalogItem]:
        return self._catalog

    def get_item(self, sku: str) -> Optional[MerchantCatalogItem]:
        for item in self._catalog:
            if item.sku.lower() == sku.lower():
                return item
        return None

    def update_catalog(self, items: List[MerchantCatalogItem]):
        self._catalog = items

    def reset_defaults(self):
        self._catalog = list(DEFAULT_CATALOG_ITEMS)


catalog_store = CatalogStore()
# Alias for backwards compatibility
MERCHANT_CATALOG = catalog_store.get_catalog()


import logging
from backend.core.llm_client import llm_client

logger = logging.getLogger("rebound.buyer_agent")

# --- CHANGE 5: Upstream Buyer Agent Intent Parser ---
def parse_buyer_intent(raw_prompt: str, catalog: Optional[List[MerchantCatalogItem]] = None) -> ParsedBuyerIntent:
    """
    Upstream intent parser that turns natural language buyer commands
    into strict structured representations BEFORE reaching The Sentinel.
    When GEMINI_API_KEY is configured:
      Uses Google Gemini to parse SKU, price, and scopes.
    When unconfigured:
      Uses deterministic catalog matching with is_llm_derived=False and parsing_confidence=0.0.
    """
    active_catalog = catalog or catalog_store.get_catalog()
    catalog_dicts = [item.model_dump() for item in active_catalog]

    # 1. Try real LLM intent parsing if configured
    if llm_client.is_configured():
        try:
            llm_result = llm_client.parse_buyer_agent_intent(raw_prompt, catalog_dicts)
            matched_sku = llm_result.get("sku", active_catalog[0].sku if active_catalog else "sku_saas_seat")
            requested_amt = float(llm_result.get("requested_amount", 0.0))
            scopes = llm_result.get("agent_permission_scope", ["procurement.saas.basic"])
            conf = float(llm_result.get("confidence", 0.85))
            advisory = llm_result.get("advisory_note", f"Parsed by {llm_client.provider}")

            provider_tag = "Gemini" if llm_result.get("_provider") == "gemini" else "AI"
            return ParsedBuyerIntent(
                sku=matched_sku,
                requested_amount=requested_amt,
                agent_permission_scope=scopes,
                advisory_note=f"[AI {provider_tag}] {advisory}",
                parsing_confidence=conf,
                raw_intent=raw_prompt,
                is_llm_derived=True,
                provider=llm_result.get("_provider", llm_client.provider),
            )
        except Exception as e:
            logger.error("LLM buyer agent intent parsing failed: %s. Falling back to regex parser.", e, exc_info=True)

    # 2. Deterministic regex / catalog fallback (honestly flagged: confidence=0.0, is_llm_derived=False)
    raw_lower = raw_prompt.lower()
    matched_sku = None
    for item in active_catalog:
        if item.sku.lower() in raw_lower or item.name.lower() in raw_lower:
            matched_sku = item.sku
            break
    
    if not matched_sku:
        matched_sku = active_catalog[0].sku if active_catalog else "sku_saas_seat"
    
    item = next((i for i in active_catalog if i.sku == matched_sku), None)
    default_price = item.price if item else 3500.0
    
    amount_matches = re.findall(r"₹?\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)", raw_prompt)
    if amount_matches:
        try:
            parsed_amt = float(amount_matches[0].replace(",", ""))
        except ValueError:
            parsed_amt = default_price
    else:
        parsed_amt = default_price

    scope = [item.requires_permission] if (item and item.requires_permission) else ["procurement.saas.basic"]
    
    return ParsedBuyerIntent(
        sku=matched_sku,
        requested_amount=parsed_amt,
        agent_permission_scope=scope,
        advisory_note=f"[Heuristic Regex] Parsed from prompt: '{raw_prompt[:60]}...' (Deterministic Regex Baseline)",
        parsing_confidence=0.0,
        raw_intent=raw_prompt,
        is_llm_derived=False,
        provider="regex_parser",
    )


class BuyerAgentDemoRunner:
    """
    Executes simulated buyer agent requests against the unmodified Sentinel.
    """

    def __init__(self):
        self.sentinel = the_sentinel

    def evaluate_purchase(self, req: BuyerAgentPurchaseRequest) -> Dict[str, Any]:
        """
        Pipes the buyer agent's purchase request directly through the Sentinel.
        PolicyRequest schema is identical to recovery action evaluation.
        """
        # Retrieve from dynamic catalog store
        item = catalog_store.get_item(req.sku_id)
        item_title = item.name if item else "Unknown Catalog SKU"
        required_scope = item.requires_permission if item else "procurement.admin"

        catalog_context = None
        if item:
            catalog_context = {
                "sku": item.sku,
                "name": item.name,
                "price": item.price,
                "in_stock": item.in_stock,
            }

        # Action-agnostic PolicyRequest
        policy_req = PolicyRequest(
            subject_id=req.agent_id,
            subject_type="buyer_agent_purchase",
            action_type=f"PURCHASE_{req.sku_id.upper()}",
            amount=req.amount,
            current_attempt_count=req.prior_orders_today,
            expected_value=req.amount,
            confidence=0.98,
            granted_permissions=req.granted_scopes,
            advisory_note=req.advisory_note,
            context={
                "monthly_budget_inr": req.monthly_budget_inr,
                "current_month_spend_inr": req.current_month_spend_inr,
                "requires_scope": required_scope,
                "max_amount_bound": self.sentinel.config.max_recovery_amount,
                "min_amount_bound": self.sentinel.config.min_amount,
                "max_retries": self.sentinel.config.max_retries,
                "catalog_item": catalog_context,
            },
        )

        decision: SentinelDecision = self.sentinel.evaluate(policy_req)

        return {
            "agent_id": req.agent_id,
            "agent_name": req.agent_name,
            "item_name": item_title,
            "sku_id": req.sku_id,
            "requested_amount_inr": req.amount,
            "business_justification": req.business_justification,
            "granted_scopes": req.granted_scopes,
            "required_scope": required_scope,
            "monthly_budget_inr": req.monthly_budget_inr,
            "current_spend_inr": req.current_month_spend_inr,
            "sentinel_decision": decision.model_dump(),
        }


# Global singleton buyer agent runner
buyer_agent_runner = BuyerAgentDemoRunner()
