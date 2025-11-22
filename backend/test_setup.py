"""Test script to verify Phase 1 setup."""
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_environment():
    """Test that environment variables are loaded."""
    print("=" * 60)
    print("TESTING ENVIRONMENT SETUP")
    print("=" * 60)

    apify_token = os.getenv("APIFY_API_TOKEN")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if apify_token:
        print(f"[OK] APIFY_API_TOKEN found: {apify_token[:10]}...")
    else:
        print("[FAIL] APIFY_API_TOKEN not found")

    if anthropic_key:
        print(f"[OK] ANTHROPIC_API_KEY found: {anthropic_key[:10]}...")
    else:
        print("[FAIL] ANTHROPIC_API_KEY not found")

    print()

def test_imports():
    """Test that all imports work."""
    print("=" * 60)
    print("TESTING IMPORTS")
    print("=" * 60)

    try:
        import fastapi
        print(f"[OK] FastAPI version: {fastapi.__version__}")
    except ImportError as e:
        print(f"[FAIL] FastAPI import failed: {e}")

    try:
        import crewai
        print(f"[OK] CrewAI imported successfully")
    except ImportError as e:
        print(f"[FAIL] CrewAI import failed: {e}")

    try:
        import httpx
        print(f"[OK] httpx imported successfully")
    except ImportError as e:
        print(f"[FAIL] httpx import failed: {e}")

    try:
        from tools.apify_linkedin import ApifyLinkedInSearchTool
        print(f"[OK] ApifyLinkedInSearchTool imported successfully")
    except ImportError as e:
        print(f"[FAIL] ApifyLinkedInSearchTool import failed: {e}")

    print()

def test_linkedin_tool():
    """Test LinkedIn tool (simple instantiation)."""
    print("=" * 60)
    print("TESTING LINKEDIN TOOL")
    print("=" * 60)

    try:
        from tools.apify_linkedin import ApifyLinkedInSearchTool

        tool = ApifyLinkedInSearchTool()
        print(f"[OK] Tool created successfully")
        print(f"  Name: {tool.name}")
        print(f"  Description: {tool.description[:80]}...")

    except Exception as e:
        print(f"[FAIL] Failed to create tool: {e}")

    print()

if __name__ == "__main__":
    print("\nPHASE 1 SETUP TEST\n")

    test_environment()
    test_imports()
    test_linkedin_tool()

    print("=" * 60)
    print("SETUP TEST COMPLETE")
    print("=" * 60)
    print("\nNext step: Install dependencies with 'pip install -r requirements.txt'")
    print("Then create a .env file with your API keys")
