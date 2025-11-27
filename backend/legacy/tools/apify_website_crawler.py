"""Website content crawler using Apify - Extract article content for analysis."""
import os
from typing import Type, List
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from apify_client import ApifyClient


class ApifyWebsiteCrawlerInput(BaseModel):
    """Input schema for website content crawler."""
    urls: List[str] = Field(..., description="List of URLs to crawl and extract content from")
    max_pages: int = Field(default=5, description="Maximum number of pages to crawl (1-20)")
    follow_links: bool = Field(default=False, description="Follow links from the page to crawl more content")
    link_pattern: str = Field(default=None, description="Glob pattern for links to follow (e.g., '/jobs/~*' for Upwork)")
    max_depth: int = Field(default=1, description="How many levels of links to follow (1-3)")


class ApifyWebsiteCrawlerTool(BaseTool):
    """
    Crawl websites to extract article content and analyze for intent signals.

    This tool:
    - Extracts clean markdown content from URLs
    - Removes ads, navigation, and clutter
    - Returns readable article text for analysis

    Use this after finding relevant URLs from Google SERP to:
    - Read full article content
    - Extract company pain points mentioned
    - Identify specific problems discussed
    - Find quotes from decision-makers
    """

    name: str = "Website Content Crawler"
    description: str = """
    Navigate directly to URLs and extract content. Essential for G2 and Upwork!

    USE FOR DIRECT NAVIGATION (NOT search):
    - G2 Reviews: https://www.g2.com/products/[competitor]/reviews?filters%5Bcomment_answer_values%5D=&order=lowest_rated&utf8=%E2%9C%93#reviews
    - Upwork Jobs: https://www.upwork.com/freelance-jobs/[category]/
    - Any URL you need to visit directly

    DON'T USE Google search for G2 or Upwork - navigate directly with this tool!

    Input parameters:
    - urls: List of URLs to crawl directly
    - max_pages: Maximum pages to crawl (default: 5, max: 20)
    - follow_links: Set True to follow links on the page (for Upwork job listings)
    - link_pattern: Glob pattern for links to follow (e.g., '/jobs/~*' for Upwork)
    - max_depth: How many levels deep to follow (default: 1)

    EXAMPLE: Upwork job extraction
    urls=["https://www.upwork.com/freelance-jobs/ui-design/"]
    follow_links=True
    link_pattern="/jobs/~*"
    → Crawls the listing page, then follows links to individual job pages

    Returns: Clean markdown content with title and URL for each page.
    """
    args_schema: Type[BaseModel] = ApifyWebsiteCrawlerInput

    def _run(
        self,
        urls: List[str],
        max_pages: int = 5,
        follow_links: bool = False,
        link_pattern: str = None,
        max_depth: int = 1
    ) -> str:
        """Execute website crawling and return formatted content."""

        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            return "Error: APIFY_API_TOKEN not found in environment variables"

        if not urls:
            return "Error: No URLs provided to crawl"

        # Limit URLs and depth
        urls_to_crawl = urls[:min(max_pages, 20)]
        max_depth = min(max_depth, 3)  # Cap depth at 3

        print(f"\n[INFO] Crawling {len(urls_to_crawl)} URLs for content...")
        for url in urls_to_crawl:
            print(f"  - {url}")
        if follow_links:
            print(f"[INFO] Following links: depth={max_depth}, pattern={link_pattern}")

        # Initialize Apify client
        client = ApifyClient(apify_token)

        # Prepare actor input (aYG0l9s7dbB7j3gbS)
        start_urls = [{"url": url} for url in urls_to_crawl]

        run_input = {
            "startUrls": start_urls,
            "maxCrawlDepth": max_depth if follow_links else 0,
            "maxCrawlPages": max_pages,
            "saveMarkdown": True,
            "htmlTransformer": "readableText",
            "readableTextCharThreshold": 100,
            "removeCookieWarnings": True,
            "blockMedia": True,
            "proxyConfiguration": {"useApifyProxy": True},
            "maxConcurrency": 5  # Crawl multiple pages in parallel
        }

        # Add link pattern filter if provided (for following specific links)
        if follow_links and link_pattern:
            run_input["linkSelector"] = f"a[href*='{link_pattern.replace('*', '')}']"
            run_input["pseudoUrls"] = [{"purl": f"https://[.*]{link_pattern}"}]

        try:
            # Run the actor
            print("[INFO] Running Website Crawler actor...")
            run = client.actor("aYG0l9s7dbB7j3gbS").call(run_input=run_input)

            # Fetch results from dataset
            print("[INFO] Fetching crawled content...")
            results = list(client.dataset(run["defaultDatasetId"]).iterate_items())

            if not results:
                return f"No content extracted from the provided URLs"

            print(f"[OK] Successfully crawled {len(results)} pages")

            # Format results
            formatted_output = []
            formatted_output.append(f"=== WEBSITE CONTENT EXTRACTION ===")
            formatted_output.append(f"Crawled: {len(results)} pages\n")

            for idx, result in enumerate(results, 1):
                url = result.get('url', 'Unknown URL')
                markdown = result.get('markdown', '')
                text = result.get('text', '')

                # Use markdown if available, fallback to text
                content = markdown if markdown else text

                # Extract title from metadata or content
                metadata = result.get('metadata', {})
                title = metadata.get('title', 'No title')

                # Truncate very long content for display
                if len(content) > 2000:
                    content_preview = content[:2000] + f"\n\n... [Content truncated, total length: {len(content)} chars]"
                else:
                    content_preview = content

                formatted_output.append(f"--- Page {idx} ---")
                formatted_output.append(f"Title: {title}")
                formatted_output.append(f"URL: {url}")
                formatted_output.append(f"Content Length: {len(content)} characters")
                formatted_output.append(f"\nContent:\n{content_preview}")
                formatted_output.append("\n" + "="*70 + "\n")

            return "\n".join(formatted_output)

        except Exception as e:
            error_msg = f"Error running website crawler: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return error_msg
