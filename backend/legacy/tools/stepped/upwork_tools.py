"""
Upwork Stepped Tools - Find high-intent buyers from job postings.

Job posters on Upwork:
- Are ACTIVELY looking to buy services
- Have allocated budget
- Company names often visible
- High intent signal: ready to pay

Uses ScrapeWebsiteTool for fetching and LLM for extraction.
"""
import os
import json
from typing import Type, List, Dict, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from openai import OpenAI
from crewai_tools import ScrapeWebsiteTool

# Import LinkedIn company search for reliable URL lookup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from apify_linkedin_company_search import LinkedInCompanyBatchSearchTool


# === Structured Output Models ===

class UpworkJob(BaseModel):
    """A single job posting extracted from Upwork."""
    title: str = Field(description="Job title")
    description: str = Field(description="Job description snippet")
    budget: str = Field(default="Not specified", description="Budget or hourly rate")
    client_company: str = Field(default="Not specified", description="Client company name if visible")
    client_location: str = Field(default="Not specified", description="Client location")
    posted_date: str = Field(default="Recent", description="When the job was posted")
    job_url: str = Field(default="", description="URL to the job posting")


class UpworkJobsList(BaseModel):
    """List of job postings from Upwork."""
    jobs: List[UpworkJob]


class ScoredJob(BaseModel):
    """A scored job with relevance assessment."""
    title: str
    description: str
    budget: str
    client_company: str
    relevance_score: int = Field(ge=0, le=100, description="Relevance to product 0-100")
    reasoning: str = Field(description="Why this job is relevant")


class ScoredJobsList(BaseModel):
    """List of scored jobs."""
    jobs: List[ScoredJob]


# === Input Schemas ===

class UpworkSearchInput(BaseModel):
    """Input schema for Upwork search."""
    category: str = Field(..., description="Job category slug (e.g., 'ui-design', 'web-development', 'ai-ml')")
    max_jobs: int = Field(default=20, description="Maximum jobs to extract (default: 20)")


class UpworkScoreInput(BaseModel):
    """Input schema for Upwork scoring."""
    jobs: List[Dict] = Field(..., description="Jobs from upwork_search")
    query: str = Field(..., description="Product description for relevance scoring")


class UpworkExtractInput(BaseModel):
    """Input schema for Upwork extraction."""
    jobs: List[Dict] = Field(..., description="High-quality jobs from upwork_score")
    query: str = Field(..., description="Product description for context")


# === Tools ===

class UpworkSearchTool(BaseTool):
    """
    Step 1: Search Upwork for job postings in a category.
    """

    name: str = "upwork_search"
    description: str = """
    Search Upwork for job postings in a specific category.

    Job posters = HIGH INTENT buyers with budget!

    Parameters:
    - category: Job category slug (e.g., "ui-design", "web-development", "ai-ml")
    - max_jobs: Max jobs to extract (default: 20)

    Returns job listings for scoring.
    """
    args_schema: Type[BaseModel] = UpworkSearchInput

    def _run(self, category: str, max_jobs: int = 20) -> str:
        """Search Upwork for jobs in the given category."""
        # Build URL
        category_slug = category.lower().replace(" ", "-")
        url = f"https://www.upwork.com/freelance-jobs/{category_slug}/"

        print(f"\n[UPWORK_SEARCH] Fetching jobs from: {url}")

        try:
            # Use CrewAI's ScrapeWebsiteTool
            scraper = ScrapeWebsiteTool(website_url=url)
            content = scraper.run()

            if not content or len(content) < 500:
                return json.dumps({
                    "jobs": [],
                    "count": 0,
                    "quality": "LOW",
                    "category": category,
                    "error": "Failed to scrape Upwork page - may require JS rendering",
                    "recommendation": "Try a different category or use alternative strategy"
                })

            # Extract jobs using LLM
            jobs = self._extract_jobs_with_llm(content, category, max_jobs)
            print(f"[UPWORK_SEARCH] Extracted {len(jobs)} jobs")

            # Assess quality
            quality = "HIGH" if len(jobs) >= 5 else "LOW"

            return json.dumps({
                "jobs": jobs,
                "count": len(jobs),
                "category": category,
                "quality": quality,
                "recommendation": f"Proceed to upwork_score with query. Found {len(jobs)} jobs in {category}."
            })

        except Exception as e:
            print(f"[UPWORK_SEARCH] Error: {e}")
            return json.dumps({
                "jobs": [],
                "count": 0,
                "quality": "LOW",
                "category": category,
                "error": str(e),
                "recommendation": "Search failed. Try different category."
            })

    def _extract_jobs_with_llm(self, content: str, category: str, max_jobs: int) -> List[Dict]:
        """Extract job postings from scraped content using structured outputs."""
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.beta.chat.completions.parse(
                model="gpt-5-nano",
                messages=[
                    {"role": "system", "content": "Extract job postings from Upwork page content. Look for job titles, descriptions, budgets, and client info."},
                    {"role": "user", "content": f"Extract up to {max_jobs} job postings from this Upwork {category} page:\n\n{content[:15000]}"}
                ],
                response_format=UpworkJobsList,
                temperature=0.2
            )

            result = response.choices[0].message.parsed
            return [j.model_dump() for j in result.jobs[:max_jobs]]

        except Exception as e:
            print(f"[UPWORK_SEARCH] LLM extraction error: {e}")
            return []


class UpworkScoreTool(BaseTool):
    """
    Step 2: Score jobs for relevance to the product.
    """

    name: str = "upwork_score"
    description: str = """
    Score Upwork jobs for relevance to your product.

    The LLM assesses which jobs indicate need for YOUR product:
    - Job requirements match product capabilities
    - Budget indicates serious buyer
    - Company type fits your ICP

    Parameters:
    - jobs: Jobs from upwork_search
    - query: Your product description

    Returns scored jobs with high-quality filtered.
    """
    args_schema: Type[BaseModel] = UpworkScoreInput

    def _run(self, jobs: List[Dict], query: str) -> str:
        """Score jobs for relevance."""
        if not jobs:
            return json.dumps({
                "scored_jobs": [],
                "high_quality_count": 0,
                "high_quality_jobs": [],
                "recommendation": "No jobs to score. Run upwork_search first."
            })

        print(f"\n[UPWORK_SCORE] Scoring {len(jobs)} jobs for: '{query}'")

        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            # Format jobs for LLM
            jobs_text = "\n\n".join([
                f"Job {i+1}:\nTitle: {j.get('title', 'Unknown')}\nDescription: {j.get('description', '')[:300]}\nBudget: {j.get('budget', 'N/A')}\nCompany: {j.get('client_company', 'N/A')}"
                for i, j in enumerate(jobs)
            ])

            response = client.beta.chat.completions.parse(
                model="gpt-5-nano",
                messages=[
                    {"role": "system", "content": "Score job postings for relevance to a product. Higher scores for jobs that clearly need the product."},
                    {"role": "user", "content": f"Product: {query}\n\nScore each job's relevance (0-100) to this product:\n\n{jobs_text}"}
                ],
                response_format=ScoredJobsList,
                temperature=0.3
            )

            result = response.choices[0].message.parsed

            # Merge scores with original job data
            scored_jobs = []
            high_quality_jobs = []

            for i, scored in enumerate(result.jobs):
                if i < len(jobs):
                    job_with_score = jobs[i].copy()
                    job_with_score['relevance_score'] = scored.relevance_score
                    job_with_score['scoring_reasoning'] = scored.reasoning
                    scored_jobs.append(job_with_score)

                    if scored.relevance_score >= 50:
                        high_quality_jobs.append(job_with_score)

            print(f"[UPWORK_SCORE] {len(high_quality_jobs)}/{len(jobs)} jobs scored >= 50")

            recommendation = self._get_recommendation(len(high_quality_jobs), len(jobs))

            return json.dumps({
                "scored_jobs": scored_jobs,
                "total_scored": len(scored_jobs),
                "high_quality_count": len(high_quality_jobs),
                "high_quality_jobs": high_quality_jobs,
                "recommendation": recommendation
            })

        except Exception as e:
            print(f"[UPWORK_SCORE] Error: {e}")
            return json.dumps({
                "scored_jobs": [],
                "high_quality_count": 0,
                "high_quality_jobs": [],
                "error": str(e),
                "recommendation": "Scoring failed. Skip to next strategy."
            })

    def _get_recommendation(self, high_quality: int, total: int) -> str:
        """Generate recommendation based on scoring results."""
        if total == 0:
            return "No jobs to score."

        if high_quality >= 5:
            return f"Excellent! {high_quality} relevant jobs. Proceed to upwork_extract."
        elif high_quality >= 2:
            return f"Good. {high_quality} relevant jobs. Proceed to upwork_extract."
        elif high_quality > 0:
            return f"Limited. Only {high_quality} relevant jobs. Proceed but expect fewer leads."
        else:
            return "No relevant jobs found. Try different category or strategy."


class UpworkExtractTool(BaseTool):
    """
    Step 3: Extract leads from jobs, enrich with LinkedIn.
    """

    name: str = "upwork_extract"
    description: str = """
    Extract client companies as leads from high-quality jobs.

    Enriches with LinkedIn company URLs for decision maker discovery.

    Parameters:
    - jobs: High-quality jobs from upwork_score
    - query: Product description for context

    Returns leads with company_linkedin_url for use with linkedin_employees_search.
    """
    args_schema: Type[BaseModel] = UpworkExtractInput

    def _run(self, jobs: List[Dict], query: str) -> str:
        """Extract leads from jobs and enrich with LinkedIn."""
        if not jobs:
            return json.dumps({
                "leads": [],
                "count": 0,
                "companies_with_linkedin": 0,
                "recommendation": "No jobs to extract from. Run upwork_search and upwork_score first."
            })

        print(f"\n[UPWORK_EXTRACT] Extracting leads from {len(jobs)} jobs")

        # Collect unique company names
        unique_companies = list(set(
            job.get('client_company', '')
            for job in jobs
            if job.get('client_company') and job.get('client_company') != "Not specified"
        ))

        # Batch lookup LinkedIn company URLs
        url_map = {}
        if unique_companies:
            print(f"[UPWORK_EXTRACT] Looking up LinkedIn URLs for {len(unique_companies)} companies...")
            linkedin_search = LinkedInCompanyBatchSearchTool()
            search_result = linkedin_search._run(companies=[
                {"name": c, "context": "company posting jobs on Upwork"}
                for c in unique_companies[:10]  # Limit to 10
            ])
            search_data = json.loads(search_result)

            for match in search_data.get("matches", []):
                if match.get("linkedin_url"):
                    url_map[match["company_name"]] = match["linkedin_url"]

            print(f"[UPWORK_EXTRACT] Found LinkedIn URLs for {len(url_map)}/{len(unique_companies)} companies")

        # Build leads
        leads = []
        for job in jobs:
            company = job.get('client_company', 'Not specified')
            job_title = job.get('title', 'Unknown Job')
            budget = job.get('budget', 'Not specified')
            job_url = job.get('job_url', '')

            leads.append({
                "name": "Unknown",  # Upwork hides client names
                "title": "Decision Maker",
                "company": company,
                "company_linkedin_url": url_map.get(company),
                "intent_signal": f"Posted job: {job_title} - Budget: {budget}",
                "intent_score": job.get('relevance_score', 75),
                "source_platform": "upwork",
                "source_url": job_url,
                "priority": self._get_priority(job.get('relevance_score', 75)),
                "scoring_reasoning": job.get('scoring_reasoning', 'Active job poster on Upwork')
            })

        companies_with_urls = len([l for l in leads if l.get("company_linkedin_url")])
        print(f"[UPWORK_EXTRACT] Created {len(leads)} leads, {companies_with_urls} with LinkedIn URLs")

        return json.dumps({
            "leads": leads,
            "count": len(leads),
            "companies_with_linkedin": companies_with_urls,
            "recommendation": f"Got {len(leads)} leads from Upwork. {companies_with_urls} have company LinkedIn URLs - use linkedin_employees_search to find decision makers."
        })

    def _get_priority(self, score: int) -> str:
        """Get priority based on relevance score."""
        if score >= 80:
            return "hot"
        elif score >= 60:
            return "warm"
        else:
            return "cold"


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("UPWORK STEPPED TOOLS TEST")
    print("=" * 70)

    # Test search
    search_tool = UpworkSearchTool()
    result = search_tool._run(category="ui-design", max_jobs=10)
    print("\nSearch Result:")
    data = json.loads(result)
    print(f"Count: {data.get('count')}")
    print(f"Quality: {data.get('quality')}")
    print(f"Recommendation: {data.get('recommendation')}")
