from jira import JIRA
import os
from dotenv import load_dotenv
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def read_project_context() -> dict:
    """Read project context from README.md including Background and DoD"""
    try:
        readme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md")
        if not os.path.exists(readme_path):
            return {"error": "README.md not found"}
            
        with open(readme_path, 'r') as f:
            content = f.read()
            
        # Extract Background section
        background_start = content.find("## Background")
        if background_start == -1:
            background = "No background information available"
        else:
            next_section = content.find("##", background_start + 2)
            background = content[background_start:next_section].strip()
            
        # Extract DoD section
        dod_start = content.find("## Definition of Done (DoD)")
        if dod_start == -1:
            return {"error": "DoD section not found in README.md"}
            
        next_section = content.find("## Common Acronyms", dod_start)
        if next_section == -1:
            dod_content = content[dod_start:]
        else:
            dod_content = content[dod_start:next_section]
            
        return {
            "background": background,
            "dod": dod_content.strip()
        }
        
    except Exception as e:
        logger.error(f"Error reading README.md: {str(e)}")
        return {"error": f"Error reading README.md: {str(e)}"}

def read_definition_of_done(file_path: str = "") -> str:
    """Read the Definition of Done guidelines from README.md"""
    try:
        readme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md")
        if not os.path.exists(readme_path):
            return "Error: README.md not found"
            
        with open(readme_path, 'r') as f:
            content = f.read()
            
        # Extract DoD section using markdown headers
        dod_start = content.find("## Definition of Done (DoD)")
        if dod_start == -1:
            return "Error: DoD section not found in README.md"
            
        # Find the next ## header after DoD section
        next_section = content.find("## Common Acronyms", dod_start)
        if next_section == -1:
            dod_content = content[dod_start:]
        else:
            dod_content = content[dod_start:next_section]
            
        return dod_content.strip()
        
    except Exception as e:
        logger.error(f"Error reading README.md: {str(e)}")
        return f"Error reading README.md: {str(e)}"

def fetch_jira_issue(issue_key: str) -> str:
    """Fetch details of a JIRA issue including linked tickets"""
    try:
        jira_server = os.getenv('JIRA_SERVER')
        jira_email = os.getenv('JIRA_EMAIL')
        jira_token = os.getenv('JIRA_API_TOKEN')
        
        logger.debug(f"Connecting to JIRA server: {jira_server}")
        logger.debug(f"Using email: {jira_email}")
        
        # Remove any quotes from the issue key
        issue_key = issue_key.strip("'")
        
        jira = JIRA(
            server=jira_server,
            basic_auth=(jira_email, jira_token)
        )
        
        logger.info(f"Fetching JIRA ticket: {issue_key}")
        issue = jira.issue(issue_key)
        
        # Get linked issues
        linked_issues = []
        if hasattr(issue.fields, 'issuelinks'):
            for link in issue.fields.issuelinks:
                if hasattr(link, 'outwardIssue'):
                    linked_issues.append(f"{link.type.outward}: {link.outwardIssue.key}")
                if hasattr(link, 'inwardIssue'):
                    linked_issues.append(f"{link.type.inward}: {link.inwardIssue.key}")
        
        linked_issues_str = "\n        ".join(linked_issues) if linked_issues else "None"
        
        # Get parent (Epic) information
        parent_info = "None"
        if hasattr(issue.fields, 'parent'):
            parent = issue.fields.parent
            parent_info = f"{parent.key} - {parent.fields.summary}"
        
        return f"""
        Issue Key: {issue.key}
        Summary: {issue.fields.summary}
        Description: {issue.fields.description}
        Status: {issue.fields.status.name}
        Type: {issue.fields.issuetype.name}
        Parent Epic: {parent_info}
        Linked Issues: 
        {linked_issues_str}
        """
    except Exception as e:
        error_msg = f"Error fetching JIRA issue: {str(e)}"
        logger.error(error_msg)
        return error_msg

def update_jira_issue(issue_key_and_comment: str) -> str:
    """Add a comment to a JIRA issue"""
    try:
        issue_key, comment = issue_key_and_comment.split('|', 1)
    except ValueError:
        return "Error: Input should be in format 'ISSUE-KEY|COMMENT'"
    
    try:
        jira_server = os.getenv('JIRA_SERVER')
        jira_email = os.getenv('JIRA_EMAIL')
        jira_token = os.getenv('JIRA_API_TOKEN')
        
        jira = JIRA(
            server=jira_server,
            basic_auth=(jira_email, jira_token)
        )
        
        issue = jira.issue(issue_key)
        jira.add_comment(issue, comment)
        return f"Added comment to {issue_key}"
    except Exception as e:
        error_msg = f"Error updating JIRA issue: {str(e)}"
        logger.error(error_msg)
        return error_msg

def get_jira_tools():
    """Get the standard set of JIRA tools"""
    return [
        {
            "name": "JIRA Issue Reader",
            "func": fetch_jira_issue,
            "description": "Fetch and read JIRA issue details. Input should be a JIRA issue key (e.g., 'ES-1281')."
        },
        {
            "name": "Definition of Done Reader",
            "func": read_definition_of_done,
            "description": "Read the Definition of Done guidelines. No input required."
        },
        {
            "name": "JIRA Issue Updater",
            "func": update_jira_issue,
            "description": "Add a comment to a JIRA issue. Input should be in format: 'ISSUE-KEY|COMMENT'"
        }
    ]

def get_analysis_prompt(issue_key: str) -> str:
    """Get the standard analysis prompt"""
    context = read_project_context()
    if "error" in context:
        logger.error(f"Error reading project context: {context['error']}")
        return f"Error: {context['error']}"
    
    return f"""
    Background Information:
    {context['background']}
    
    Definition of Done:
    {context['dod']}
    
    Please analyze JIRA ticket {issue_key} and provide:
    1. A summary of the ticket
    2. Proposed acceptance criteria that align with our DoD
    3. Any potential dependencies or risks
    """

def shared_utilities():
    pass

shared_utilities()