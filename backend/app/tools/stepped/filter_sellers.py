"""
Filter Sellers Tool - Remove sellers/promoters from leads using LLM reasoning.

The LLM knows what seller language looks like - no hardcoded patterns needed.
"""
import os
import json
from typing import Type, List, Dict
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from openai import OpenAI


# === Structured Output Models ===

class LeadClassification(BaseModel):
    """Classification of a single lead."""
    index: int = Field(description="1-based index of the lead")
    name: str = Field(description="Name of the lead")
    is_seller: bool = Field(description="True if seller/promoter, False if buyer")
    reason: str = Field(description="Brief reason for classification")


class ClassificationsList(BaseModel):
    """List of lead classifications."""
    classifications: List[LeadClassification]


class FilterSellersInput(BaseModel):
    """Input schema for seller filtering."""
    leads: List[Dict] = Field(
        ...,
        description="List of lead dictionaries with 'intent_signal' field"
    )


class FilterSellersTool(BaseTool):
    """
    Filter out sellers/promoters from leads using LLM reasoning.

    ALWAYS use this before finalizing leads from any platform!
    """

    name: str = "filter_sellers"
    description: str = """
    Filter out sellers/promoters from leads. ALWAYS use this before finalizing leads!

    Uses LLM to identify sellers - people promoting their own products vs buyers looking for solutions.

    Parameters:
    - leads: List of lead dictionaries (must have 'intent_signal' or 'buying_signal' field)

    Returns JSON with:
    - buyer_leads: Filtered list of BUYER leads only
    - buyer_count: Number of buyers
    - sellers_removed: Names of removed sellers
    - recommendation: What to do next
    """
    args_schema: Type[BaseModel] = FilterSellersInput

    def _run(self, leads: List[Dict]) -> str:
        """Filter out sellers from leads list using LLM with structured outputs."""
        if not leads:
            return json.dumps({
                "buyer_leads": [],
                "buyer_count": 0,
                "sellers_removed": [],
                "recommendation": "No leads to filter"
            })

        print(f"\n[FILTER_SELLERS] Analyzing {len(leads)} leads for buyer vs seller...")

        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            # Build lead summaries for LLM
            lead_summaries = []
            for i, lead in enumerate(leads):
                name = lead.get('name', lead.get('username', f'Lead_{i}'))
                signal = lead.get('intent_signal', lead.get('buying_signal', ''))
                lead_summaries.append(f"{i+1}. {name}: \"{signal[:200]}\"")

            prompt = f"""Classify each lead as BUYER or SELLER.

LEADS:
{chr(10).join(lead_summaries)}

CLASSIFICATION:
- BUYER: Someone LOOKING for a solution, asking questions, frustrated with current tools
- SELLER: Someone PROMOTING their own product, announcing launches, self-promoting"""

            response = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You identify buyers vs sellers in lead lists. Sellers promote their own products. Buyers look for solutions."},
                    {"role": "user", "content": prompt}
                ],
                response_format=ClassificationsList,
                temperature=0.2
            )

            result = response.choices[0].message.parsed

            # Separate buyers and sellers
            buyers = []
            sellers_removed = []

            for cls in result.classifications:
                idx = cls.index - 1
                if 0 <= idx < len(leads):
                    if cls.is_seller:
                        sellers_removed.append(cls.name)
                    else:
                        buyers.append(leads[idx])

            print(f"[FILTER_SELLERS] Result: {len(buyers)} buyers, {len(sellers_removed)} sellers removed")

            return json.dumps({
                "buyer_leads": buyers,
                "buyer_count": len(buyers),
                "sellers_removed": sellers_removed,
                "sellers_removed_count": len(sellers_removed),
                "recommendation": f"Filtered {len(sellers_removed)} sellers. {len(buyers)} buyer leads ready."
            }, indent=2)

        except Exception as e:
            print(f"[FILTER_SELLERS] Error: {e}")
            # On error, return all leads (fail open)
            return json.dumps({
                "buyer_leads": leads,
                "buyer_count": len(leads),
                "sellers_removed": [],
                "error": str(e),
                "recommendation": "Filter failed - returning all leads. Manual review recommended."
            })
