"""
JIRA RAG Assistant - Builds context from parent ticket and children for acceptance criteria generation
"""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import CharacterTextSplitter
from jira import JIRA
import os
from dotenv import load_dotenv
import logging
import sys
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class JiraRAGAssistant:
    def __init__(self, persist_directory="./vector_store"):
        """Initialize the RAG assistant with vector store and embeddings"""
        self.embeddings = OpenAIEmbeddings()
        self.persist_directory = persist_directory
        self.vector_store = None
        self.text_splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=500,
            chunk_overlap=50,
            length_function=len
        )
        self.processed_tickets = set()
        
        # Initialize JIRA client
        jira_server = os.getenv("JIRA_SERVER")
        jira_email = os.getenv("JIRA_EMAIL")
        jira_api_token = os.getenv("JIRA_API_TOKEN")
        
        if not all([jira_server, jira_email, jira_api_token]):
            raise ValueError("JIRA_SERVER, JIRA_EMAIL and JIRA_API_TOKEN environment variables must be set")
            
        self.jira = JIRA(
            server=jira_server,
            basic_auth=(jira_email, jira_api_token)
        )
        
        # System message for the analyzer
        self.system_message = SystemMessage(content="""
        I am a JIRA ticket analyzer for the Embedded Systems team at u-blox.
        My purpose is to analyze tickets and propose precise acceptance criteria 
        based on our Definition of Done and historical context from related tickets.
        """)
        
        self.chat = ChatOpenAI(
            temperature=0.7,
            model="gpt-4-turbo-preview"
        )

    def fetch_all_related_tickets(self, parent_key: str) -> list:
        """Fetch parent ticket and all its child tickets"""
        try:
            # Get parent ticket
            parent_issue = self.jira.issue(parent_key)
            tickets = [parent_issue]
            
            # Find all subtasks and linked issues
            jql = f'parent = {parent_key} OR "Epic Link" = {parent_key}'
            children = self.jira.search_issues(jql)
            tickets.extend(children)
            
            logger.info(f"Found {len(tickets)} related tickets for {parent_key}")
            return tickets
            
        except Exception as e:
            logger.error(f"Error fetching related tickets: {e}")
            return []

    def extract_ticket_content(self, issue) -> dict:
        """Extract relevant content from a JIRA ticket"""
        try:
            content = {
                "key": issue.key,
                "summary": issue.fields.summary,
                "description": issue.fields.description or "",
                "type": issue.fields.issuetype.name,
                "acceptance_criteria": getattr(issue.fields, "customfield_10006", "") or ""  # Adjust field ID as needed
            }
            return content
        except Exception as e:
            logger.error(f"Error extracting content from {issue.key}: {e}")
            return None

    def build_knowledge_base(self, parent_key: str):
        """Build RAG knowledge base from parent ticket and children"""
        try:
            # Clear existing vector store
            self.vector_store = None
            self.processed_tickets.clear()
            
            # Fetch all related tickets
            tickets = self.fetch_all_related_tickets(parent_key)
            if not tickets:
                raise ValueError(f"No tickets found for parent {parent_key}")
                
            # Process each ticket
            texts = []
            metadatas = []
            
            for ticket in tickets:
                content = self.extract_ticket_content(ticket)
                if content:
                    # Add description
                    texts.append(content["description"])
                    metadatas.append({
                        "source": "description",
                        "ticket": content["key"]
                    })
                    
                    # Add acceptance criteria if available
                    if content["acceptance_criteria"]:
                        texts.append(content["acceptance_criteria"])
                        metadatas.append({
                            "source": "acceptance_criteria",
                            "ticket": content["key"]
                        })
                    
                    self.processed_tickets.add(content["key"])
            
            # Add definition of done
            dod = self.read_definition_of_done()
            if dod:
                texts.append(dod)
                metadatas.append({
                    "source": "definition_of_done",
                    "type": "reference"
                })
            
            # Create vector store
            self.create_or_update_vector_store(texts, metadatas)
            logger.info(f"Built knowledge base from {len(self.processed_tickets)} tickets")
            
        except Exception as e:
            logger.error(f"Error building knowledge base: {e}")
            raise

    def read_definition_of_done(self):
        """Read the Definition of Done file"""
        try:
            with open("definition_of_done.txt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading Definition of Done: {e}")
            return None

    def create_or_update_vector_store(self, texts, metadatas=None):
        """Create or update the vector store with new texts"""
        try:
            # Split texts into chunks
            all_chunks = []
            all_metadatas = []
            
            for i, text in enumerate(texts):
                chunks = self.text_splitter.split_text(text)
                all_chunks.extend(chunks)
                
                if metadatas:
                    chunk_metadata = metadatas[i]
                    all_metadatas.extend([chunk_metadata] * len(chunks))
                    
            if self.vector_store is None:
                self.vector_store = Chroma.from_texts(
                    texts=all_chunks,
                    embedding=self.embeddings,
                    metadatas=all_metadatas,
                    persist_directory=self.persist_directory
                )
            else:
                self.vector_store.add_texts(
                    texts=all_chunks,
                    metadatas=all_metadatas
                )
                
            self.vector_store.persist()
            self._save_processed_tickets()
            
        except Exception as e:
            logger.error(f"Error updating vector store: {e}")

    def _save_processed_tickets(self):
        """Save the list of processed JIRA tickets to a file"""
        try:
            with open('jira_rag_pages.txt', 'w') as f:
                sorted_tickets = sorted(list(self.processed_tickets))
                f.write("JIRA Tickets in Vector Store:\n")
                f.write("=========================\n")
                for ticket in sorted_tickets:
                    f.write(f"{ticket}\n")
                f.write(f"\nTotal Tickets: {len(sorted_tickets)}")
                
            logger.info(f"Saved {len(self.processed_tickets)} processed tickets to jira_rag_pages.txt")
        except Exception as e:
            logger.error(f"Error saving processed tickets: {e}")

    def get_relevant_context(self, query: str, k: int = 3) -> list:
        """Retrieve relevant context from vector store"""
        if self.vector_store is None:
            return []
            
        try:
            return self.vector_store.similarity_search(query, k=k)
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return []

    def analyze_ticket(self, issue_key: str) -> str:
        """Analyze a JIRA ticket and suggest acceptance criteria"""
        try:
            # Fetch ticket to analyze
            issue = self.jira.issue(issue_key)
            content = self.extract_ticket_content(issue)
            
            if not content:
                return "Error: Could not fetch JIRA issue"
                
            # Get relevant context
            query = f"Based on the ticket '{content['summary']}', what should be the acceptance criteria?"
            relevant_contexts = self.get_relevant_context(query)
            context_text = "\n".join([doc.page_content for doc in relevant_contexts])
            
            # First classify the ticket
            classification_prompt = ChatPromptTemplate.from_messages([
                self.system_message,
                HumanMessagePromptTemplate.from_template(
                    """Based on the ticket information, classify this ticket into one of these categories:
                    - General feature development
                    - Release (ROM/FW)
                    - Bug Fix
                    - Verification and Bring-up
                    - Tool Update
                    - Investigation/Concept Work
                    - RMA

Ticket Information:
- Summary: {summary}
- Description: {description}
- Type: {ticket_type}

Provide ONLY the category name, nothing else."""
                )
            ])
            
            classification_response = self.chat.invoke(
                classification_prompt.format(
                    summary=content["summary"],
                    description=content["description"],
                    ticket_type=content["type"]
                )
            )
            ticket_category = classification_response.content.strip()
            
            # Generate acceptance criteria
            prompt = ChatPromptTemplate.from_messages([
                self.system_message,
                HumanMessagePromptTemplate.from_template(
                    """Based on the following information, provide up to 4 specific acceptance criteria for this ticket.

Ticket Classification: {ticket_category}

Ticket Information:
- Key: {ticket_key}
- Type: {ticket_type}
- Summary: {summary}
- Description: {description}

Related Context:
{context}

Format your response as follows:

Ticket Type: {ticket_category}

Acceptance Criteria (max 4):
1. [First criterion]
   - Verification: [How to verify this criterion]

2. [Second criterion]
   - Verification: [How to verify this criterion]

[etc., up to 4 criteria]"""
                )
            ])
            
            response = self.chat.invoke(
                prompt.format(
                    ticket_category=ticket_category,
                    ticket_key=content["key"],
                    ticket_type=content["type"],
                    summary=content["summary"],
                    description=content["description"],
                    context=context_text
                )
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error analyzing ticket: {e}")
            return f"Error analyzing ticket: {str(e)}"

def main():
    """Main function to run the JIRA RAG assistant"""
    if len(sys.argv) < 3:
        print("Usage: python jira_rag.py <parent_ticket> <ticket_to_analyze>")
        print("Example: python jira_rag.py ES-2700 ES-2754")
        sys.exit(1)
        
    try:
        # Initialize the assistant
        assistant = JiraRAGAssistant()
        
        # Get ticket numbers from command line
        parent_ticket = sys.argv[1]
        analyze_ticket = sys.argv[2]
        
        if not parent_ticket.startswith("ES-"):
            parent_ticket = f"ES-{parent_ticket}"
        if not analyze_ticket.startswith("ES-"):
            analyze_ticket = f"ES-{analyze_ticket}"
            
        # Build knowledge base from parent ticket
        logger.info(f"Building knowledge base from {parent_ticket} and its children...")
        assistant.build_knowledge_base(parent_ticket)
        
        # Analyze the specified ticket
        logger.info(f"Analyzing ticket {analyze_ticket}")
        result = assistant.analyze_ticket(analyze_ticket)
        
        # Print results
        print("\n" + "="*50)
        print(f"Analysis for {analyze_ticket}")
        print("="*50)
        print(result)
        print("\n" + "="*50)
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()