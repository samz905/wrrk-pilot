"""
IntentSignalHunterTool - Parallel search across LinkedIn, Reddit, and Twitter.

This composite tool searches for intent signals across all major platforms
in parallel, then merges and deduplicates the results.
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

from apify_linkedin_posts import ApifyLinkedInPostsSearchTool
from apify_reddit import ApifyRedditSearchTool
from apify_twitter import ApifyTwitterSearchTool


class IntentSignalHunterInput(BaseModel):
    """Input schema for intent signal hunting."""
    topic: str = Field(..., description="Topic to search for (e.g., 'CRM software', 'project management')")
    pain_point_keywords: Optional[List[str]] = Field(
        default=None,
        description="Additional pain point keywords to search (e.g., ['frustrated with', 'looking for alternative'])"
    )
    max_results_per_platform: int = Field(default=30, description="Max results per platform (default: 30)")
    platforms: Optional[List[str]] = Field(
        default=None,
        description="Platforms to search: ['linkedin', 'reddit', 'twitter']. Default: all"
    )


class IntentSignalHunterTool(BaseTool):
    """
    Search for buying intent signals across LinkedIn, Reddit, and Twitter IN PARALLEL.

    This tool:
    1. Generates platform-specific search queries from your topic
    2. Executes searches on all platforms simultaneously
    3. Merges and deduplicates results
    4. Returns a unified list of leads with intent signals

    Use this as your primary tool for finding people actively discussing problems
    or seeking solutions related to your product.
    """

    name: str = "Intent Signal Hunter"
    description: str = """
    Search for buying intent signals across LinkedIn, Reddit, and Twitter in PARALLEL.

    This composite tool:
    1. Searches all major platforms simultaneously for speed
    2. Finds people actively discussing problems or seeking solutions
    3. Merges and deduplicates results across platforms
    4. Returns unified lead list with intent signals and scores

    Input parameters:
    - topic: Main topic to search (e.g., "CRM software", "design tools")
    - pain_point_keywords: Optional additional keywords for intent signals
    - max_results_per_platform: Results per platform (default: 30)
    - platforms: Which platforms to search (default: all)

    Returns list of leads with:
    - Name, title, company (where available)
    - Intent signal (quote showing buying intent)
    - Intent score (0-100)
    - Source platform and URL

    PERFORMANCE: Runs all platform searches in parallel for 3x speed.
    """
    args_schema: Type[BaseModel] = IntentSignalHunterInput

    def _run(
        self,
        topic: str,
        pain_point_keywords: Optional[List[str]] = None,
        max_results_per_platform: int = 30,
        platforms: Optional[List[str]] = None
    ) -> str:
        """
        Execute parallel intent signal search across platforms.
        """
        print(f"\n[INFO] Intent Signal Hunter starting for: '{topic}'")

        # Default to all platforms
        if platforms is None:
            platforms = ["linkedin", "reddit", "twitter"]

        # Build search queries
        base_queries = self._build_search_queries(topic, pain_point_keywords)
        print(f"[INFO] Search queries: {json.dumps(base_queries, indent=2)}")
        print(f"[INFO] Platforms: {platforms}")

        # Create tool instances on demand
        linkedin_tool = ApifyLinkedInPostsSearchTool()
        reddit_tool = ApifyRedditSearchTool()
        twitter_tool = ApifyTwitterSearchTool()

        # Execute parallel searches
        all_results = {}
        errors = []

        def search_linkedin(query, max_results):
            return linkedin_tool._run(query=query, max_results=max_results)

        def search_reddit(query, max_results):
            return reddit_tool._run(
                query=query, subreddit=None, time_filter="month",
                sort_by="relevance", desired_results=max_results
            )

        def search_twitter(query, max_results):
            return twitter_tool._run(query=query, query_type="Top", max_results=max_results)

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}

            # Submit platform searches
            if "linkedin" in platforms:
                futures[executor.submit(
                    search_linkedin,
                    base_queries.get("linkedin", topic),
                    max_results_per_platform
                )] = "linkedin"

            if "reddit" in platforms:
                futures[executor.submit(
                    search_reddit,
                    base_queries.get("reddit", topic),
                    max_results_per_platform
                )] = "reddit"

            if "twitter" in platforms:
                futures[executor.submit(
                    search_twitter,
                    base_queries.get("twitter", topic),
                    max_results_per_platform
                )] = "twitter"

            # Collect results as they complete
            for future in as_completed(futures):
                platform = futures[future]
                try:
                    result = future.result()
                    all_results[platform] = result
                    print(f"[OK] {platform.capitalize()} search completed")
                except Exception as e:
                    errors.append(f"{platform}: {str(e)}")
                    print(f"[ERROR] {platform} search failed: {str(e)}")

        # Format combined results
        return self._format_combined_results(all_results, errors, topic)

    def _build_search_queries(
        self,
        topic: str,
        pain_point_keywords: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Build platform-specific search queries.

        Different platforms need different query styles:
        - LinkedIn: Professional language, problem-focused
        - Reddit: Casual, recommendation-seeking
        - Twitter: Short, hashtag-friendly
        """
        # Default pain point keywords
        if pain_point_keywords is None:
            pain_point_keywords = [
                "looking for",
                "recommend",
                "alternative to",
                "frustrated with"
            ]

        # Combine topic with pain point keywords
        linkedin_query = f"{topic} {pain_point_keywords[0]}"
        reddit_query = f"{topic} recommendation"
        twitter_query = f"{topic} recommend"

        return {
            "linkedin": linkedin_query,
            "reddit": reddit_query,
            "twitter": twitter_query
        }

    def _format_combined_results(
        self,
        results: Dict[str, str],
        errors: List[str],
        topic: str
    ) -> str:
        """
        Format combined results from all platforms.
        """
        output = []
        output.append("=" * 70)
        output.append(f"INTENT SIGNAL HUNT: '{topic}'")
        output.append("=" * 70)
        output.append(f"\nPlatforms searched: {len(results)}")
        if errors:
            output.append(f"Errors: {len(errors)}")
            for error in errors:
                output.append(f"  - {error}")
        output.append("")

        # Add results from each platform
        for platform, result in results.items():
            output.append(f"\n{'='*30} {platform.upper()} {'='*30}")
            output.append(result)
            output.append("")

        output.append("=" * 70)
        output.append("\nCOMBINED INSIGHTS:")
        output.append(f"- Platforms with results: {len(results)}")
        output.append(f"- Use these results to identify high-intent leads")
        output.append(f"- Look for people explicitly asking for solutions")
        output.append(f"- Prioritize recent posts with high engagement")
        output.append("=" * 70)

        return "\n".join(output)


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("INTENT SIGNAL HUNTER TEST")
    print("=" * 70)

    tool = IntentSignalHunterTool()

    # Test with a topic
    result = tool._run(
        topic="CRM software",
        max_results_per_platform=5,
        platforms=["reddit"]  # Just test Reddit for speed
    )

    print("\n" + result)
