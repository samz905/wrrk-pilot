"""
Test LinkedIn Lead Extraction Tool

Tests extracting leads from LinkedIn post URLs.
"""

import sys
from dotenv import load_dotenv
load_dotenv()

from app.tools.apify_linkedin_leads import LinkedInLeadExtractionTool


def test_lead_extraction(query: str, post_urls: list):
    """Test the LinkedIn lead extraction tool."""
    print("=" * 80)
    print("LINKEDIN LEAD EXTRACTION TOOL TEST")
    print("=" * 80)
    print(f"\nQuery: '{query}'")
    print(f"Post URLs: {len(post_urls)}")
    for url in post_urls:
        print(f"  - {url[:80]}...")
    print("\n" + "=" * 80)
    print("Running...\n")

    tool = LinkedInLeadExtractionTool()
    result = tool._run(query=query, post_urls=post_urls)

    print("\n" + result)

    print("\n" + "=" * 80)
    print("✓ Test complete!")
    print("=" * 80)

    return result


if __name__ == "__main__":
    # Default test case
    default_query = "founder leads"
    default_urls = [
        "https://www.linkedin.com/posts/y-combinator_maritime-fusion-has-raised-a-45m-seed-round-activity-7398812668230295553-WSh6"
    ]

    # Parse command line args
    if len(sys.argv) > 1:
        query = sys.argv[1]
        urls = sys.argv[2:] if len(sys.argv) > 2 else default_urls
    else:
        query = default_query
        urls = default_urls

    test_lead_extraction(query, urls)
