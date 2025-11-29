"""Lead Exporter - Export leads to JSON and CSV formats."""

import csv
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional


def export_leads_json(
    leads: List[Dict[str, Any]],
    filepath: str,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Export leads to a JSON file with metadata.

    Args:
        leads: List of lead dictionaries
        filepath: Path to save the JSON file
        metadata: Optional additional metadata to include

    Returns:
        The filepath where the file was saved
    """
    # Calculate statistics
    hot_leads = [l for l in leads if l.get('intent_score', 0) >= 80]
    warm_leads = [l for l in leads if 60 <= l.get('intent_score', 0) < 80]
    cold_leads = [l for l in leads if l.get('intent_score', 0) < 60]

    # Count by platform (map source_platform to platform)
    platforms = {}
    for lead in leads:
        platform = lead.get('platform', lead.get('source_platform', 'unknown'))
        platforms[platform] = platforms.get(platform, 0) + 1

    # Count by user type
    user_types = {}
    for lead in leads:
        user_type = lead.get('user_type', 'unknown')
        user_types[user_type] = user_types.get(user_type, 0) + 1

    output = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_leads": len(leads),
            "hot_leads": len(hot_leads),
            "warm_leads": len(warm_leads),
            "cold_leads": len(cold_leads),
            "leads_by_platform": platforms,
            "leads_by_user_type": user_types,
            "average_intent_score": round(
                sum(l.get('intent_score', 0) for l in leads) / len(leads), 1
            ) if leads else 0,
            **(metadata or {})
        },
        "leads": leads
    }

    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    print(f"[EXPORT] Saved {len(leads)} leads to {filepath}")
    return filepath


def export_leads_csv(
    leads: List[Dict[str, Any]],
    filepath: str
) -> str:
    """
    Export leads to a CSV file.

    Args:
        leads: List of lead dictionaries
        filepath: Path to save the CSV file

    Returns:
        The filepath where the file was saved
    """
    if not leads:
        print("[EXPORT] No leads to export")
        return filepath

    # Define CSV columns in order of importance
    fieldnames = [
        'name',
        'username',
        'title',
        'company',
        'intent_score',
        'priority',
        'buying_signal',
        'fit_reasoning',
        'platform',
        'user_type',
        'is_problem_relater',
        'email',
        'phone',
        'linkedin_url',
        'url',
        'source_url',
        'source_title',
        'source_subreddit'
    ]

    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        for lead in leads:
            # Flatten source_post if present
            row = lead.copy()
            if 'source_post' in row:
                source = row.pop('source_post')
                row['source_url'] = source.get('url', '')
                row['source_title'] = source.get('title', '')
                row['source_subreddit'] = source.get('subreddit', '')

            # Map tool field names to CSV column names
            # Tools use: intent_signal, scoring_reasoning, source_platform
            # CSV expects: buying_signal, fit_reasoning, platform
            if 'intent_signal' in row and not row.get('buying_signal'):
                row['buying_signal'] = row.get('intent_signal', '')
            if 'scoring_reasoning' in row and not row.get('fit_reasoning'):
                row['fit_reasoning'] = row.get('scoring_reasoning', '')
            if 'source_platform' in row and not row.get('platform'):
                row['platform'] = row.get('source_platform', '')

            # Calculate priority from intent_score
            score = row.get('intent_score', 0)
            if score >= 80:
                row['priority'] = 'hot'
            elif score >= 60:
                row['priority'] = 'warm'
            else:
                row['priority'] = 'cold'

            writer.writerow(row)

    print(f"[EXPORT] Saved {len(leads)} leads to {filepath}")
    return filepath


def format_leads_table(leads: List[Dict[str, Any]], max_rows: int = 50) -> str:
    """
    Format leads as a text table for display.

    Args:
        leads: List of lead dictionaries
        max_rows: Maximum rows to display

    Returns:
        Formatted text table
    """
    if not leads:
        return "No leads to display"

    # Sort by intent score descending
    sorted_leads = sorted(leads, key=lambda x: x.get('intent_score', 0), reverse=True)

    lines = []
    lines.append("="*100)
    lines.append(f"{'#':<4} {'Name':<25} {'Platform':<10} {'Score':<6} {'Type':<12} {'Signal':<40}")
    lines.append("-"*100)

    for i, lead in enumerate(sorted_leads[:max_rows], 1):
        name = lead.get('username', lead.get('name', 'Unknown'))[:24]
        # Map source_platform to platform
        platform = lead.get('platform', lead.get('source_platform', 'unknown'))[:9]
        score = lead.get('intent_score', 0)
        user_type = lead.get('user_type', 'unknown')[:11]
        # Map intent_signal to buying_signal
        signal = lead.get('buying_signal', lead.get('intent_signal', ''))[:39]

        # Add priority indicator
        if score >= 80:
            priority = "HOT"
        elif score >= 60:
            priority = "WARM"
        else:
            priority = "COLD"

        lines.append(f"{i:<4} {name:<25} {platform:<10} {score:<3} {priority:<3} {user_type:<12} {signal}")

    if len(sorted_leads) > max_rows:
        lines.append(f"\n... and {len(sorted_leads) - max_rows} more leads")

    lines.append("="*100)

    # Summary statistics
    hot = sum(1 for l in leads if l.get('intent_score', 0) >= 80)
    warm = sum(1 for l in leads if 60 <= l.get('intent_score', 0) < 80)
    cold = sum(1 for l in leads if l.get('intent_score', 0) < 60)

    lines.append(f"\nTOTAL: {len(leads)} leads | HOT: {hot} | WARM: {warm} | COLD: {cold}")

    return "\n".join(lines)


def merge_leads(
    *lead_lists: List[Dict[str, Any]],
    dedupe_by: str = "username"
) -> List[Dict[str, Any]]:
    """
    Merge multiple lead lists and remove duplicates.

    Args:
        *lead_lists: Variable number of lead lists to merge
        dedupe_by: Field to use for deduplication (default: "username")

    Returns:
        Merged and deduplicated list of leads
    """
    seen = set()
    merged = []

    for lead_list in lead_lists:
        for lead in lead_list:
            key = lead.get(dedupe_by, '')
            if key and key not in seen:
                seen.add(key)
                merged.append(lead)
            elif not key:
                # No key field, include anyway
                merged.append(lead)

    # Sort by intent score
    merged.sort(key=lambda x: x.get('intent_score', 0), reverse=True)

    print(f"[MERGE] Combined {sum(len(l) for l in lead_lists)} leads into {len(merged)} unique leads")
    return merged
