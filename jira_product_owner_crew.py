from crewai import Agent, Task, Crew
from utils import get_jira_tools, get_analysis_prompt, read_project_context, logger
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get project context
context = read_project_context()

# Create tools as dictionaries
jira_tools = get_jira_tools()

# 1️⃣ Epic & User Story Analyzer Agent
analyzer = Agent(
    role="Epic & User Story Analyzer",
    goal="Analyze JIRA user stories and epics to extract key acceptance criteria.",
    backstory=f"""You are a product owner assistant skilled in breaking down epics and user stories from JIRA.
    Project Context:
    {context.get('background', '')}
    
    Private Context:
    {context.get('private_context', '')}
    
    Definition of Done:
    {context.get('dod', '')}""",
    tools=jira_tools,
    allow_delegation=False,
    verbose=True
)

# 2️⃣ Acceptance Criteria Enhancer Agent
enhancer = Agent(
    role="Acceptance Criteria Enhancer",
    goal="Refine and enhance the acceptance criteria based on best practices.",
    backstory="You are an experienced Scrum Master and Agile expert who ensures clear and effective user stories.",
    tools=jira_tools,
    allow_delegation=False,
    verbose=True
)

# 3️⃣ DoD Validator Agent
validator = Agent(
    role="DoD Validator",
    goal="Ensure the acceptance criteria comply with the Definition of Done and update JIRA accordingly.",
    backstory="You are a quality assurance specialist ensuring all stories meet company-wide standards.",
    tools=jira_tools,
    allow_delegation=False,
    verbose=True
)

def analyze_ticket(issue_key: str) -> str:
    """Analyze a JIRA ticket using CrewAI"""
    try:
        # Define Tasks for Agents with the specific issue key
        analyze_task = Task(
            description=get_analysis_prompt(issue_key),
            agent=analyzer
        )

        refine_task = Task(
            description=f"""
            1. Review the initial analysis and acceptance criteria for {issue_key}
            2. Enhance the acceptance criteria with best practices
            3. Ensure each criterion is clear, measurable, and testable
            """,
            agent=enhancer
        )

        validate_task = Task(
            description=f"""
            1. Review the refined acceptance criteria for {issue_key}
            2. Validate against the Definition of Done
            3. Update the JIRA ticket with the final acceptance criteria
            """,
            agent=validator
        )

        # Create Crew
        crew = Crew(
            agents=[analyzer, enhancer, validator],
            tasks=[analyze_task, refine_task, validate_task],
            verbose=2
        )

        result = crew.kickoff()
        return result
    except Exception as e:
        error_msg = f"Error analyzing ticket: {str(e)}"
        logger.error(error_msg)
        return error_msg

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Please provide a JIRA ticket key as argument")
        sys.exit(1)
        
    # Format the ticket number with 'ES-' prefix
    issue_key = f"ES-{sys.argv[1]}"
    result = analyze_ticket(issue_key)
    print("\nAnalysis Result:", result)