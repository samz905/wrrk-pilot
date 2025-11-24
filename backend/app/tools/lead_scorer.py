"""
Lead Scorer tool for calculating final lead quality scores.

Combines multiple scoring factors:
- ICP fit score
- Intent signal strength
- Contact quality (email, LinkedIn, etc.)
- Data completeness
- Recency/timing
"""
from crewai.tools import BaseTool
import json


class LeadScorerTool(BaseTool):
    name: str = "Lead Quality Scorer"
    description: str = """
    Calculates a comprehensive lead quality score (0-100).

    Combines multiple factors:
    - ICP fit score (from ICP Matcher)
    - Intent signal strength
    - Contact information quality
    - Data completeness
    - Platform diversity (found on multiple platforms)

    Returns final score with detailed breakdown.
    """

    def _run(
        self,
        icp_score: int = 0,
        tier: int = 3,
        has_email: bool = False,
        has_linkedin: bool = False,
        intent_strength: str = "low",
        data_completeness: int = 50
    ) -> str:
        """
        Calculate comprehensive lead score.

        Args:
            icp_score: Score from ICP Matcher (0-100)
            tier: Platform tier (1=3+ platforms, 2=2 platforms, 3=1 platform)
            has_email: Whether email is available
            has_linkedin: Whether LinkedIn profile is available
            intent_strength: "high", "medium", or "low"
            data_completeness: Percentage of fields populated (0-100)

        Returns:
            JSON string with final score and breakdown
        """
        # Start with ICP score as base (worth 40% of final score)
        base_score = icp_score * 0.4

        # Platform diversity bonus (worth 20% of final score)
        tier_scores = {1: 20, 2: 15, 3: 10}
        platform_score = tier_scores.get(tier, 5)

        # Contact quality bonus (worth 20% of final score)
        contact_score = 0
        if has_email:
            contact_score += 12
        if has_linkedin:
            contact_score += 8

        # Intent strength bonus (worth 15% of final score)
        intent_scores = {"high": 15, "medium": 10, "low": 5}
        intent_score = intent_scores.get(intent_strength.lower(), 5)

        # Data completeness bonus (worth 5% of final score)
        completeness_score = data_completeness * 0.05

        # Calculate final score
        final_score = int(base_score + platform_score + contact_score + intent_score + completeness_score)
        final_score = min(100, max(0, final_score))  # Clamp to 0-100

        # Build breakdown
        breakdown = {
            "icp_contribution": int(base_score),
            "platform_diversity": platform_score,
            "contact_quality": contact_score,
            "intent_strength": intent_score,
            "data_completeness": int(completeness_score)
        }

        # Determine priority
        if final_score >= 80:
            priority = "hot"
            recommendation = "Immediate outreach recommended"
        elif final_score >= 60:
            priority = "warm"
            recommendation = "Prioritize for outreach"
        elif final_score >= 40:
            priority = "cold"
            recommendation = "Add to nurture campaign"
        else:
            priority = "disqualified"
            recommendation = "Skip or deprioritize"

        return json.dumps({
            "final_score": final_score,
            "priority": priority,
            "recommendation": recommendation,
            "breakdown": breakdown
        })
