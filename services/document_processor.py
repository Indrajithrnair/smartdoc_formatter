from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader
import os
from typing import Dict, List, Optional, Any
import logging
from functools import wraps
import time

from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from langchain.schema import SystemMessage, HumanMessage
from langchain.chains import LLMChain
from langchain_core.messages import AIMessage

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT, WD_LINE_SPACING
from docx.enum.style import WD_STYLE_TYPE

# Configure logging
logger = logging.getLogger(__name__)

def retry_on_rate_limit(max_retries=3, delay=2):
    """Decorator to handle Groq API rate limits with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if "rate limit" in str(e).lower():
                        wait_time = delay * (2 ** retries)
                        logger.warning(f"Rate limit hit, retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        retries += 1
                    else:
                        raise
            raise Exception("Max retries exceeded for rate limit")
        return wrapper
    return decorator

class DocumentTools:
    """Tools for document manipulation using python-docx."""
    
    @staticmethod
    def apply_heading(paragraph, level: int):
        """Apply heading style to paragraph."""
        paragraph.style = f'Heading {level}'
        
    @staticmethod
    def apply_font_style(run, **kwargs):
        """Apply font styling to a run."""
        if 'bold' in kwargs:
            run.bold = kwargs['bold']
        if 'italic' in kwargs:
            run.italic = kwargs['italic']
        if 'size' in kwargs:
            run.font.size = Pt(kwargs['size'])
        if 'color' in kwargs:
            rgb = kwargs['color']
            run.font.color.rgb = RGBColor(*rgb)
            
    @staticmethod
    def set_paragraph_alignment(paragraph, alignment: str):
        """Set paragraph alignment."""
        align_map = {
            'left': WD_PARAGRAPH_ALIGNMENT.LEFT,
            'center': WD_PARAGRAPH_ALIGNMENT.CENTER,
            'right': WD_PARAGRAPH_ALIGNMENT.RIGHT,
            'justify': WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        }
        paragraph.alignment = align_map.get(alignment.lower(), WD_PARAGRAPH_ALIGNMENT.LEFT)
        
    @staticmethod
    def set_line_spacing(paragraph, spacing: float):
        """Set line spacing for paragraph."""
        paragraph.paragraph_format.line_spacing = spacing

class DocumentAgent:
    """LangChain agent for document processing using Groq."""
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
            
        # Initialize primary and secondary LLMs
        self.primary_llm = self._init_llm("llama3-70b-8192", 0.1, 4096)
        self.secondary_llm = self._init_llm("llama3-8b-8192", 0.1, 2048)
        
        # Initialize tools
        self.tools = self._init_tools()
        
        # Initialize memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Initialize agent
        self.agent = self._init_agent()
        
    def _init_llm(self, model_name: str, temperature: float, max_tokens: int) -> ChatGroq:
        """Initialize a Groq LLM with specified parameters."""
        try:
            return ChatGroq(
                groq_api_key=self.api_key,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens
            )
        except Exception as e:
            logger.error(f"Error initializing Groq LLM: {str(e)}")
            raise

    def _init_tools(self) -> List[Tool]:
        """Initialize document manipulation tools."""
        return [
            Tool(
                name="apply_heading",
                func=DocumentTools.apply_heading,
                description="Apply heading style to a paragraph. Input: {paragraph, level (1-6)}"
            ),
            Tool(
                name="apply_font_style",
                func=DocumentTools.apply_font_style,
                description="Apply font styling (bold, italic, size, color) to text"
            ),
            Tool(
                name="set_alignment",
                func=DocumentTools.set_paragraph_alignment,
                description="Set paragraph alignment (left, center, right, justify)"
            ),
            Tool(
                name="set_line_spacing",
                func=DocumentTools.set_line_spacing,
                description="Set line spacing for paragraph"
            )
        ]

    def _init_agent(self) -> AgentExecutor:
        """Initialize the LangChain agent with tools and memory."""
        system_message = SystemMessage(content="""
        You are an expert document formatting assistant. Your task is to:
        1. Analyze document structure and content
        2. Understand formatting instructions
        3. Apply appropriate formatting using available tools
        4. Maintain document integrity
        5. Provide clear explanations of changes made
        
        Always validate inputs and handle errors gracefully.
        """)
        
        prompt = ChatPromptTemplate.from_messages([
            system_message,
            MessagesPlaceholder(variable_name="chat_history"),
            MessagesPlaceholder(variable_name="user_input"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_openai_tools_agent(
            llm=self.primary_llm,
            tools=self.tools,
            prompt=prompt
        )
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True
        )

    @retry_on_rate_limit()
    def analyze_document(self, doc: Document) -> Dict[str, Any]:
        """Analyze document structure and content."""
        try:
            # Extract document content for analysis
            content = []
            for para in doc.paragraphs:
                content.append(para.text)
            
            # Use secondary LLM for quick analysis
            analysis_chain = LLMChain(
                llm=self.secondary_llm,
                prompt=ChatPromptTemplate.from_messages([
                    SystemMessage(content="Analyze the document structure and provide insights."),
                    HumanMessage(content="\n".join(content))
                ])
            )
            
            analysis = analysis_chain.run(content)
            return {
                "status": "success",
                "analysis": analysis,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing document: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    @retry_on_rate_limit()
    def process_document(self, doc_path: str, instructions: Optional[str] = None) -> Dict[str, Any]:
        """Process document with given instructions using LangChain agent."""
        try:
            # Load document
            doc = Document(doc_path)
            
            # Analyze document first
            analysis = self.analyze_document(doc)
            if analysis["status"] == "error":
                return analysis
            
            if not instructions:
                return {
                    "status": "success",
                    "message": "Document analyzed successfully",
                    "analysis": analysis
                }
            
            # Process instructions with primary LLM
            result = self.agent.invoke({
                "input": f"""
                Document Analysis: {analysis['analysis']}
                
                Instructions: {instructions}
                
                Please process these instructions and apply appropriate formatting.
                """
            })
            
            # Save processed document
            output_path = doc_path.replace('.docx', '_processed.docx')
            doc.save(output_path)
            
            return {
                "status": "success",
                "message": "Document processed successfully",
                "agent_response": result['output'],
                "output_path": output_path,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def reset_memory(self):
        """Reset the agent's conversation memory."""
        self.memory.clear()

class DocumentProcessor:
    def __init__(self):
        """Initialize the document processor with Groq-powered agent."""
        try:
            self.agent = DocumentAgent()
        except Exception as e:
            logger.error(f"Failed to initialize DocumentAgent: {str(e)}")
            raise

    def process_document(self, file_path: str, instructions: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a document with optional formatting instructions.
        
        Args:
            file_path: Path to the document file
            instructions: Optional natural language instructions for formatting
            
        Returns:
            Dict containing processing status and results
        """
        try:
            # Process document using the agent
            result = self.agent.process_document(file_path, instructions)
            
            # Reset agent memory after processing
            self.agent.reset_memory()
            
            return result
            
        except Exception as e:
            logger.error(f"Error in document processing: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to process document: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            } 