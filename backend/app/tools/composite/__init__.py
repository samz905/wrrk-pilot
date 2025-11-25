"""
Composite Tools for Sales Prospecting.

These tools chain multiple atomic tools for common prospecting workflows:
- IntentSignalHunterTool: Parallel search across LinkedIn, Reddit, Twitter
- CompanyTriggerScannerTool: Find companies with buying triggers
- DecisionMakerFinderTool: Find decision makers at companies
"""

from .intent_signal_hunter import IntentSignalHunterTool
from .company_trigger_scanner import CompanyTriggerScannerTool
from .decision_maker_finder import DecisionMakerFinderTool

__all__ = [
    "IntentSignalHunterTool",
    "CompanyTriggerScannerTool",
    "DecisionMakerFinderTool",
]
