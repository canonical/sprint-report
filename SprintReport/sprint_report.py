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
        return {}

    # Get JIRA issues in batch of 50
    issue_index = 0
    issue_batch = 50

    found_issues = {}

    while True:
        start_index = issue_index * issue_batch
        request = "project = {} " \
            "AND cf[10020] = \"{}\" " \
            "AND status = Done ORDER BY type".format(project, sprint)
        issues = jira_api.search_issues(request, startAt=start_index)

        if not issues:
            break

        issue_index += 1

        # For each issue in JIRA with LP# in the title
        for issue in issues:
            summary = issue.fields.summary
            issue_type = issue.fields.issuetype.name
            found_issues[issue.key]= {
                "key":issue.key,
                "type":issue_type,
                "summary":summary}

    return found_issues


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
        print(" - {}".format(summary))
    else:
        print(" - {} : {}".format(key, summary))


def print_jira_report(issues):
    if not issues:
        return

    global sprint
    category = ""
    print("# {} report".format(sprint))
    for issue in issues:
        if issues[issue]["type"] != category:
            category = issues[issue]["type"]
            print("\n## {}".format(category))
        print_jira_issue(issues[issue])


def main(args=None):
    global jira_server
    global sprint
    parser = argparse.ArgumentParser(
        description=
            "A script to return a a Markdown report of a Jira Sprint"
    )

    parser.add_argument("project", type=str, help="key of the Jira project")
    parser.add_argument("sprint", type=str, help="name of the Jira sprint")

    opts = parser.parse_args(args)

    try:
        api = jira_api()
    except ValueError as e:
        print(f"ERROR: Cannot initialize Jira API: {e}", file=sys.stderr)
        sys.exit(1)

    jira_server = api.server

    jira = JIRA(api.server, basic_auth=(api.login, api.token))

    sprint = opts.sprint
    # Create a set of all Jira issues completed in a given sprint
    issues = find_issue_in_jira_sprint(jira, opts.project, sprint)
    print("Found {} issue{} in JIRA".format(
        len(issues),"s" if len(issues)> 1 else "")
    )

    print_jira_report(issues)

# =============================================================================
