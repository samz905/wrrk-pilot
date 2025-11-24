"""
ICP Matcher tool for scoring leads against Ideal Customer Profile.

Evaluates how well a lead matches the target ICP based on:
- Job title relevance
- Company industry
- Company size indicators
- Seniority level
"""
from crewai.tools import BaseTool
from typing import Optional


class ICPMatcherTool(BaseTool):
    name: str = "ICP Matcher"
    description: str = """
    Scores how well a lead matches the Ideal Customer Profile (ICP).

    Use this when you need to evaluate:
    - Job title fit (is this a decision-maker?)
    - Industry relevance
    - Company size signals
    - Seniority level

    Returns a score (0-100) and breakdown of why it matches or doesn't match.
    """

    def _run(self, title: str = "", company: str = "", industry: str = "", signals: str = "") -> str:
        """
        Score lead against ICP criteria.

        Args:
            title: Job title (e.g., "VP of Sales", "CEO")
            company: Company name
            industry: Industry or business type
            signals: Intent signals or context about the lead

        Returns:
            JSON string with ICP score and reasoning
        """
        score = 0
        reasons = []

        # Normalize inputs
        title_lower = title.lower() if title else ""
        company_lower = company.lower() if company else ""
        industry_lower = industry.lower() if industry else ""
        signals_lower = signals.lower() if signals else ""

        # TITLE SCORING (0-50 points)
        title_score = self._score_title(title_lower, reasons)
        score += title_score

        # INDUSTRY SCORING (0-25 points)
        industry_score = self._score_industry(industry_lower, company_lower, signals_lower, reasons)
        score += industry_score

        # SIGNALS SCORING (0-25 points)
        signals_score = self._score_signals(signals_lower, reasons)
        score += signals_score

        # Determine fit level
        if score >= 80:
            fit_level = "excellent"
        elif score >= 60:
            fit_level = "good"
        elif score >= 40:
            fit_level = "fair"
        else:
            fit_level = "poor"

        return f'{{"score": {score}, "fit_level": "{fit_level}", "reasons": {reasons}}}'

    def _score_title(self, title: str, reasons: list) -> int:
        """Score job title (0-50 points)."""
        score = 0

        # Executive level (50 points)
        executive_titles = ["ceo", "chief executive", "founder", "co-founder", "president", "owner"]
        if any(exec_title in title for exec_title in executive_titles):
            score = 50
            reasons.append("C-level executive (highest authority)")
            return score

        # VP/Director level (40 points)
        vp_titles = ["vp", "vice president", "director", "head of"]
        if any(vp_title in title for vp_title in vp_titles):
            score = 40
            # Bonus for revenue-related roles
            if any(dept in title for dept in ["sales", "revenue", "business development", "growth"]):
                score += 5
                reasons.append("VP/Director in revenue organization (high authority)")
            else:
                reasons.append("VP/Director level (good authority)")
            return score

        # Manager level (25 points)
        manager_titles = ["manager", "lead", "senior"]
        if any(mgr_title in title for mgr_title in manager_titles):
            score = 25
            if any(dept in title for dept in ["sales", "revenue", "business"]):
                score += 5
                reasons.append("Manager in sales/revenue (moderate authority)")
            else:
                reasons.append("Manager level (some authority)")
            return score

        # Individual contributor (10 points)
        if title:
            score = 10
            reasons.append("Individual contributor (limited authority)")
        else:
            reasons.append("No title provided (unknown authority)")

        return score

    def _score_industry(self, industry: str, company: str, signals: str, reasons: list) -> int:
        """Score industry fit (0-25 points)."""
        score = 0

        # Target industries for B2B SaaS tools (adjust based on your ICP)
        target_keywords = [
            "saas", "software", "tech", "technology", "startup",
            "b2b", "enterprise", "cloud", "platform", "services"
        ]

        # Check industry field
        if industry:
            if any(keyword in industry for keyword in target_keywords):
                score = 25
                reasons.append("Perfect industry fit (B2B/SaaS)")
                return score
            else:
                score = 15
                reasons.append("Acceptable industry")
                return score

        # Check company name for tech indicators
        tech_indicators = ["tech", "soft", "data", "cloud", "ai", "io", ".com"]
        if any(indicator in company for indicator in tech_indicators):
            score = 20
            reasons.append("Tech company indicators in name")
            return score

        # Check signals for industry context
        if any(keyword in signals for keyword in target_keywords):
            score = 15
            reasons.append("Industry signals detected")
            return score

        reasons.append("No industry information")
        return score

    def _score_signals(self, signals: str, reasons: list) -> int:
        """Score intent signals (0-25 points)."""
        score = 0

        if not signals:
            reasons.append("No intent signals")
            return score

        # High intent signals (25 points)
        high_intent = [
            "looking for", "need", "searching", "evaluating", "considering",
            "switching from", "migrating", "replacing", "alternative to",
            "budget approved", "ready to buy", "procurement"
        ]
        if any(signal in signals for signal in high_intent):
            score = 25
            reasons.append("Strong buying intent detected")
            return score

        # Medium intent signals (15 points)
        medium_intent = [
            "frustrated with", "problem with", "issue", "challenge",
            "unhappy", "disappointed", "too expensive", "slow",
            "missing feature", "wish", "would love"
        ]
        if any(signal in signals for signal in medium_intent):
            score = 15
            reasons.append("Pain points identified")
            return score

        # Low intent signals (10 points)
        low_intent = [
            "interested in", "curious", "wondering", "asking about",
            "heard about", "seen", "mentioned"
        ]
        if any(signal in signals for signal in low_intent):
            score = 10
            reasons.append("Some interest detected")
            return score

        # Has signals but not categorized (5 points)
        score = 5
        reasons.append("General signals present")
        return score
