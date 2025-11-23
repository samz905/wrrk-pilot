"""Website content crawler using Apify - Extract article content for analysis."""
import os
from typing import Type, List
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from apify_client import ApifyClient


class ApifyWebsiteCrawlerInput(BaseModel):
    """Input schema for website content crawler."""
    urls: List[str] = Field(..., description="List of URLs to crawl and extract content from")
    max_pages: int = Field(default=5, description="Maximum number of pages to crawl (1-10)")


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
    Crawl websites to extract clean article content for analysis.

    Use this to:
    - Read full articles about company problems
    - Extract detailed pain point discussions
    - Find specific quotes and examples
    - Analyze industry reports and case studies

    Input parameters:
    - urls: List of URLs to crawl (e.g., from Google SERP results)
    - max_pages: Maximum pages to crawl (default: 5, max: 10)

    Returns for each URL:
    - Clean markdown content
    - Title
    - URL
    - Content length

    Note: This extracts actual article text, removing ads and navigation.
    Perfect for analyzing detailed discussions about problems and solutions.
    """
    args_schema: Type[BaseModel] = ApifyWebsiteCrawlerInput

    def _run(
        self,
        urls: List[str],
        max_pages: int = 5
    ) -> str:
        """Execute website crawling and return formatted content."""

        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            return "Error: APIFY_API_TOKEN not found in environment variables"

        if not urls:
            return "Error: No URLs provided to crawl"

        # Limit URLs to max_pages
        urls_to_crawl = urls[:min(max_pages, 10)]

        print(f"\n[INFO] Crawling {len(urls_to_crawl)} URLs for content...")
        for url in urls_to_crawl:
            print(f"  - {url}")

        # Initialize Apify client
        client = ApifyClient(apify_token)

        # Prepare actor input (aYG0l9s7dbB7j3gbS)
        start_urls = [{"url": url} for url in urls_to_crawl]

        run_input = {
            "startUrls": start_urls,
            "maxCrawlDepth": 0,  # Don't follow links
            "maxCrawlPages": len(urls_to_crawl),
            "saveMarkdown": True,
            "htmlTransformer": "readableText",
            "readableTextCharThreshold": 100,
            "removeCookieWarnings": True,
            "blockMedia": True,
            "proxyConfiguration": {"useApifyProxy": True},
            "maxConcurrency": 5  # Crawl multiple pages in parallel
        }

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
