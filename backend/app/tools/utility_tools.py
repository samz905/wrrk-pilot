"""
Utility Tools for Lead Processing

Explicit tools for common operations that LLMs sometimes fail at:
- deduplicate_leads: Remove duplicate leads
- validate_leads: Check required fields exist
- fix_encoding: Handle encoding errors in text

v3.5: Part of Flow-based orchestrator architecture.
"""
import json
import re
from typing import Type, List, Dict, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class DeduplicateInput(BaseModel):
    """Input schema for deduplicate_leads tool."""
    leads: List[Dict] = Field(..., description="List of leads to deduplicate")


class DeduplicateLeadsTool(BaseTool):
    """
    Explicit deduplication tool - removes duplicate leads.

    Deduplication rules:
    1. Same name + same company = duplicate (keep higher score)
    2. Same LinkedIn URL = duplicate (keep higher score)
    3. Same email = duplicate (keep higher score)
    """
    name: str = "deduplicate_leads"
    description: str = """
    Remove duplicate leads from a list. Keeps the version with higher intent_score.

    Deduplication keys (in order):
    1. linkedin_url (if present)
    2. name + company combination
    3. email (if present)

    Returns JSON with:
    - leads: Deduplicated lead list
    - count: Number of unique leads
    - duplicates_removed: Number of duplicates removed
    """
    args_schema: Type[BaseModel] = DeduplicateInput

    def _run(self, leads: List[Dict]) -> str:
        """Execute deduplication."""
        if not leads:
            return json.dumps({
                "leads": [],
                "count": 0,
                "duplicates_removed": 0
            })

        seen = {}  # key -> lead
        unique = []
        duplicates_removed = 0

        for lead in leads:
            key = self._get_dedup_key(lead)
            if key is None:
                # No valid key, keep the lead
                unique.append(lead)
                continue

            if key in seen:
                # Duplicate found - keep higher score
                existing = seen[key]
                if lead.get('intent_score', 0) > existing.get('intent_score', 0):
                    # Replace with higher-scored lead
                    unique.remove(existing)
                    unique.append(lead)
                    seen[key] = lead
                duplicates_removed += 1
            else:
                seen[key] = lead
                unique.append(lead)

        return json.dumps({
            "leads": unique,
            "count": len(unique),
            "duplicates_removed": duplicates_removed
        }, indent=2)

    def _get_dedup_key(self, lead: Dict) -> Optional[str]:
        """Generate deduplication key for a lead."""
        # Priority 1: LinkedIn URL
        linkedin_url = lead.get('linkedin_url', '')
        if linkedin_url and 'linkedin.com/in/' in linkedin_url:
            # Normalize URL
            url = linkedin_url.lower().rstrip('/')
            return f"linkedin:{url}"

        # Priority 2: Name + Company
        name = lead.get('name', '').lower().strip()
        company = lead.get('company', '').lower().strip()
        if name and company:
            return f"name_company:{name}:{company}"

        # Priority 3: Email
        email = lead.get('email', '').lower().strip()
        if email:
            return f"email:{email}"

        # Priority 4: Just name (fallback)
        if name:
            return f"name:{name}"

        return None


class ValidateInput(BaseModel):
    """Input schema for validate_leads tool."""
    leads: List[Dict] = Field(..., description="List of leads to validate")


class ValidateLeadsTool(BaseTool):
    """
    Validates lead data quality - ensures required fields exist.

    Required fields:
    - name
    - intent_signal
    - source_platform

    Optional but valuable:
    - company
    - title
    - linkedin_url
    - intent_score
    """
    name: str = "validate_leads"
    description: str = """
    Validate lead data quality. Checks for required fields.

    Required: name, intent_signal, source_platform
    Optional but tracked: company, title, linkedin_url, intent_score

    Returns JSON with:
    - valid_leads: Leads with all required fields
    - invalid_leads: Leads missing required fields
    - valid_count: Number of valid leads
    - invalid_count: Number of invalid leads
    - missing_optional: Count of leads missing optional fields
    """
    args_schema: Type[BaseModel] = ValidateInput

    def _run(self, leads: List[Dict]) -> str:
        """Execute validation."""
        if not leads:
            return json.dumps({
                "valid_leads": [],
                "invalid_leads": [],
                "valid_count": 0,
                "invalid_count": 0,
                "missing_optional": {}
            })

        required = ['name', 'intent_signal', 'source_platform']
        optional = ['company', 'title', 'linkedin_url', 'intent_score']

        valid = []
        invalid = []
        missing_optional_counts = {f: 0 for f in optional}

        for lead in leads:
            missing_required = [f for f in required if not lead.get(f)]

            if missing_required:
                invalid.append({
                    "lead": lead,
                    "missing": missing_required
                })
            else:
                valid.append(lead)

                # Track missing optional fields
                for field in optional:
                    if not lead.get(field):
                        missing_optional_counts[field] += 1

        return json.dumps({
            "valid_leads": valid,
            "invalid_leads": invalid,
            "valid_count": len(valid),
            "invalid_count": len(invalid),
            "missing_optional": missing_optional_counts
        }, indent=2)


class FixEncodingInput(BaseModel):
    """Input schema for fix_encoding tool."""
    text: str = Field(..., description="Text with potential encoding issues")


class FixEncodingTool(BaseTool):
    """
    Fix encoding issues in text data.

    Common issues:
    - Surrogate characters (\\udcXX)
    - Invalid UTF-8 sequences
    - Mixed encodings
    """
    name: str = "fix_encoding"
    description: str = """
    Fix encoding issues in text. Handles:
    - Surrogate characters (\\udcXX)
    - Invalid UTF-8 sequences
    - Mixed encodings

    Returns cleaned text with encoding issues replaced by safe characters.
    """
    args_schema: Type[BaseModel] = FixEncodingInput

    def _run(self, text: str) -> str:
        """Fix encoding issues."""
        if not text:
            return ""

        try:
            # Method 1: Encode to UTF-8 with error handling
            fixed = text.encode('utf-8', errors='replace').decode('utf-8')

            # Method 2: Remove surrogate characters
            fixed = re.sub(r'[\ud800-\udfff]', '', fixed)

            # Method 3: Replace common problematic patterns
            fixed = fixed.replace('\x00', '')  # Null bytes
            fixed = fixed.replace('\ufffd', '?')  # Replacement character

            return fixed

        except Exception as e:
            # Last resort: ASCII only
            return text.encode('ascii', errors='replace').decode('ascii')


# Export all tools
def get_utility_tools() -> List[BaseTool]:
    """Get all utility tools for use in crews."""
    return [
        DeduplicateLeadsTool(),
        ValidateLeadsTool(),
        FixEncodingTool()
    ]


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("UTILITY TOOLS TEST")
    print("=" * 70)

    # Test deduplication
    print("\n--- Deduplicate Test ---")
    dedup_tool = DeduplicateLeadsTool()
    test_leads = [
        {"name": "John Doe", "company": "Acme", "intent_score": 80, "linkedin_url": "https://linkedin.com/in/johndoe"},
        {"name": "John Doe", "company": "Acme", "intent_score": 90, "linkedin_url": "https://linkedin.com/in/johndoe"},  # Duplicate, higher score
        {"name": "Jane Smith", "company": "TechCo", "intent_score": 75},
        {"name": "jane smith", "company": "techco", "intent_score": 70},  # Case-insensitive duplicate
    ]
    result = dedup_tool._run(test_leads)
    print(result)

    # Test validation
    print("\n--- Validate Test ---")
    validate_tool = ValidateLeadsTool()
    test_leads = [
        {"name": "Valid Lead", "intent_signal": "Looking for CRM", "source_platform": "reddit", "company": "Test"},
        {"name": "Missing Signal", "source_platform": "reddit"},  # Missing intent_signal
        {"intent_signal": "No name", "source_platform": "techcrunch"},  # Missing name
    ]
    result = validate_tool._run(test_leads)
    print(result)

    # Test encoding fix
    print("\n--- Fix Encoding Test ---")
    fix_tool = FixEncodingTool()
    test_text = "Hello \udcbb world"  # Contains surrogate character
    result = fix_tool._run(test_text)
    print(f"Input: {repr(test_text)}")
    print(f"Output: {repr(result)}")
