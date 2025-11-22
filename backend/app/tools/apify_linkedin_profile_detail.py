"""Apify LinkedIn Profile Detail tool - Deep profile scraping with email."""
from typing import Type, Optional, List, Dict, Any
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from apify_client import ApifyClient
import os


class LinkedInProfileDetailInput(BaseModel):
    """Input schema for LinkedIn profile detail scraper."""
    profile_url: str = Field(..., description="LinkedIn profile URL to scrape (e.g., https://www.linkedin.com/in/john-smith)")


class ApifyLinkedInProfileDetailTool(BaseTool):
    """Deep scrape LinkedIn profile for contact data and detailed information."""

    name: str = "LinkedIn Profile Detail Scraper"
    description: str = """
    Extract detailed information from a LinkedIn profile URL including:
    - Email address (if publicly available)
    - Phone number (if available)
    - Complete work history with descriptions
    - Skills and endorsements
    - Education details
    - Certifications and courses
    - Recommendations count

    Use this to enrich high-priority leads with contact information.

    Example usage:
    - profile_url: "https://www.linkedin.com/in/sarah-johnson"
    - Returns: Full profile data including email if available
    """
    args_schema: Type[BaseModel] = LinkedInProfileDetailInput

    def _run(
        self,
        profile_url: str
    ) -> str:
        """Execute LinkedIn profile detail scraping via Apify."""
        try:
            apify_token = os.getenv("APIFY_API_TOKEN")
            if not apify_token:
                return "Error: APIFY_API_TOKEN not found in environment"

            print(f"\n[INFO] Scraping detailed profile data for: {profile_url}")

            # Initialize Apify client
            client = ApifyClient(apify_token)

            # Prepare Actor input for apimaestro/linkedin-profile-detail
            run_input = {
                "profileUrls": [profile_url],
                "proxyConfig": {
                    "useApifyProxy": True
                }
            }

            print(f"[INFO] Calling Apify actor VhxlqQXRwhW8H5hNV (LinkedIn Profile Detail)...")

            # Run the Actor and wait for it to finish
            run = client.actor("VhxlqQXRwhW8H5hNV").call(run_input=run_input)

            print(f"[INFO] Actor run completed. Fetching profile details...")

            # Fetch results from the run's dataset
            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                results.append(item)

            if not results:
                return f"No profile data found for {profile_url}"

            print(f"[INFO] Profile data retrieved successfully")

            if results:
                print(f"\n[DEBUG] Profile data keys: {list(results[0].keys())}\n")

            return self._format_profile_detail(results[0])

        except Exception as e:
            return f"Error scraping profile detail: {str(e)}"

    def _format_profile_detail(self, profile: Dict[str, Any]) -> str:
        """Format detailed profile data into structured text."""

        # Extract basic info
        name = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip() or 'N/A'
        headline = profile.get('headline', 'N/A')
        location = profile.get('location', {})
        if isinstance(location, dict):
            location_str = location.get('linkedinText', 'N/A')
        else:
            location_str = str(location) if location else 'N/A'

        # Extract contact info (KEY VALUE!)
        email = profile.get('email', profile.get('emailAddress', 'Not available'))
        phone = profile.get('phone', profile.get('phoneNumber', 'Not available'))

        # Extract current position
        current_position = profile.get('currentPosition', {})
        if isinstance(current_position, dict):
            company = current_position.get('companyName', 'N/A')
            title = current_position.get('title', headline)
        else:
            company = 'N/A'
            title = headline

        # Extract experience count
        experience = profile.get('experience', [])
        experience_count = len(experience) if isinstance(experience, list) else 0

        # Extract education
        education = profile.get('education', [])
        education_str = "None listed"
        if isinstance(education, list) and education:
            edu_item = education[0]
            if isinstance(edu_item, dict):
                school = edu_item.get('schoolName', 'N/A')
                degree = edu_item.get('degreeName', 'N/A')
                education_str = f"{degree} from {school}"

        # Extract skills
        skills = profile.get('skills', [])
        if isinstance(skills, list):
            top_skills = [s.get('name', s) if isinstance(s, dict) else s for s in skills[:5]]
            skills_str = ", ".join(top_skills) if top_skills else "None listed"
        else:
            skills_str = "None listed"

        # Extract connections
        connections = profile.get('connectionsCount', 'N/A')

        # Extract about/summary
        about = profile.get('about', profile.get('summary', ''))
        summary = (about[:300] + '...') if about and len(about) > 300 else (about or 'N/A')

        formatted_detail = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ENRICHED PROFILE DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 BASIC INFORMATION
   Name: {name}
   Title: {title}
   Company: {company}
   Location: {location_str}

📧 CONTACT INFORMATION (HIGH VALUE!)
   Email: {email}
   Phone: {phone}
   LinkedIn: {profile.get('linkedinUrl', profile.get('url', 'N/A'))}

💼 PROFESSIONAL DETAILS
   Total Positions: {experience_count}
   Connections: {connections}
   Education: {education_str}

🎯 TOP SKILLS
   {skills_str}

📝 SUMMARY
   {summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ENRICHMENT COMPLETE
   Email Available: {"YES ✓" if email != "Not available" else "NO ✗"}
   Phone Available: {"YES ✓" if phone != "Not available" else "NO ✗"}
   Ready for Outreach: {"YES - Contact info found!" if email != "Not available" else "Partial - Manual lookup needed"}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return formatted_detail
