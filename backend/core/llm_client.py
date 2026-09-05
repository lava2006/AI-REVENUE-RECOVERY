"""
Real LLM Client Integration for Rebound — AI Revenue Recovery Agent
Supports Google Gemini and OpenAI APIs.
Uses structured prompts requiring genuine model-generated confidence estimates,
failure causes, and playbook probability estimations.
ZERO SILENT FALLBACKS: Raises loud, explicit errors when credentials or network calls fail.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
import httpx
from dotenv import load_dotenv

# Load local environment variables if available
load_dotenv()

logger = logging.getLogger("rebound.llm")

# Model configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
DEFAULT_OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


class LLMConfigurationError(Exception):
    """Raised when required LLM credentials are not configured."""
    pass


class LLMInferenceError(Exception):
    """Raised when an LLM API call fails or returns invalid structured output."""
    pass


class LLMClient:
    """Real LLM Client for Rebound with explicit error handling and zero silent mocking."""

    def __init__(self):
        self.gemini_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
        self.openai_key = os.environ.get("OPENAI_API_KEY", "")

        if self.gemini_key:
            self.provider = "gemini"
        elif self.openai_key:
            self.provider = "openai"
        else:
            self.provider = "none"

    def is_configured(self) -> bool:
        """Returns True only if a valid API key is present."""
        return self.provider in ["gemini", "openai"]

    def require_configured(self):
        """Fails loudly if no valid API key is present."""
        if not self.is_configured():
            raise LLMConfigurationError(
                "No valid LLM API key found in environment. Please set GEMINI_API_KEY or GOOGLE_API_KEY."
            )

    # ------------------------------------------------------------------------
    # 1. Real AI Diagnosis Call
    # ------------------------------------------------------------------------
    def diagnose_payment(
        self,
        payment_id: str,
        amount: float,
        decline_code: str,
        raw_signal: str,
        customer_tier: str,
        tenure_months: int,
        past_failed_retries: int,
        dunning_attempts: int,
    ) -> Dict[str, Any]:
        """
        Calls Claude or GPT to diagnose recurring subscription payment failure.
        Returns genuine model-estimated confidence and structured reasoning.
        """
        self.require_configured()

        prompt = (
            f"You are a payment operations diagnostician for Razorpay recurring subscriptions.\n"
            f"Analyze this failed transaction:\n"
            f"- Amount: INR {amount:,.2f}\n"
            f"- Decline Code: {decline_code}\n"
            f"- Gateway Raw Signal: {raw_signal}\n"
            f"- Customer Tier: {customer_tier}\n"
            f"- Account Tenure: {tenure_months} months\n"
            f"- Prior Failed Retries: {past_failed_retries}\n"
            f"- Dunning Alerts Sent: {dunning_attempts}\n\n"
            f"Diagnose the root cause into EXACTLY ONE of:\n"
            f"1. INSUFFICIENT_FUNDS (low balance, salary cycle needed)\n"
            f"2. CARD_EXPIRED (card expiration date lapsed, token invalid)\n"
            f"3. ISSUER_DECLINE (bank e-mandate limit, international block, 3DS required)\n"
            f"4. BANK_DOWNTIME (transient CBS timeout, issuer switch offline)\n"
            f"5. RISK_BLOCK (fraud flag, stolen card, velocity anomaly)\n\n"
            f"Respond ONLY with a valid JSON object matching this schema:\n"
            f'{{\n'
            f'  "cause": "INSUFFICIENT_FUNDS" | "CARD_EXPIRED" | "ISSUER_DECLINE" | "BANK_DOWNTIME" | "RISK_BLOCK",\n'
            f'  "confidence": <float between 0.10 and 0.99 reflecting your model confidence in this diagnosis>,\n'
            f'  "reasoning": "<detailed explanation of why this cause fits this telemetry>",\n'
            f'  "key_signals": ["<signal 1>", "<signal 2>"]\n'
            f'}}'
        )

        if self.provider == "gemini":
            return self._call_gemini(prompt)
        else:
            return self._call_openai(prompt, DEFAULT_OPENAI_MODEL)

    # ------------------------------------------------------------------------
    # 2. Real AI Strategy Ranking & Recovery Probability Estimation
    # ------------------------------------------------------------------------
    def estimate_strategy_probabilities(
        self,
        payment_id: str,
        amount: float,
        diagnosed_cause: str,
        customer_tier: str,
        tenure_months: int,
        past_failed_retries: int,
        dunning_attempts: int,
    ) -> Dict[str, Any]:
        """
        Calls Gemini, Claude, or GPT to estimate genuine recovery probabilities for all 5 playbook strategies.
        """
        self.require_configured()

        prompt = (
            f"You are a FinTech recovery strategy optimizer.\n"
            f"A recurring subscription payment of INR {amount:,.2f} failed due to {diagnosed_cause}.\n"
            f"Customer profile: {customer_tier} tier, {tenure_months} months tenure, "
            f"{past_failed_retries} prior failed retries, {dunning_attempts} dunning alerts sent.\n\n"
            f"Estimate the success probability (P between 0.00 and 0.95) and provide a concise context-specific rationale for each of the 5 fixed strategies:\n"
            f"1. RETRY_NOW: Immediate smart retry\n"
            f"2. RETRY_LATER: Scheduled retry after 4-48h cooldown window\n"
            f"3. NOTIFY_CUSTOMER: 1-click payment link alert via SMS/Email/WhatsApp\n"
            f"4. OFFER_ALTERNATE_PAYMENT_METHOD: Switch mandate to UPI AutoPay / NetBanking\n"
            f"5. PROMPT_CARD_UPDATE: Prompt customer for renewed card token details\n\n"
            f"Respond ONLY with a valid JSON object matching:\n"
            f'{{\n'
            f'  "strategies": [\n'
            f'    {{"action": "RETRY_NOW", "probability": <float 0.0-0.95>, "rationale": "<context reasoning>"}},\n'
            f'    {{"action": "RETRY_LATER", "probability": <float 0.0-0.95>, "rationale": "<context reasoning>"}},\n'
            f'    {{"action": "NOTIFY_CUSTOMER", "probability": <float 0.0-0.95>, "rationale": "<context reasoning>"}},\n'
            f'    {{"action": "OFFER_ALTERNATE_PAYMENT_METHOD", "probability": <float 0.0-0.95>, "rationale": "<context reasoning>"}},\n'
            f'    {{"action": "PROMPT_CARD_UPDATE", "probability": <float 0.0-0.95>, "rationale": "<context reasoning>"}}\n'
            f'  ]\n'
            f'}}'
        )

        if self.provider == "gemini":
            return self._call_gemini(prompt)
        else:
            return self._call_openai(prompt, DEFAULT_OPENAI_MODEL)

    # ------------------------------------------------------------------------
    # 3. Real AI Buyer Agent Intent Parsing
    # ------------------------------------------------------------------------
    def parse_buyer_agent_intent(
        self,
        raw_prompt: str,
        catalog_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calls Gemini, Claude, or GPT to parse natural language buyer intent against the merchant catalog.
        """
        self.require_configured()

        catalog_summary = json.dumps([
            {"sku": item["sku"], "name": item["name"], "price": item["price"], "requires_permission": item.get("requires_permission")}
            for item in catalog_items
        ], indent=2)

        prompt = (
            f"You are an autonomous Agent Commerce intent parser.\n"
            f"An enterprise buyer agent issued this purchase instruction:\n"
            f"\"{raw_prompt}\"\n\n"
            f"Active Merchant Catalog:\n"
            f"{catalog_summary}\n\n"
            f"Parse the intent into the best matching SKU, total requested amount, and required permission scopes.\n"
            f"Respond ONLY with a valid JSON object:\n"
            f'{{\n'
            f'  "sku": "<matched SKU from catalog>",\n'
            f'  "requested_amount": <total price as float>,\n'
            f'  "agent_permission_scope": ["<scope required>"],\n'
            f'  "confidence": <float 0.1-0.99 reflecting parsing confidence>,\n'
            f'  "advisory_note": "<brief notes on parsing decision>"\n'
            f'}}'
        )

        if self.provider == "gemini":
            return self._call_gemini(prompt)
        else:
            return self._call_openai(prompt, DEFAULT_OPENAI_MODEL)

    # ------------------------------------------------------------------------
    # Google Gemini API Execution
    # ------------------------------------------------------------------------
    def _call_gemini(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes Google Gemini API call with structured JSON output and automatic model failover.
        Resiliently attempts models in order: DEFAULT_GEMINI_MODEL, gemini-3.1-flash-lite, gemini-3.6-flash.
        """
        candidate_models = [
            DEFAULT_GEMINI_MODEL,
            "gemini-3.1-flash-lite",
            "gemini-3.6-flash",
        ]
        candidate_models = list(dict.fromkeys(candidate_models))

        last_error = None
        raw_text = ""
        for model in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_key}"
            payload: Dict[str, Any] = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.1,
                },
            }
            if system_prompt:
                payload["systemInstruction"] = {
                    "parts": [{"text": system_prompt}]
                }

            try:
                resp = httpx.post(url, json=payload, timeout=25.0)
                if resp.status_code in [503, 429]:
                    logger.warning("Gemini model %s returned HTTP %s. Retrying fallback candidate...", model, resp.status_code)
                    last_error = LLMInferenceError(f"Gemini {model} returned HTTP {resp.status_code}: {resp.text}")
                    continue
                if resp.status_code != 200:
                    logger.error("Gemini API returned HTTP %s: %s", resp.status_code, resp.text)
                    raise LLMInferenceError(f"Gemini API returned HTTP {resp.status_code}: {resp.text}")

                res_json = resp.json()
                raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.strip("`").replace("json\n", "", 1).strip()

                data = json.loads(raw_text)
                data["_raw_model_response"] = raw_text
                data["_provider"] = "gemini"
                data["_model"] = model
                return data
            except json.JSONDecodeError as e:
                logger.error("Gemini model %s returned invalid JSON: %s. Raw: %s", model, e, raw_text)
                raise LLMInferenceError(f"Gemini returned invalid JSON: {str(e)}") from e
            except httpx.RequestError as e:
                logger.warning("Gemini network error with model %s: %s", model, e)
                last_error = LLMInferenceError(f"Gemini connection error: {str(e)}")
                continue

        raise last_error or LLMInferenceError("All Gemini candidate models failed to return a response.")


    # ------------------------------------------------------------------------
    # OpenAI API Execution
    # ------------------------------------------------------------------------
    def _call_openai(self, prompt: str, model: str) -> Dict[str, Any]:
        """Executes OpenAI chat completions with structured output and explicit error handling."""
        try:
            resp = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are an autonomous FinTech decision engine. Output valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1,
                },
                timeout=12.0
            )
            if resp.status_code != 200:
                logger.error("OpenAI API returned HTTP %s: %s", resp.status_code, resp.text)
                raise LLMInferenceError(f"OpenAI API returned HTTP {resp.status_code}: {resp.text}")

            res_json = resp.json()
            raw_text = res_json["choices"][0]["message"]["content"].strip()
            data = json.loads(raw_text)
            data["_raw_model_response"] = raw_text
            data["_provider"] = "openai"
            data["_model"] = model
            return data
        except Exception as e:
            logger.error("OpenAI API call failed: %s", e)
            raise LLMInferenceError(f"OpenAI API call failed: {str(e)}") from e


# Global LLM Client instance
llm_client = LLMClient()
