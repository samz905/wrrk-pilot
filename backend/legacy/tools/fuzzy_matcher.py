"""
Fuzzy matching tool for deduplicating leads across platforms.

Matches names and company names with tolerance for typos, variations,
and different formats.
"""
from crewai.tools import BaseTool
from typing import Optional
from pydantic import Field
from difflib import SequenceMatcher


class FuzzyMatcherTool(BaseTool):
    name: str = "Fuzzy Name and Company Matcher"
    description: str = """
    Determines if two names or company names are likely the same person/company
    despite typos, variations, or different formats.

    Use this when comparing:
    - Names: "John Smith" vs "Jon Smith" vs "J. Smith"
    - Companies: "DataTech Inc" vs "DataTech" vs "Data Tech"

    Returns a match score (0-100) and whether it's a match (>80 = match).
    """

    def _run(self, string1: str, string2: str, match_type: str = "name") -> str:
        """
        Compare two strings and determine if they match.

        Args:
            string1: First string to compare
            string2: Second string to compare
            match_type: Type of matching ('name' or 'company')

        Returns:
            JSON string with match score and decision
        """
        if not string1 or not string2:
            return '{"match": false, "score": 0, "reason": "Empty string provided"}'

        # Normalize strings
        s1 = self._normalize(string1, match_type)
        s2 = self._normalize(string2, match_type)

        # If exact match after normalization
        if s1 == s2:
            return f'{{"match": true, "score": 100, "reason": "Exact match after normalization"}}'

        # Calculate similarity ratio
        ratio = SequenceMatcher(None, s1, s2).ratio()
        score = int(ratio * 100)

        # Additional checks for names
        if match_type == "name":
            score = self._adjust_name_score(string1, string2, score)

        # Additional checks for companies
        if match_type == "company":
            score = self._adjust_company_score(string1, string2, score)

        # Decision threshold
        is_match = score >= 80

        return f'{{"match": {str(is_match).lower()}, "score": {score}, "string1_normalized": "{s1}", "string2_normalized": "{s2}"}}'

    def _normalize(self, text: str, match_type: str) -> str:
        """Normalize text for comparison."""
        # Lowercase
        text = text.lower().strip()

        # Remove extra whitespace
        text = " ".join(text.split())

        # For companies, remove common suffixes
        if match_type == "company":
            suffixes = [" inc", " inc.", " llc", " ltd", " limited", " corp", " corporation", " co"]
            for suffix in suffixes:
                if text.endswith(suffix):
                    text = text[:-len(suffix)].strip()

        # Remove punctuation except spaces
        text = "".join(c if c.isalnum() or c.isspace() else "" for c in text)

        return text

    def _adjust_name_score(self, name1: str, name2: str, base_score: int) -> int:
        """Adjust score for name-specific matching rules."""
        # Split into parts
        parts1 = name1.lower().split()
        parts2 = name2.lower().split()

        # If last names match exactly, boost score
        if parts1 and parts2:
            if parts1[-1] == parts2[-1]:
                base_score = min(100, base_score + 20)

            # If first initial matches and last name matches
            if len(parts1[0]) > 0 and len(parts2[0]) > 0:
                if parts1[0][0] == parts2[0][0] and parts1[-1] == parts2[-1]:
                    base_score = min(100, base_score + 15)

        return base_score

    def _adjust_company_score(self, company1: str, company2: str, base_score: int) -> int:
        """Adjust score for company-specific matching rules."""
        c1 = company1.lower()
        c2 = company2.lower()

        # If one is contained in the other (e.g., "DataTech" in "DataTech Solutions")
        if c1 in c2 or c2 in c1:
            base_score = min(100, base_score + 25)

        # If both have same first word and it's substantial (4+ chars)
        words1 = c1.split()
        words2 = c2.split()
        if words1 and words2 and len(words1[0]) >= 4:
            if words1[0] == words2[0]:
                base_score = min(100, base_score + 20)

        return base_score
