import argparse
import re
import sys

from jira import JIRA, JIRAError
from SprintReport.jira_api import jira_api

jira_server = ""

def get_bug_id(summary):
    "Extract the bug id from a jira title which would include LP#"
    id = ""

    if "LP#" in summary:
        for char in summary[summary.find("LP#")+3:]:
            if char.isdigit():
                id = id + char
            else:
                break

    return id


def find_issue_in_jira_sprint(jira_api, project, sprint):
    if not jira_api or not project:
        return {}, {}

    found_issues = {}
    analytics = {
        "total_issues": 0,
        "completed_issues": 0,
        "total_story_points": 0.0,
        "completed_story_points": 0.0
    }

    sprint_goal = ""
    # First, get completed issues
    request = "project = {} " \
        "AND sprint = \"{}\" " \
        "AND status = Done AND issueType != Sub-task ORDER BY \'Epic Link\'".format(project, sprint)
    issues = jira_api.search_issues(request)

    # For each issue in JIRA with LP# in the title
    for issue in issues:
        for pulse in issue.fields.customfield_10020:
            if pulse.name == sprint:
                sprint_goal = pulse.goal
        summary = issue.fields.summary
        issue_type = issue.fields.issuetype.name
        if hasattr(issue.fields, "parent"):
            epic = jira_api.issue(issue.fields.parent.key)
            epic_summary = epic.fields.summary
            epic_status = str(epic.fields.status)
        else:
            epic = ""
            epic_summary = "Other"
            epic_status = "Other"

        if epic:
            epic_summary = "{} : {}".format(key_to_md(epic.key), epic_summary)

        found_issues[issue.key]= {
            "key":issue.key,
            "type":issue_type,
            "epic":epic_summary,
            "epic_status":epic_status,
            "summary":summary}

    # Now get all issues in sprint for analytics
    request_all = "project = {} " \
        "AND sprint = \"{}\" " \
        "AND issueType != Sub-task".format(project, sprint)
    all_issues = jira_api.search_issues(request_all)
    
    analytics["total_issues"] = len(all_issues)
    analytics["completed_issues"] = len(found_issues)
    
    # Create a set of completed issue keys for O(1) lookup
    completed_keys = set(found_issues.keys())
    
    # Calculate story points
    for issue in all_issues:
        # Story points are typically in customfield_10016, but can vary
        story_points = getattr(issue.fields, 'customfield_10016', None)
        if story_points:
            analytics["total_story_points"] += float(story_points)
            # Check if this issue is completed
            if issue.key in completed_keys:
                analytics["completed_story_points"] += float(story_points)

    print("\nPulse Goal:\n{}\n\n".format(sprint_goal))
    return found_issues, analytics

def key_to_md(key):
    global jira_server
    markdown_link = "[{}]({})"

    return markdown_link.format(key, jira_server + "/browse/" + key)


def insert_bug_link(text):
    markdown_link = "[{}]({})"
    bugid = get_bug_id(text)
    bug= "LP#" + bugid
    link = "https://pad.lv/" + bugid

    return re.sub(bug, markdown_link.format(bug, link), text)


def print_jira_issue(issue):
    summary = issue["summary"]
    key = key_to_md(issue["key"])
    if "LP#" in summary:
        summary = insert_bug_link(summary)
        print("   - {}".format(summary))
    else:
        print("   - {} : {}".format(key, summary))


def print_jira_report(issues):
    if not issues:
        return

    epic = ""
    print("---\nCompleted Epics:\n")
    for issue in issues:
        if epic != issues[issue]["epic"] and issues[issue]["epic_status"] == 'Done':
            epic = issues[issue]["epic"]
            print(" - {}".format(issues[issue]["epic"]))
    
    epic = ""
    print("\n---\nCompleted Tasks:\n")
    for issue in issues:
        if epic != issues[issue]["epic"]:
            epic = issues[issue]["epic"]
            print(" - {} ".format(issues[issue]["epic"]))
        print_jira_issue(issues[issue])


def print_analytics(analytics):
    """Print sprint analytics showing completed vs total issues and story points"""
    if not analytics:
        return
    
    print("\n---\nSprint Analytics:\n")
    
    # Issues analytics
    completed = analytics["completed_issues"]
    total = analytics["total_issues"]
    if total > 0:
        percentage = (completed / total) * 100
        print(f" - Issues: {completed}/{total} completed ({percentage:.1f}%)")
    else:
        print(f" - Issues: {completed}/{total} completed")
    
    # Story points analytics
    completed_sp = analytics["completed_story_points"]
    total_sp = analytics["total_story_points"]
    if total_sp > 0:
        percentage_sp = (completed_sp / total_sp) * 100
        print(f" - Story Points: {completed_sp:.1f}/{total_sp:.1f} completed ({percentage_sp:.1f}%)")
    elif completed_sp > 0:
        print(f" - Story Points: {completed_sp:.1f} completed (total not available)")
    else:
        print(f" - Story Points: Not tracked or not available")
    print("")


def main(args=None):
    global jira_server
    global sprint
    parser = argparse.ArgumentParser(
        description=
            "A script to return a a Markdown report of a Jira Sprint"
    )

    parser.add_argument("project", type=str, help="key of the Jira project")
    parser.add_argument("sprint", type=str, help="name of the Jira sprint")
    parser.add_argument("--analytics-only", action="store_true",
                        help="print only sprint name and analytics (no detailed report)")

    opts = parser.parse_args(args)

    try:
        api = jira_api()
    except ValueError as e:
        print(f"ERROR: Cannot initialize Jira API: {e}", file=sys.stderr)
        sys.exit(1)

    jira_server = api.server

    jira = JIRA(api.server, basic_auth=(api.login, api.token))

    sprint = opts.sprint
    
    print("") # Insert blank line to avoid md format issue
    print(sprint) # Insert blank line to avoid md format issue
      
    # Create a set of all Jira issues completed in a given sprint
    issues, analytics = find_issue_in_jira_sprint(jira, opts.project, sprint)

    if opts.analytics_only:
        # Print only analytics (sprint name already printed above)
        print_analytics(analytics)
    else:
        # Print full report with analytics (default behavior)
        print_jira_report(issues)
        print_analytics(analytics)

# =============================================================================
