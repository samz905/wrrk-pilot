"""
Domain extraction tool for finding company domains from various sources.

Extracts company website domains from LinkedIn profiles, Twitter bios,
company names, and other text.
"""
from crewai.tools import BaseTool
from typing import Optional
from pydantic import Field
import re


class DomainExtractorTool(BaseTool):
    name: str = "Company Domain Extractor"
    description: str = """
    Extracts company website domains from text, profiles, and company names.

    Use this when you need to find:
    - Company domain from LinkedIn profile
    - Company domain from Twitter bio
    - Likely domain from company name ("DataTech Inc" → "datatech.com")

    Returns the extracted domain or a best guess based on company name.
    """

    def _run(self, text: str, company_name: str = "") -> str:
        """
        Extract company domain from text or generate from company name.

        Args:
            text: Text containing potential domain (profile, bio, etc.)
            company_name: Company name to generate domain from if not found in text

        Returns:
            JSON string with domain and confidence
        """
        # Try to extract domain from text first
        domain = self._extract_from_text(text)
        if domain:
            return f'{{"domain": "{domain}", "source": "extracted", "confidence": "high"}}'

        # If not found and company name provided, generate domain
        if company_name:
            domain = self._generate_from_company_name(company_name)
            return f'{{"domain": "{domain}", "source": "generated", "confidence": "medium", "note": "This is a guess based on company name"}}'

        return '{"domain": null, "source": "none", "confidence": "none", "error": "No domain found in text and no company name provided"}'

    def _extract_from_text(self, text: str) -> Optional[str]:
        """Extract domain from text using various patterns."""
        if not text:
            return None

        # Pattern 1: Full URLs
        url_pattern = r'https?://(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+)/?'
        urls = re.findall(url_pattern, text)
        if urls:
            # Filter out social media domains
            for url in urls:
                if not self._is_social_media(url):
                    return self._clean_domain(url)

        # Pattern 2: Email addresses
        email_pattern = r'@([a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+)'
        emails = re.findall(email_pattern, text)
        if emails:
            for email_domain in emails:
                if not self._is_common_email_provider(email_domain):
                    return self._clean_domain(email_domain)

        # Pattern 3: Standalone domains (word.com format)
        domain_pattern = r'\b([a-zA-Z0-9-]+\.(com|io|co|ai|net|org|app))\b'
        domains = re.findall(domain_pattern, text, re.IGNORECASE)
        if domains:
            for domain, _ in domains:
                if not self._is_social_media(domain):
                    return self._clean_domain(domain)

        return None

    def _generate_from_company_name(self, company_name: str) -> str:
        """Generate likely domain from company name."""
        # Remove common suffixes
        name = company_name.lower().strip()
        suffixes = [" inc", " inc.", " llc", " ltd", " limited", " corp", " corporation", " co", " company"]
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)].strip()

        # Remove non-alphanumeric except spaces
        name = re.sub(r'[^a-z0-9\s]', '', name)

        # Remove spaces
        name = name.replace(" ", "")

        # Common TLD priority for B2B companies
        # Try .com first (most common), then .io (tech startups), then .co
        return f"{name}.com"

    def _clean_domain(self, domain: str) -> str:
        """Clean and normalize domain."""
        # Remove www prefix
        domain = domain.lower().strip()
        if domain.startswith("www."):
            domain = domain[4:]

        # Remove trailing slashes, paths
        domain = domain.split("/")[0]

        # Remove port numbers
        domain = domain.split(":")[0]

        return domain

    def _is_social_media(self, domain: str) -> bool:
        """Check if domain is a social media site."""
        social_domains = [
            "linkedin.com", "twitter.com", "x.com", "facebook.com",
            "instagram.com", "youtube.com", "tiktok.com", "reddit.com",
            "github.com", "medium.com", "substack.com"
        ]
        return any(social in domain.lower() for social in social_domains)

    def _is_common_email_provider(self, domain: str) -> bool:
        """Check if domain is a common email provider (not company domain)."""
        providers = [
            "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
            "icloud.com", "aol.com", "protonmail.com", "mail.com"
        ]
        return domain.lower() in providers
