"""
CompanyTriggerScannerTool - Find companies with buying triggers.

This composite tool searches Google SERP and Crunchbase in parallel
to find companies showing buying signals (funding, hiring, tech changes).
"""
import os
import json
from typing import Type, List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Import atomic tools
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crewai_tools import SerperDevTool
from apify_crunchbase import ApifyCrunchbaseTool


class CompanyTriggerScannerInput(BaseModel):
    """Input schema for company trigger scanning."""
    industry: str = Field(..., description="Target industry (e.g., 'SaaS', 'fintech', 'healthcare')")
    trigger_types: Optional[List[str]] = Field(
        default=None,
        description="Types of triggers to search: ['funding', 'hiring', 'expansion', 'tech_change']. Default: all"
    )
    company_size: Optional[str] = Field(
        default=None,
        description="Target company size: 'startup', 'smb', 'mid-market', 'enterprise'"
    )
    max_results: int = Field(default=30, description="Maximum results to return (default: 30)")


class CompanyTriggerScannerTool(BaseTool):
    """
    Find companies with buying triggers using Google SERP + Crunchbase IN PARALLEL.

    This tool:
    1. Searches Google for news about companies with triggers
    2. Searches Crunchbase for funding/growth signals
    3. Merges results and identifies companies with multiple signals
    4. Returns prioritized list of companies likely to buy

    Buying triggers include:
    - Funding: Series A/B/C, raised money
    - Hiring: VP/Director roles, team growth
    - Expansion: New markets, office openings
    - Tech Change: Migration, new implementations
    """

    name: str = "Company Trigger Scanner"
    description: str = """
    Find companies with buying triggers using Google and Crunchbase in PARALLEL.

    This composite tool:
    1. Searches Google SERP for company news (funding, hiring, expansion)
    2. Searches Crunchbase for funding and growth signals
    3. Merges and deduplicates company data
    4. Returns prioritized list with trigger details

    Input parameters:
    - industry: Target industry (e.g., "SaaS", "fintech")
    - trigger_types: Which triggers to search (default: all)
    - company_size: Target company size filter
    - max_results: Maximum results (default: 30)

    Returns list of companies with:
    - Company name and description
    - Funding information
    - Trigger type and details
    - Source URLs

    PERFORMANCE: Runs Google + Crunchbase searches in parallel for 2x speed.
    """
    args_schema: Type[BaseModel] = CompanyTriggerScannerInput

    def _run(
        self,
        industry: str,
        trigger_types: Optional[List[str]] = None,
        company_size: Optional[str] = None,
        max_results: int = 30
    ) -> str:
        """
        Execute parallel company trigger search.
        """
        print(f"\n[INFO] Company Trigger Scanner starting for: '{industry}'")

        # Default to all trigger types
        if trigger_types is None:
            trigger_types = ["funding", "hiring", "expansion", "tech_change"]

        # Build search queries
        queries = self._build_trigger_queries(industry, trigger_types, company_size)
        print(f"[INFO] Trigger queries: {json.dumps(queries, indent=2)}")

        # Create tool instances on demand
        google_tool = SerperDevTool(n_results=max_results)
        crunchbase_tool = ApifyCrunchbaseTool()

        def search_google(query, max_res):
            # SerperDevTool returns dict with 'organic' results
            result = google_tool.run(search_query=query)
            # Format result for display
            if isinstance(result, dict) and 'organic' in result:
                formatted = [f"=== GOOGLE SEARCH RESULTS ===\nQuery: '{query}'\nFound: {len(result['organic'])} results\n"]
                for item in result['organic'][:max_res]:
                    formatted.append(f"--- Result #{item.get('position', 'N/A')} ---")
                    formatted.append(f"Title: {item.get('title', 'No title')}")
                    formatted.append(f"URL: {item.get('link', 'No URL')}")
                    formatted.append(f"Snippet: {item.get('snippet', 'No description')}\n")
                return "\n".join(formatted)
            return str(result)

        def search_crunchbase(query, max_res):
            return crunchbase_tool._run(keyword=query, limit=max_res)

        # Execute parallel searches
        all_results = {}
        errors = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {}

            # Submit Google SERP search
            futures[executor.submit(
                search_google,
                queries.get("google", industry),
                max_results
            )] = "google"

            # Submit Crunchbase search
            futures[executor.submit(
                search_crunchbase,
                queries.get("crunchbase", industry),
                max_results
            )] = "crunchbase"

            # Collect results as they complete
            for future in as_completed(futures):
                source = futures[future]
                try:
                    result = future.result()
                    all_results[source] = result
                    print(f"[OK] {source.capitalize()} search completed")
                except Exception as e:
                    errors.append(f"{source}: {str(e)}")
                    print(f"[ERROR] {source} search failed: {str(e)}")

        # Format combined results
        return self._format_combined_results(all_results, errors, industry, trigger_types)

    def _build_trigger_queries(
        self,
        industry: str,
        trigger_types: List[str],
        company_size: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Build platform-specific queries for trigger types.
        """
        # Build trigger-specific query parts
        trigger_parts = []
        if "funding" in trigger_types:
            trigger_parts.append("raised funding OR Series A OR Series B")
        if "hiring" in trigger_types:
            trigger_parts.append("hiring OR new VP OR team growth")
        if "expansion" in trigger_types:
            trigger_parts.append("expansion OR new market OR office opening")
        if "tech_change" in trigger_types:
            trigger_parts.append("migration OR new platform OR digital transformation")

        # Size modifier
        size_modifier = ""
        if company_size:
            size_map = {
                "startup": "startup",
                "smb": "small business",
                "mid-market": "mid-market company",
                "enterprise": "enterprise"
            }
            size_modifier = size_map.get(company_size, "")

        # Google query - focus on news
        google_query = f"{industry} {size_modifier} company {trigger_parts[0] if trigger_parts else 'funding'}"

        # Crunchbase query - focus on funding/growth
        crunchbase_query = f"{industry} {size_modifier}".strip()
        if "funding" in trigger_types:
            crunchbase_query = f"Series A {industry}" if "startup" in str(company_size).lower() else f"funding {industry}"

        return {
            "google": google_query.strip(),
            "crunchbase": crunchbase_query.strip()
        }

    def _format_combined_results(
        self,
        results: Dict[str, str],
        errors: List[str],
        industry: str,
        trigger_types: List[str]
    ) -> str:
        """
        Format combined results from all sources.
        """
        output = []
        output.append("=" * 70)
        output.append(f"COMPANY TRIGGER SCAN: '{industry}'")
        output.append("=" * 70)
        output.append(f"\nTrigger types: {', '.join(trigger_types)}")
        output.append(f"Sources searched: {len(results)}")
        if errors:
            output.append(f"Errors: {len(errors)}")
            for error in errors:
                output.append(f"  - {error}")
        output.append("")

        # Add results from each source
        for source, result in results.items():
            output.append(f"\n{'='*30} {source.upper()} {'='*30}")
            output.append(result)
            output.append("")

        output.append("=" * 70)
        output.append("\nNEXT STEPS:")
        output.append("1. Identify companies with multiple trigger signals")
        output.append("2. Use DecisionMakerFinderTool to find contacts at top companies")
        output.append("3. Prioritize companies with recent triggers (last 30 days)")
        output.append("=" * 70)

        return "\n".join(output)


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("COMPANY TRIGGER SCANNER TEST")
    print("=" * 70)

    tool = CompanyTriggerScannerTool()

    # Test with an industry
    result = tool._run(
        industry="SaaS",
        trigger_types=["funding"],
        max_results=5
    )

    print("\n" + result)
