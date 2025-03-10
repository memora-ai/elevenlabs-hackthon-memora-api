import json
import logging
import os

from langchain.agents.agent_types import AgentType
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_openai import AzureChatOpenAI
from langchain.prompts import PromptTemplate

import posthog
from posthog.ai.langchain import CallbackHandler

from app.core.config import settings

logger = logging.getLogger(__name__)

posthog.project_api_key = settings.POSTHOG_API_KEY
posthog.host = settings.POSTHOG_HOST

class UserAnalyzer:
    def __init__(self, db_path: str):
        """Initialize the UserAnalyzer with database connection and LLM"""
        try:
            self.db_path = db_path
            sqlite_path = f"sqlite:///{db_path}"
            # Initialize SQLite database connection
            logger.info(f"Initializing UserAnalyzer with db_path {sqlite_path}")
            
            # Add debug logging for database connection
            try:
                self.db = SQLDatabase.from_uri(sqlite_path)
                # Test the connection by getting tables
                tables = self.db.get_usable_table_names()
                logger.info(f"Successfully connected to database. Available tables: {tables}")
            except Exception as db_error:
                logger.error(f"Database connection error: {str(db_error)}")
                # Check file permissions
                logger.info(f"Database file exists: {os.path.exists(db_path)}")
                logger.info(f"Database file permissions: {oct(os.stat(db_path).st_mode)[-3:]}")
                raise

            # Initialize Azure OpenAI with settings from config
            self.llm = AzureChatOpenAI(
                deployment_name=settings.AZURE_DEPLOYMENT_NAME,
                openai_api_key=settings.AZURE_OPENAI_API_KEY,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                openai_api_version=settings.AZURE_OPENAI_API_VERSION,
                temperature=0.2,
                max_tokens=None,
                timeout=None,
                max_retries=2
            )
            
            # Create SQL toolkit and agent
            self.toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)
            self.agent = create_sql_agent(
                llm=self.llm,
                toolkit=self.toolkit,
                agent_type=AgentType.OPENAI_FUNCTIONS,
                verbose=False,
                handle_parsing_errors=True,
                top_k=10,
                max_iterations=15,
                max_execution_time=30,
                early_stopping_method="generate"
            )
            
            logger.info("UserAnalyzer initialized successfully with Azure OpenAI")
        except Exception as e:
            logger.error("Error initializing UserAnalyzer: %s", str(e))
            raise

    def analyze_user(self, language: str = 'en') -> dict:
        """
        Perform a comprehensive user analysis. 
        We then parse the returned string with json.loads to produce a dictionary.
        """
        # Prepare the single prompt
        prompt = PromptTemplate(
            input_variables=["language"],
            template="""
            You have access to a database with my Instagram data, including posts, stories, captions, profile info, and other metadata. 
            Using all relevant insights from that data, imagine you are me and produce a JSON object containing two fields:

            Imagine you are me, reflecting on who you are based on all the Instagram data in the database 
            (posts, stories, captions, profile info, inbox messages, media, comments, likes, followers, following, and any other relevant details). 

            **IMPORTANT**:
            - Dont make more than 6 SQL queries.
            - Return ONLY the JSON object, nothing else.

            Return ONLY a valid JSON compatible with python json.loads, with three fields:
            - "short_bio" [str]: 
                Write a concise first-person bio, focused on how I typically describe myself. 
                Emphasize my key personality traits, main interests, and unique qualities.

                Keep it under 500 characters, engaging, and personal. 
                Keep everything in one line. Dont skip lines. Be careful with things that can break the JSON format.
                The text MUST be in {language} language.
            
            - "detailed_profile" [str]: 
                Dive into the nuances of my personality, daily life, interests, social interactions, 
                and online presence. Aim for a fluent, narrative style that weaves these details 
                together seamlessly, as if I'm talking about myself. 

                Encourage depth and reflection: discuss my emotions, motivations, notable experiences, 
                and any unique traits or behaviors that define me. However, maintain a respectful tone 
                and avoid overly sensitive or confidential details.

                Dont use sentences like "my instagram...", the instagram is just the source of the data, 
                you are me and you are talking about yourself.

                Write at least a 3000 characters, engaging, and personal text.
                Keep everything in one line. Dont skip lines. Be careful with things that can break the JSON format.
                The text MUST be in {language} language.
            - "speak_pattern": [str]:
                From inbox tables, extract the pattern of how I speak.
                Make sure to get nuances of the language. Do I speak using slangs? Do I speak using emojis? Am I a formal person?
                Is my language very technical or not?
                Bring some examples of things that I say.

                Write at least a 1000 characters. This will be used to generate a voice for me, so details are very important.
                The pattern must be in {language} language.
                The pattern must be in one line. Dont skip lines. Be careful with things that can break the JSON format.
            """
        )

        chain = prompt | self.agent

        callback_handler = CallbackHandler(
            client=posthog,
            distinct_id=self.db_path,
            privacy_mode=False,
            groups={"agent": "user_analyzer_agent"}
        )

        # Execute the prompt
        response = chain.invoke({'language': language}, config={"callbacks": [callback_handler]})

        response_str = response['output']
        
        # Attempt to parse the response as JSON
        response_str = response_str.replace('```json', '').replace('```', '')

        start_index = response_str.find('{')
        if start_index != -1:
            response_str = response_str[start_index:]

        logger.info("Raw response from the agent: %s", response_str)

        return json.loads(response_str)
