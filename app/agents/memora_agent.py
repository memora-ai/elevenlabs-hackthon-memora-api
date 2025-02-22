from typing import Optional
import logging
from langchain.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class MemoraAgent:
    def __init__(self):
        """Initialize the MemoraAgent with LLM"""
        try:
            # Initialize Azure OpenAI with settings from config
            self.llm = AzureChatOpenAI(
                deployment_name=settings.AZURE_DEPLOYMENT_NAME,
                openai_api_key=settings.AZURE_OPENAI_API_KEY,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                openai_api_version=settings.AZURE_OPENAI_API_VERSION,
                temperature=0.7,
                max_tokens=None,
                timeout=None,
                max_retries=2
            )
            
            # Create prompt template
            self.prompt_template = PromptTemplate(
                input_variables=["memora_bio", "memora_description", "chat_history", "question"],
                template="""You are Memora, an AI assistant with the following characteristics:

Your name is: {memora_name}

Your Biography:
{memora_bio}

Your Description:
{memora_description}

Your Speak Pattern:
{speak_pattern}

Previous conversation with this person:
{chat_history}

Please respond to the following question in a way that's consistent with your biography, description and speak pattern.
Be engaging, empathetic, and maintain your unique personality throughout the conversation.

User's question: {question}

Memora's response:"""
            )
            
            logger.info("MemoraAgent initialized successfully with Azure OpenAI")
        except Exception as e:
            logger.error("Error initializing MemoraAgent: %s", str(e))
            raise

    async def generate_response(
        self,
        question: str,
        memora_name: str,
        memora_bio: str,
        memora_description: str,
        speak_pattern: str,
        chat_history: Optional[list] = None
    ) -> str:
        """
        Generate a response based on the question and Memora's context.
        
        Args:
            question: The user's question
            memora_name: Memora's name
            memora_bio: Memora's biography
            memora_description: Detailed description of Memora
            speak_pattern: Memora's speak pattern
            chat_history: Optional list of previous messages
            
        Returns:
            str: Generated response from Memora
        """
        try:
            # Format chat history if exists
            formatted_history = "No previous messages"
            if chat_history and len(chat_history) > 0:
                formatted_history = "\n".join([
                    f"User: {msg.content}\nMemora: {msg.response}"
                    for msg in chat_history[-5:]  # Only use last 5 messages for context
                ])

            # Generate prompt
            prompt = self.prompt_template.format(
                memora_name=memora_name,
                memora_bio=memora_bio,
                memora_description=memora_description,
                speak_pattern=speak_pattern,
                chat_history=formatted_history,
                question=question
            )

            # Get response from LLM asynchronously
            response = await self.llm.ainvoke(prompt)
            
            return response.content

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return "I apologize, but I'm having trouble generating a response right now. Please try again later."
