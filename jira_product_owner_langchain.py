from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.agents import AgentType, initialize_agent
from langchain.tools import Tool
from langchain.memory import ConversationBufferMemory
from jira import JIRA
import os
from dotenv import load_dotenv
import logging
import sys


# pip install openai
# pip install langchain-openai
# pip install python-dotenv
# pip install jira
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# System message for the analyzer
system_message = SystemMessage(content="""I am a JIRA ticket analyzer for the Embedded Systems team at u-blox.
My purpose is to analyze tickets and propose precise acceptance criteria. Give me as much context as possible.
""")

def read_project_context(public_file_path: str = "README.md", private_file_path: str = "non-public.md") -> dict:
    """Read project context from both README.md and non-public.md"""
    try:
        # Read public content
        public_readme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), public_file_path)
        if not os.path.exists(public_readme_path):
            return {"error": f"{public_file_path} not found"}
            
        with open(public_readme_path, 'r') as f:
            public_content = f.read()
            
        # First try to find Background in public content
        background = "No background information available"
        background_start = public_content.find("## Background")
        if background_start != -1:
            next_section = public_content.find("##", background_start + 2)
            if next_section == -1:
                background = public_content[background_start:]
            else:
                background = public_content[background_start:next_section].strip()
            
        # Extract DoD section from public content
        dod_start = public_content.find("## Definition of Done (DoD)")
        if dod_start == -1:
            return {"error": "DoD section not found in README.md"}
            
        next_section = public_content.find("##", dod_start + 2)
        if next_section == -1:
            dod_content = public_content[dod_start:]
        else:
            dod_content = public_content[dod_start:next_section]
            
        # Try to read private content if available
        private_content = ""
        try:
            private_readme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), private_file_path)
            if os.path.exists(private_readme_path):
                with open(private_readme_path, 'r') as file:
                    private_content = file.read()
                    
                    # Try to find Background in private content if not found in public
                    if background == "No background information available":
                        background_start = private_content.find("## Background")
                        if background_start != -1:
                            next_section = private_content.find("##", background_start + 2)
                            if next_section == -1:
                                background = private_content[background_start:]
                            else:
                                background = private_content[background_start:next_section].strip()
        except Exception as e:
            logger.warning(f"Could not read private context file {private_file_path}: {str(e)}")
        
        return {
            "background": background,
            "dod": dod_content.strip(),
            "private_context": private_content
        }
        
    except Exception as e:
        logger.error(f"Error reading context files: {str(e)}")
        return {"error": f"Error reading context files: {str(e)}"}

def read_definition_of_done(public_file_path: str = "README.md") -> str:
    """Read the Definition of Done guidelines from README.md"""
    try:
        public_readme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), public_file_path)
        if not os.path.exists(public_readme_path):
            return "Error: README.md not found"
            
        with open(public_readme_path, 'r') as f:
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

# Create tools
tools = [
    Tool(
        name="JIRA Issue Reader",
        func=fetch_jira_issue,
        description="Fetch and read JIRA issue details. Input should be a JIRA issue key (e.g., 'ES-1281')."
    ),
    Tool(
        name="Definition of Done Reader",
        func=read_definition_of_done,
        description="Read the Definition of Done guidelines. Just provide an empty string as input."
    ),
    Tool(
        name="JIRA Issue Updater",
        func=update_jira_issue,
        description="Add a comment to a JIRA issue. Input should be in format: 'ISSUE-KEY|COMMENT'"
    )
]

# Initialize the LLM
chat = ChatOpenAI(
    model_name="gpt-4",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

# Create a memory to store conversation history
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

# Create the agent
agent = initialize_agent(
    tools=tools,
    llm=chat,
    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
    verbose=False,
    memory=memory,
    max_iterations=5
)

def analyze_ticket(issue_key: str) -> None:
    """Analyze a JIRA ticket and provide recommendations"""
    # First, verify the README.md file exists and get project context
    context = read_project_context()
    if "error" in context:
        logger.error("Could not read project context from README.md")
        print(f"\nError: {context['error']}")
        return

    # Extract only the relevant sections from background
    background = context['background']
    # Keep only the first paragraph and target environments
    background_lines = background.split('\n')
    relevant_background = '\n'.join([
        line for line in background_lines[:10]  # Only first 10 lines
        if ('repository' in line.lower() or 
            'target' in line.lower() or 
            any(chip in line for chip in ['JU', 'EI', 'EIP', 'MO', 'SA', 'GE']))
    ])

    # Fetch JIRA ticket details
    ticket_details = fetch_jira_issue(issue_key)
    
    # Extract only essential parts of DoD
    dod_lines = context['dod'].split('\n')
    essential_dod = '\n'.join([
        line for line in dod_lines 
        if line.strip() and not line.startswith('#') and not line.startswith('>')
    ][:15])  # Only first 15 non-empty, non-header lines

    # Only include first 1000 characters of private context if it's too long
    private_context = context['private_context'][:1000] if len(context['private_context']) > 1000 else context['private_context']

    prompt = f"""Analyze JIRA ticket {issue_key}:

Ticket Information:
{ticket_details}

Key Project Context:
{relevant_background}

Private Project Context:
{private_context}

Definition of Done Guidelines:
{essential_dod}

Provide analysis in this format:

**Ticket Type:**
[Select one: General feature development, Release (ROM/FW), Bug Fix, Verification and Bring-up, Tool Update, RMA, or Investigation/Concept Work]

**DoD Analysis:**
[Analysis focusing on specific chip type]

**Proposed Acceptance Criteria:**
[Based on the ticket type's DoD section, create specific, measurable criteria]
1. [DoD Item Being Addressed] 
   - Testing method: [How to verify this criterion]
   - Done when: [Specific, measurable completion state]

2. [Next DoD Item]
   - Testing method: [How to verify this criterion]
   - Done when: [Specific, measurable completion state]

**Missing Information:**
[List critical missing details needed to meet the DoD requirements]"""

    try:
        logger.info(f"Analyzing ticket {issue_key}")
        response = agent.invoke({
            "input": prompt,
            "chat_history": []
        })
        logger.debug(f"Raw response: {response}")
        
        print(f"\n{'=' * 50}")
        print(f"Analysis of {issue_key}")
        print(f"{'=' * 50}")
        
        if not response or not response.get("output"):
            print("Error: Failed to get analysis output.")
            return
            
        # Handle both string and dictionary responses
        output = response["output"]
        if isinstance(output, dict):
            # Convert dictionary to formatted string
            formatted_output = []
            for section in ["Ticket Type", "DoD Analysis", "Proposed Acceptance Criteria", "Missing Information"]:
                if section in output:
                    formatted_output.append(f"**{section}:**")
                    formatted_output.append(str(output[section]))
            output = "\n".join(formatted_output)
        
        # Clean up the output by removing any duplicate sections
        output_lines = output.strip().split('\n')
        seen_sections = set()
        cleaned_output = []
        current_section = None
        
        for line in output_lines:
            line = line.strip()
            if not line:  # Skip empty lines
                continue
                
            if line.startswith('**') and line.endswith('**'):
                current_section = line
                if current_section not in seen_sections:
                    seen_sections.add(current_section)
                    cleaned_output.append(line)
            else:
                cleaned_output.append(line)
        
        if not cleaned_output:
            print("Error: No valid analysis sections found.")
            return
            
        print('\n'.join(cleaned_output))
        print(f"\n{'=' * 50}")
        
    except Exception as e:
        logger.error(f"Error analyzing ticket: {str(e)}")
        print(f"\nError analyzing ticket {issue_key}: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Please provide at least one ticket number.")
        print("Usage: python main.py <ticket_number> [<ticket_number> ...]")
        print("Example: python main.py 1281 1425")
        sys.exit(1)
    
    # Process each ticket number
    for ticket_num in sys.argv[1:]:
        try:
            # Format the ticket number with 'ES-' prefix
            ticket_id = f"ES-{ticket_num}"
            logger.debug(f"Processing ticket number: {ticket_num}")
            analyze_ticket(ticket_id)
        except Exception as e:
            logger.error(f"Failed to process ticket {ticket_num}: {str(e)}")
            continue
