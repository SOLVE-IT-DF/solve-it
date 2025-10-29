#!/usr/bin/env python3
"""
Script to find the next available IDs for techniques, weaknesses, and mitigations
in the SOLVE-IT project. Also checks GitHub issues and PRs for reserved IDs.

Produced with Claude Code

"""

import os
import json
import re
import subprocess
import sys
from typing import Set, Dict, List, Tuple

class IDScanner:
    def __init__(self, project_root: str = None):
        # If no project_root specified, assume we're in reporting_scripts and go up one level
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.project_root = project_root
        self.technique_ids: Set[int] = set()
        self.mitigation_ids: Set[int] = set()
        self.weakness_ids: Set[int] = set()
        
        # IDs found in GitHub issues/PRs but not yet in files
        # Format: {id: [(issue_number, title, type)]}
        self.reserved_technique_ids: Dict[int, List[Tuple[int, str, str]]] = {}
        self.reserved_mitigation_ids: Dict[int, List[Tuple[int, str, str]]] = {}
        self.reserved_weakness_ids: Dict[int, List[Tuple[int, str, str]]] = {}
    
    def scan_local_files(self):
        """Scan local JSON files for existing IDs"""
        print("Scanning local files for existing IDs...")
        
        # Scan techniques
        technique_dir = os.path.join(self.project_root, "data", "techniques")
        if os.path.exists(technique_dir):
            for filename in os.listdir(technique_dir):
                if filename.startswith("T") and filename.endswith(".json"):
                    match = re.match(r"T(\d+)\.json", filename)
                    if match:
                        self.technique_ids.add(int(match.group(1)))
        
        # Scan mitigations
        mitigation_dir = os.path.join(self.project_root, "data", "mitigations")
        if os.path.exists(mitigation_dir):
            for filename in os.listdir(mitigation_dir):
                if filename.startswith("M") and filename.endswith(".json"):
                    match = re.match(r"M(\d+)\.json", filename)
                    if match:
                        self.mitigation_ids.add(int(match.group(1)))
        
        # Scan weaknesses
        weakness_dir = os.path.join(self.project_root, "data", "weaknesses")
        if os.path.exists(weakness_dir):
            for filename in os.listdir(weakness_dir):
                if filename.startswith("W") and filename.endswith(".json"):
                    match = re.match(r"W(\d+)\.json", filename)
                    if match:
                        self.weakness_ids.add(int(match.group(1)))
        
        print(f"Found {len(self.technique_ids)} techniques, {len(self.mitigation_ids)} mitigations, {len(self.weakness_ids)} weaknesses")
    
    def scan_github_issues_prs(self):
        """Scan GitHub issues and PRs for ID assignments"""
        print("Scanning GitHub issues and PRs for reserved IDs...")
        
        try:
            # Check if gh CLI is available
            check_result = subprocess.run(
                ["gh", "--version"], 
                capture_output=True, text=True, check=False
            )
            if check_result.returncode != 0:
                print("Warning: GitHub CLI (gh) not found or not working.")
                print("Install it from: https://cli.github.com/")
                print("Continuing with local file scan only...")
                return
            
            # Get issues with comments
            issues_result = subprocess.run(
                ["gh", "issue", "list", "--limit", "100", "--json", "number,title,body,comments", "--state", "all"],
                capture_output=True, text=True, check=True
            )
            issues = json.loads(issues_result.stdout)
            
            # Get PRs with comments
            prs_result = subprocess.run(
                ["gh", "pr", "list", "--limit", "100", "--json", "number,title,body,comments", "--state", "all"],
                capture_output=True, text=True, check=True
            )
            prs = json.loads(prs_result.stdout)
            
            # Process issues first, then PRs
            for items, item_type in [(issues, "issue"), (prs, "PR")]:
                for item in items:
                    number = item.get('number', 0)
                    title = item.get('title', '')
                    body = item.get('body', '')
                    
                    # Collect comment text
                    comment_text = ""
                    comments = item.get('comments', [])
                    for comment in comments:
                        comment_body = comment.get('body', '')
                        comment_text += f" {comment_body}"
                    
                    text_to_search = f"{title} {body} {comment_text}"
                    
                    # Find technique IDs (T1000-T9999, excluding obvious test cases like T9999)
                    t_matches = re.findall(r'\bT(1\d{3})\b', text_to_search)
                    for match in t_matches:
                        tid = int(match)
                        # Skip obvious test/placeholder IDs
                        if tid == 9999:
                            continue
                        if tid not in self.technique_ids:
                            if tid not in self.reserved_technique_ids:
                                self.reserved_technique_ids[tid] = []
                            # Avoid duplicates from same issue/PR
                            if (number, title, item_type) not in self.reserved_technique_ids[tid]:
                                self.reserved_technique_ids[tid].append((number, title, item_type))
                    
                    # Find mitigation IDs (M1000-M9999, excluding single digits)
                    m_matches = re.findall(r'\bM(1\d{3})\b', text_to_search)
                    for match in m_matches:
                        mid = int(match)
                        if mid not in self.mitigation_ids:
                            if mid not in self.reserved_mitigation_ids:
                                self.reserved_mitigation_ids[mid] = []
                            # Avoid duplicates from same issue/PR
                            if (number, title, item_type) not in self.reserved_mitigation_ids[mid]:
                                self.reserved_mitigation_ids[mid].append((number, title, item_type))
                    
                    # Find weakness IDs (W1000-W9999, excluding single digits)
                    w_matches = re.findall(r'\bW(1\d{3})\b', text_to_search)
                    for match in w_matches:
                        wid = int(match)
                        if wid not in self.weakness_ids:
                            if wid not in self.reserved_weakness_ids:
                                self.reserved_weakness_ids[wid] = []
                            # Avoid duplicates from same issue/PR
                            if (number, title, item_type) not in self.reserved_weakness_ids[wid]:
                                self.reserved_weakness_ids[wid].append((number, title, item_type))
            
            print(f"Found {len(self.reserved_technique_ids)} reserved technique IDs, " +
                  f"{len(self.reserved_mitigation_ids)} reserved mitigation IDs, " +
                  f"{len(self.reserved_weakness_ids)} reserved weakness IDs in GitHub")
            
        except FileNotFoundError:
            print("Warning: GitHub CLI (gh) not found.")
            print("Install it from: https://cli.github.com/")
            print("Continuing with local file scan only...")
        except subprocess.CalledProcessError as e:
            if "not logged into any GitHub hosts" in str(e.stderr):
                print("Warning: Not authenticated with GitHub CLI.")
                print("Run 'gh auth login' to authenticate, or continue with local scan only.")
            elif "could not resolve to a Repository" in str(e.stderr):
                print("Warning: Current directory is not a GitHub repository or remote not accessible.")
                print("Make sure you're in the correct repository directory.")
            else:
                print(f"Warning: GitHub CLI command failed: {e}")
                print("Error output:", e.stderr if hasattr(e, 'stderr') else "No error details available")
            print("Continuing with local file scan only...")
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse GitHub API response: {e}")
            print("The GitHub CLI might have returned unexpected output.")
            print("Continuing with local file scan only...")
        except Exception as e:
            print(f"Warning: Unexpected error while fetching GitHub data: {e}")
            print("Continuing with local file scan only...")
    
    def find_gaps(self, used_ids: Set[int], reserved_ids: Dict[int, List[Tuple[int, str, str]]]) -> List[int]:
        """Find gaps in the ID sequence"""
        all_used = used_ids | set(reserved_ids.keys())
        if not all_used:
            return []
        
        gaps = []
        min_id = min(all_used)
        max_id = max(all_used)
        
        for i in range(min_id, max_id + 1):
            if i not in all_used:
                gaps.append(i)
        
        return gaps
    
    def find_next_available(self, used_ids: Set[int], reserved_ids: Dict[int, List[Tuple[int, str, str]]], count: int = 5) -> List[int]:
        """Find the next available IDs after the highest used ID"""
        all_used = used_ids | set(reserved_ids.keys())
        if not all_used:
            return list(range(1001, 1001 + count))
        
        max_id = max(all_used)
        next_ids = []
        current = max_id + 1
        
        while len(next_ids) < count:
            if current not in all_used:
                next_ids.append(current)
            current += 1
        
        return next_ids
    
    def generate_report(self) -> str:
        """Generate a comprehensive report of ID usage and availability"""
        report = []
        report.append("SOLVE-IT ID Usage Report")
        report.append("=" * 50)
        report.append("")
        
        # Current usage summary
        report.append("Current Usage:")
        report.append(f"  Techniques: {len(self.technique_ids)} IDs (T{min(self.technique_ids) if self.technique_ids else 'N/A'} - T{max(self.technique_ids) if self.technique_ids else 'N/A'})")
        report.append(f"  Mitigations: {len(self.mitigation_ids)} IDs (M{min(self.mitigation_ids) if self.mitigation_ids else 'N/A'} - M{max(self.mitigation_ids) if self.mitigation_ids else 'N/A'})")
        report.append(f"  Weaknesses: {len(self.weakness_ids)} IDs (W{min(self.weakness_ids) if self.weakness_ids else 'N/A'} - W{max(self.weakness_ids) if self.weakness_ids else 'N/A'})")
        report.append("")
        
        # Reserved IDs from GitHub
        if self.reserved_technique_ids or self.reserved_mitigation_ids or self.reserved_weakness_ids:
            report.append("Reserved IDs (from GitHub issues/PRs):")
            
            if self.reserved_technique_ids:
                report.append("  Techniques:")
                for tid in sorted(self.reserved_technique_ids.keys()):
                    sources = self.reserved_technique_ids[tid]
                    for number, title, item_type in sources:
                        # Truncate title if too long
                        display_title = title[:60] + "..." if len(title) > 60 else title
                        report.append(f"    T{tid}: {item_type} #{number} - {display_title}")
            
            if self.reserved_mitigation_ids:
                report.append("  Mitigations:")
                for mid in sorted(self.reserved_mitigation_ids.keys()):
                    sources = self.reserved_mitigation_ids[mid]
                    for number, title, item_type in sources:
                        display_title = title[:60] + "..." if len(title) > 60 else title
                        report.append(f"    M{mid}: {item_type} #{number} - {display_title}")
            
            if self.reserved_weakness_ids:
                report.append("  Weaknesses:")
                for wid in sorted(self.reserved_weakness_ids.keys()):
                    sources = self.reserved_weakness_ids[wid]
                    for number, title, item_type in sources:
                        display_title = title[:60] + "..." if len(title) > 60 else title
                        report.append(f"    W{wid}: {item_type} #{number} - {display_title}")
            
            report.append("")
        
        # Find gaps and next available IDs
        technique_gaps = self.find_gaps(self.technique_ids, self.reserved_technique_ids)
        mitigation_gaps = self.find_gaps(self.mitigation_ids, self.reserved_mitigation_ids)
        weakness_gaps = self.find_gaps(self.weakness_ids, self.reserved_weakness_ids)
        
        technique_next = self.find_next_available(self.technique_ids, self.reserved_technique_ids)
        mitigation_next = self.find_next_available(self.mitigation_ids, self.reserved_mitigation_ids)
        weakness_next = self.find_next_available(self.weakness_ids, self.reserved_weakness_ids)
        
        # Available IDs section
        report.append("Available IDs:")
        report.append("")
        
        report.append("TECHNIQUES:")
        if technique_gaps:
            report.append(f"  Available gaps: T{', T'.join(map(str, technique_gaps[:10]))}")
            if len(technique_gaps) > 10:
                report.append(f"  (and {len(technique_gaps) - 10} more gaps)")
        else:
            report.append("  No gaps found in sequence")
        report.append(f"  Next available: T{', T'.join(map(str, technique_next))}")
        report.append("")
        
        report.append("MITIGATIONS:")
        if mitigation_gaps:
            report.append(f"  Available gaps: M{', M'.join(map(str, mitigation_gaps[:10]))}")
            if len(mitigation_gaps) > 10:
                report.append(f"  (and {len(mitigation_gaps) - 10} more gaps)")
        else:
            report.append("  No gaps found in sequence")
        report.append(f"  Next available: M{', M'.join(map(str, mitigation_next))}")
        report.append("")
        
        report.append("WEAKNESSES:")
        if weakness_gaps:
            report.append(f"  Available gaps: W{', W'.join(map(str, weakness_gaps[:10]))}")
            if len(weakness_gaps) > 10:
                report.append(f"  (and {len(weakness_gaps) - 10} more gaps)")
        else:
            report.append("  No gaps found in sequence")
        report.append(f"  Next available: W{', W'.join(map(str, weakness_next))}")
        report.append("")
        
        # Quick reference for next single ID
        report.append("QUICK REFERENCE - Next Single ID:")
        report.append(f"  Next Technique:  T{technique_next[0] if technique_next else 'N/A'}")
        report.append(f"  Next Mitigation: M{mitigation_next[0] if mitigation_next else 'N/A'}")
        report.append(f"  Next Weakness:   W{weakness_next[0] if weakness_next else 'N/A'}")
        
        return "\n".join(report)
    
    def run(self):
        """Run the complete ID scanning process"""
        self.scan_local_files()
        self.scan_github_issues_prs()
        return self.generate_report()

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Usage: python find_next_ids.py [project_root]")
        print("  project_root: Path to SOLVE-IT project (default: auto-detect from script location)")
        print("")
        print("This script scans for existing technique, mitigation, and weakness IDs")
        print("both in local files and GitHub issues/PRs, then reports the next")
        print("available IDs and any gaps in the sequence.")
        print("")
        print("Requirements:")
        print("  - GitHub CLI (gh) for fetching issues/PRs (optional, will fallback to local scan)")
        print("  - Run 'gh auth login' if you want to access private repositories")
        print("")
        print("When run from reporting_scripts/ folder, it automatically detects the project root.")
        return
    
    project_root = sys.argv[1] if len(sys.argv) > 1 else None
    
    scanner = IDScanner(project_root)
    report = scanner.run()
    print(report)

if __name__ == "__main__":
    main()