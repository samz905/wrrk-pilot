"""
TechCrunch Stepped Tools - Funding signals from TechCrunch.

Uses CrewAI ScrapeWebsiteTool to extract funding articles.
Better than Crunchbase: no auth required, always fresh data.

Architecture: Each tool does ONE thing. Agent decides what to call next.
"""
import os
import json
from typing import Type, List, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from openai import OpenAI
from crewai_tools import ScrapeWebsiteTool


# === Structured Output Models ===

class FundingArticle(BaseModel):
    """A single funding article extracted from TechCrunch."""
    title: str
    company: str
    funding: str
    date: Optional[str] = None


class FundingArticlesList(BaseModel):
    """List of funding articles."""
    articles: List[FundingArticle]


class SelectedCompany(BaseModel):
    """A company selected as relevant for the query."""
    company: str
    funding: str
    title: str
    relevance: str


class SelectedCompaniesList(BaseModel):
    """List of selected companies."""
    selected: List[SelectedCompany]


class DecisionMaker(BaseModel):
    """A selected decision maker."""
    name: str
    title: str
    linkedin_url: Optional[str] = None
    reason: str


class DecisionMakersList(BaseModel):
    """List of selected decision makers."""
    selected: List[DecisionMaker]



class TechCrunchFetchInput(BaseModel):
    """Input schema for TechCrunch fetch."""
    page: int = Field(default=1, description="Page number (1, 2, 3...) for pagination")


class TechCrunchSelectArticlesInput(BaseModel):
    """Input schema for article selection."""
    articles: List[dict] = Field(..., description="Articles from techcrunch_fetch")
    query: str = Field(..., description="Product description to match against")
    limit: int = Field(default=5, description="Max articles to select")


class TechCrunchExtractCompaniesInput(BaseModel):
    """Input schema for company extraction."""
    articles: List[dict] = Field(..., description="Selected articles from techcrunch_select_articles")
    query: str = Field(..., description="Product description for context")


class TechCrunchSelectDecisionMakersInput(BaseModel):
    """Input schema for decision maker selection."""
    employees_by_company: dict = Field(..., description="Dict of {company_name: [employees]} from LinkedIn searches")
    query: str = Field(..., description="Product description")
    companies_context: List[dict] = Field(..., description="Company funding info from techcrunch_extract_companies")


class TechCrunchFetchTool(BaseTool):
    """
    Fetch funding announcements from TechCrunch.
    """

    name: str = "techcrunch_fetch"
    description: str = """
    Fetch recent funding announcements from TechCrunch.

    TechCrunch = FRESH FUNDING DATA (updated daily)!

    Parameters:
    - page: Page number (default: 1). Use page=2, 3, etc. for more articles.

    Returns article info for selection.
    """
    args_schema: Type[BaseModel] = TechCrunchFetchInput

    def _run(self, page: int = 1) -> str:
        """Fetch TechCrunch funding articles."""
        url = f"https://techcrunch.com/tag/funding/page/{page}/" if page > 1 else "https://techcrunch.com/tag/funding/"

        print(f"\n[TECHCRUNCH_FETCH] Scraping TechCrunch funding page {page}...")

        try:
            # Use CrewAI's ScrapeWebsiteTool
            scraper = ScrapeWebsiteTool(website_url=url)
            content = scraper.run()

            if not content or len(content) < 500:
                return json.dumps({
                    "articles": [],
                    "count": 0,
                    "page": page,
                    "has_more": False,
                    "error": "Failed to scrape TechCrunch page",
                    "recommendation": "Try a different strategy"
                })

            # Use LLM to extract article info
            articles = self._extract_articles_with_llm(content)
            print(f"[TECHCRUNCH_FETCH] Found {len(articles)} funding articles")

            return json.dumps({
                "articles": articles,
                "count": len(articles),
                "page": page,
                "has_more": len(articles) >= 10,
                "recommendation": f"Proceed to techcrunch_select_articles with query. If more leads needed later, call techcrunch_fetch with page={page + 1}"
            })

        except Exception as e:
            print(f"[TECHCRUNCH_FETCH] Error: {e}")
            return json.dumps({
                "articles": [],
                "count": 0,
                "page": page,
                "error": str(e),
                "recommendation": "Try a different strategy"
            })

    def _extract_articles_with_llm(self, content: str) -> List[dict]:
        """Extract funding articles from scraped content using structured outputs."""
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract funding article information from TechCrunch page content. Look for patterns like 'Company raises $XM' or 'Company secures funding'."},
                    {"role": "user", "content": f"Extract all funding articles from this TechCrunch page:\n\n{content[:12000]}"}
                ],
                response_format=FundingArticlesList,
                temperature=0.2
            )

            result = response.choices[0].message.parsed
            return [a.model_dump() for a in result.articles]

        except Exception as e:
            print(f"[TECHCRUNCH_FETCH] LLM extraction error: {e}")
            return []


class TechCrunchSelectArticlesTool(BaseTool):
    """
    LLM selects relevant funding articles for the query.
    """

    name: str = "techcrunch_select_articles"
    description: str = """
    Select funding articles relevant to your product/query.

    The LLM picks articles about companies in YOUR target space.

    Parameters:
    - articles: List from techcrunch_fetch
    - query: Your product description
    - limit: Max articles to select (default: 5)

    Returns selected articles for company extraction.
    """
    args_schema: Type[BaseModel] = TechCrunchSelectArticlesInput

    def _run(self, articles: List[dict], query: str, limit: int = 5) -> str:
        """Select relevant articles using LLM."""
        if not articles:
            return json.dumps({
                "selected": [],
                "count": 0,
                "recommendation": "No articles to select from. Try techcrunch_fetch first."
            })

        print(f"\n[TECHCRUNCH_SELECT] Selecting from {len(articles)} articles for: '{query}'")

        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            # Format articles with company and funding info
            articles_text = "\n".join([
                f"- {a.get('company', 'Unknown')} ({a.get('funding', '?')}): {a.get('title', '')}"
                for a in articles
            ])

            response = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You select recently funded companies relevant to a product query. Pick companies that would be good prospects for the product."},
                    {"role": "user", "content": f"Product: {query}\n\nSelect up to {limit} recently funded companies that might need this product:\n\n{articles_text}"}
                ],
                response_format=SelectedCompaniesList,
                temperature=0.3
            )

            result = response.choices[0].message.parsed
            selected = [s.model_dump() for s in result.selected[:limit]]
            print(f"[TECHCRUNCH_SELECT] Selected {len(selected)} relevant articles")

            return json.dumps({
                "selected": selected,
                "count": len(selected),
                "recommendation": "Proceed to techcrunch_extract_companies to get company details"
            })

        except Exception as e:
            print(f"[TECHCRUNCH_SELECT] Error: {e}")
            # Fallback: return first N articles
            selected = articles[:limit]
            return json.dumps({
                "selected": selected,
                "count": len(selected),
                "error": str(e),
                "recommendation": "Proceed to techcrunch_extract_companies"
            })


class TechCrunchExtractCompaniesTool(BaseTool):
    """
    Extract company details from selected articles.
    Does NOT call LinkedIn - agent must call linkedin_company_batch_search separately.
    """

    name: str = "techcrunch_extract_companies"
    description: str = """
    Extract company details from selected funding articles.

    Returns structured company data (name, funding, description).
    Does NOT include LinkedIn URLs - you must call linkedin_company_batch_search next.

    Parameters:
    - articles: Selected articles from techcrunch_select_articles
    - query: Product description for context

    Returns company list. Next: call linkedin_company_batch_search to get LinkedIn URLs.
    """
    args_schema: Type[BaseModel] = TechCrunchExtractCompaniesInput

    def _run(self, articles: List[dict], query: str) -> str:
        """Extract company details from articles. Agent calls LinkedIn search separately."""
        if not articles:
            return json.dumps({
                "companies": [],
                "count": 0,
                "done": "No articles to extract from",
                "next": "Try techcrunch_fetch first"
            })

        print(f"\n[TECHCRUNCH_EXTRACT] Extracting {len(articles)} companies")

        # Build companies list (NO LinkedIn lookup - agent does that)
        companies = []
        for article in articles[:5]:  # Limit to 5
            company_name = article.get("company", "")
            if not company_name:
                continue

            companies.append({
                "name": company_name,
                "funding": article.get("funding", "recently funded"),
                "description": article.get("title", ""),
                "relevance": article.get("relevance", ""),
                "date": article.get("date", "")
            })
            print(f"[TECHCRUNCH_EXTRACT] Extracted: {company_name} ({article.get('funding', '?')})")

        print(f"[TECHCRUNCH_EXTRACT] Done. Extracted {len(companies)} companies")

        # Format companies for linkedin_company_batch_search input
        companies_for_linkedin = [
            {"name": c["name"], "context": c.get("description", "recently funded company")}
            for c in companies
        ]

        return json.dumps({
            "companies": companies,
            "companies_for_linkedin": companies_for_linkedin,
            "count": len(companies),
            "done": f"Extracted {len(companies)} funded companies from TechCrunch",
            "next": "Call linkedin_company_batch_search with companies_for_linkedin to get company LinkedIn URLs. Then linkedin_employees_search for each company. Then techcrunch_select_decision_makers."
        })


class TechCrunchSelectDecisionMakersTool(BaseTool):
    """
    Select the RIGHT decision makers for the product from LinkedIn employee lists.
    """

    name: str = "techcrunch_select_decision_makers"
    description: str = """
    Batch select the RIGHT decision makers from all companies.

    The LLM picks WHO at each company would buy YOUR product:
    - AI recruitment tool → Head of Talent, HR Director
    - Design tool → Head of Design, VP Product
    - DevOps tool → VP Engineering, CTO

    Parameters:
    - employees_by_company: Dict of {company_name: [employees]} from LinkedIn
    - query: Your product description
    - companies_context: Company funding info from techcrunch_extract_companies

    Returns qualified leads ready for outreach.
    """
    args_schema: Type[BaseModel] = TechCrunchSelectDecisionMakersInput

    def _run(self, employees_by_company: dict, query: str, companies_context: List[dict]) -> str:
        """Select decision makers using LLM."""
        if not employees_by_company:
            return json.dumps({
                "leads": [],
                "count": 0,
                "recommendation": "No employees to select from. Run linkedin_employees_search first."
            })

        print(f"\n[TECHCRUNCH_DM] Selecting decision makers for: '{query}'")
        print(f"[TECHCRUNCH_DM] Companies: {list(employees_by_company.keys())}")

        # Build context mapping
        company_context_map = {c.get("name", ""): c for c in companies_context}

        leads = []

        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            for company_name, employees in employees_by_company.items():
                if not employees:
                    continue

                context = company_context_map.get(company_name, {})
                funding = context.get("funding", "recently funded")
                description = context.get("description", "")
                article_url = context.get("article_url", "")

                # Format employees for LLM
                emp_text = "\n".join([
                    f"- {e.get('name', 'Unknown')}: {e.get('title', 'Unknown')} ({e.get('profile_url', '')})"
                    for e in employees[:20]
                ])

                response = client.beta.chat.completions.parse(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You identify the best decision makers to contact for a product. Select 1-3 people who would actually buy/use the product."},
                        {"role": "user", "content": f"Product: {query}\n\nCompany: {company_name}\nFunding: {funding}\nDoes: {description}\n\nEmployees:\n{emp_text}\n\nSelect 1-3 people who would buy this product."}
                    ],
                    response_format=DecisionMakersList,
                    temperature=0.3
                )

                result = response.choices[0].message.parsed

                for person in result.selected:
                    leads.append({
                        "name": person.name,
                        "title": person.title,
                        "company": company_name,
                        "linkedin_url": person.linkedin_url or "",
                        "intent_signal": f"Company {funding} - {person.reason}",
                        "intent_score": 75,
                        "source_platform": "techcrunch",
                        "source_url": article_url,
                        "priority": "warm",
                        "scoring_reasoning": f"Recently funded company, {person.reason}"
                    })

            print(f"[TECHCRUNCH_DM] Selected {len(leads)} decision makers")

            return json.dumps({
                "leads": leads,
                "count": len(leads),
                "done": f"Selected {len(leads)} decision makers from funded companies",
                "warning": "APPLY filter_sellers BEFORE using these leads! Some may be self-promoters.",
                "next": "Run filter_sellers on these leads to remove any sellers/promoters. Then leads are ready for outreach."
            })

        except Exception as e:
            print(f"[TECHCRUNCH_DM] Error: {e}")
            return json.dumps({
                "leads": [],
                "count": 0,
                "error": str(e),
                "recommendation": "Error selecting decision makers"
            })
