import pytest
from unittest.mock import Mock, MagicMock, patch
from SprintReport.sprint_report import (
    find_issue_in_jira_sprint,
    print_analytics,
    get_bug_id,
    key_to_md,
    insert_bug_link,
    main,
)


@pytest.fixture
def mock_jira_api():
    """Create a mock JIRA API object"""
    mock_api = Mock()
    return mock_api


@pytest.fixture
def mock_issue():
    """Create a mock JIRA issue"""
    issue = Mock()
    issue.key = "TEST-123"
    issue.fields = Mock()
    issue.fields.summary = "Test summary"
    issue.fields.issuetype = Mock()
    issue.fields.issuetype.name = "Story"
    issue.fields.customfield_10020 = []
    issue.fields.customfield_10016 = 5.0  # Story points
    return issue


def test_get_bug_id():
    """Test bug ID extraction from summary"""
    assert get_bug_id("Fix LP#12345 issue") == "12345"
    assert get_bug_id("No bug here") == ""
    assert get_bug_id("LP#999 at start") == "999"


def test_key_to_md():
    """Test JIRA key to markdown conversion"""
    import SprintReport.sprint_report as sr
    sr.jira_server = "https://jira.example.com"
    result = key_to_md("TEST-123")
    assert result == "[TEST-123](https://jira.example.com/browse/TEST-123)"


def test_insert_bug_link():
    """Test Launchpad bug link insertion"""
    text = "Fix LP#12345 issue"
    result = insert_bug_link(text)
    assert "https://pad.lv/12345" in result
    assert "[LP#12345]" in result


def test_find_issue_in_jira_sprint_no_api(mock_jira_api):
    """Test find_issue_in_jira_sprint with no API"""
    issues, analytics = find_issue_in_jira_sprint(None, "TEST", "Sprint 1")
    assert issues == {}
    assert analytics == {}


def test_find_issue_in_jira_sprint_with_issues(mock_jira_api, mock_issue):
    """Test find_issue_in_jira_sprint with issues"""
    # Setup mock completed issue without parent (no epic)
    completed_issue = mock_issue
    completed_issue.fields.customfield_10020 = [Mock(name="Sprint 1", goal="Test goal")]
    # Remove parent attribute to avoid epic lookup
    if hasattr(completed_issue.fields, "parent"):
        delattr(completed_issue.fields, "parent")
    
    # Setup mock all issues (including the completed one)
    all_issue = Mock()
    all_issue.key = "TEST-124"
    all_issue.fields = Mock()
    all_issue.fields.customfield_10016 = 3.0  # Story points
    if hasattr(all_issue.fields, "parent"):
        delattr(all_issue.fields, "parent")
    
    mock_jira_api.search_issues = Mock(side_effect=[
        [completed_issue],  # First call for completed issues
        [completed_issue, all_issue]  # Second call for all issues
    ])
    
    issues, analytics = find_issue_in_jira_sprint(mock_jira_api, "TEST", "Sprint 1")
    
    assert len(issues) == 1
    assert "TEST-123" in issues
    assert analytics["total_issues"] == 2
    assert analytics["completed_issues"] == 1
    assert analytics["total_story_points"] == 8.0  # 5.0 + 3.0
    assert analytics["completed_story_points"] == 5.0


def test_print_analytics_complete_data(capsys):
    """Test print_analytics with complete data"""
    analytics = {
        "total_issues": 10,
        "completed_issues": 7,
        "total_story_points": 50.0,
        "completed_story_points": 35.0
    }
    
    print_analytics(analytics)
    captured = capsys.readouterr()
    
    assert "Sprint Analytics:" in captured.out
    assert "7/10 completed (70.0%)" in captured.out
    assert "35.0/50.0 completed (70.0%)" in captured.out


def test_print_analytics_no_story_points(capsys):
    """Test print_analytics with no story points"""
    analytics = {
        "total_issues": 5,
        "completed_issues": 3,
        "total_story_points": 0.0,
        "completed_story_points": 0.0
    }
    
    print_analytics(analytics)
    captured = capsys.readouterr()
    
    assert "Sprint Analytics:" in captured.out
    assert "3/5 completed (60.0%)" in captured.out
    assert "Not tracked or not available" in captured.out


def test_print_analytics_empty(capsys):
    """Test print_analytics with empty data"""
    print_analytics(None)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_print_analytics_zero_total(capsys):
    """Test print_analytics with zero total issues"""
    analytics = {
        "total_issues": 0,
        "completed_issues": 0,
        "total_story_points": 0.0,
        "completed_story_points": 0.0
    }
    
    print_analytics(analytics)
    captured = capsys.readouterr()
    
    assert "0/0 completed" in captured.out


@patch('SprintReport.sprint_report.jira_api')
@patch('SprintReport.sprint_report.JIRA')
def test_main_with_analytics_only_flag(mock_jira_class, mock_jira_api_class, capsys, mock_issue):
    """Test main function with --analytics-only flag"""
    # Setup mocks
    mock_api_instance = Mock()
    mock_api_instance.server = "https://jira.example.com"
    mock_api_instance.login = "test@example.com"
    mock_api_instance.token = "test-token"
    mock_jira_api_class.return_value = mock_api_instance
    
    mock_jira_instance = Mock()
    mock_jira_class.return_value = mock_jira_instance
    
    # Setup mock issue
    completed_issue = mock_issue
    completed_issue.fields.customfield_10020 = [Mock(name="Sprint 1", goal="Test goal")]
    if hasattr(completed_issue.fields, "parent"):
        delattr(completed_issue.fields, "parent")
    
    all_issue = Mock()
    all_issue.key = "TEST-124"
    all_issue.fields = Mock()
    all_issue.fields.customfield_10016 = 3.0
    if hasattr(all_issue.fields, "parent"):
        delattr(all_issue.fields, "parent")
    
    mock_jira_instance.search_issues = Mock(side_effect=[
        [completed_issue],  # First call for completed issues
        [completed_issue, all_issue]  # Second call for all issues
    ])
    
    # Call main with --analytics-only flag
    main(["TEST", "Sprint 1", "--analytics-only"])
    captured = capsys.readouterr()
    
    # Should contain sprint name and analytics
    assert "Sprint 1" in captured.out
    assert "Sprint Analytics:" in captured.out
    assert "Issues:" in captured.out
    
    # Should NOT contain detailed report sections
    assert "Completed Epics:" not in captured.out
    assert "Completed Tasks:" not in captured.out


@patch('SprintReport.sprint_report.jira_api')
@patch('SprintReport.sprint_report.JIRA')
def test_main_without_analytics_only_flag(mock_jira_class, mock_jira_api_class, capsys, mock_issue):
    """Test main function without --analytics-only flag (default behavior)"""
    # Setup mocks
    mock_api_instance = Mock()
    mock_api_instance.server = "https://jira.example.com"
    mock_api_instance.login = "test@example.com"
    mock_api_instance.token = "test-token"
    mock_jira_api_class.return_value = mock_api_instance
    
    mock_jira_instance = Mock()
    mock_jira_class.return_value = mock_jira_instance
    
    # Setup mock issue
    completed_issue = mock_issue
    completed_issue.fields.customfield_10020 = [Mock(name="Sprint 1", goal="Test goal")]
    if hasattr(completed_issue.fields, "parent"):
        delattr(completed_issue.fields, "parent")
    
    all_issue = Mock()
    all_issue.key = "TEST-124"
    all_issue.fields = Mock()
    all_issue.fields.customfield_10016 = 3.0
    if hasattr(all_issue.fields, "parent"):
        delattr(all_issue.fields, "parent")
    
    mock_jira_instance.search_issues = Mock(side_effect=[
        [completed_issue],  # First call for completed issues
        [completed_issue, all_issue]  # Second call for all issues
    ])
    
    # Call main without --analytics-only flag
    main(["TEST", "Sprint 1"])
    captured = capsys.readouterr()
    
    # Should contain sprint name, detailed report, and analytics
    assert "Sprint 1" in captured.out
    assert "Sprint Analytics:" in captured.out
    assert "Issues:" in captured.out
    
    # Should contain detailed report sections
    assert "Completed Epics:" in captured.out
    assert "Completed Tasks:" in captured.out

def test_print_analytics_zero_total(capsys):
    """Test print_analytics with zero total issues"""
    analytics = {
        "total_issues": 0,
        "completed_issues": 0,
        "total_story_points": 0.0,
        "completed_story_points": 0.0
    }
    
    print_analytics(analytics)
    captured = capsys.readouterr()
    
    assert "0/0 completed" in captured.out
