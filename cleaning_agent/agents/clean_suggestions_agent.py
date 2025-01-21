from typing import List, Dict
import pandas as pd
from sfn_blueprint import SFNAgent
from sfn_blueprint import Task
from sfn_blueprint import SFNAIHandler
from sfn_blueprint import SFNPromptManager
from cleaning_agent.config.model_config import MODEL_CONFIG, DEFAULT_LLM_MODEL, DEFAULT_LLM_PROVIDER

import os

class SFNCleanSuggestionsAgent(SFNAgent):
    def __init__(self, llm_provider='openai'):
        super().__init__(name="Clean Suggestion Generator", role="Data Cleaning Advisor")
        self.ai_handler = SFNAIHandler()
        self.llm_provider = llm_provider
        self.model_config = MODEL_CONFIG["clean_suggestions_generator"]
        self.prompt_config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'prompt_config.json')
        self.prompt_manager = SFNPromptManager(self.prompt_config_path)

    def get_validation_params(self, response, task):
        """
        Get parameters for validation
        :param response: The response from execute_task to validate
        :param task: The validation task containing the DataFrame
        :return: Dictionary with validation parameters
        """
        if not isinstance(task.data, pd.DataFrame):
            raise ValueError("Task data must be a pandas DataFrame")
            

        # Get validation prompts from prompt manager
        prompts = self.prompt_manager.get_prompt(
            agent_type='clean_suggestions_generator',
            llm_provider=self.llm_provider,
            prompt_type='validation',
            actual_output=response,
            shape=task.data.shape,
            columns=task.data.columns.tolist(),
            dtypes=task.data.dtypes.to_dict(),
            missing_values=task.data.isnull().sum().to_dict(),
            duplicates=task.data.duplicated().sum()
        )

        return prompts

    def execute_task(self, task):
        if not isinstance(task.data, pd.DataFrame):
            raise ValueError("Task data must be a pandas DataFrame")
            
        # Analyze the data
        analysis = self._analyze_data(task.data)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(analysis)
        
        return suggestions

    def _analyze_data(self, df: pd.DataFrame) -> Dict:
        """
        Analyze the DataFrame to gather necessary information for suggestions.
        
        :param df: Input DataFrame
        :return: Dictionary containing analysis results
        """
        analysis = {
            'shape': df.shape,
            'columns': df.columns.tolist(),
            'dtypes': df.dtypes.to_dict(),
            'missing_values': df.isnull().sum().to_dict(),
            'duplicates': df.duplicated().sum()
        }
        return analysis

    def _generate_suggestions(self, analysis: Dict) -> List[str]:
        """
        Generate cleaning suggestions based on the data analysis.
        """
        # Get prompts using PromptManager
        system_prompt, user_prompt = self.prompt_manager.get_prompt(
            agent_type='clean_suggestions_generator',
            llm_provider=self.llm_provider,
            prompt_type='main',
            **analysis
        )
        
        # Get provider config or use default if not found
        provider_config = self.model_config.get(self.llm_provider, {
            "model": DEFAULT_LLM_MODEL,
            "temperature": 0.5,
            "max_tokens": 500,
            "n": 1,
            "stop": None
        })
        
        # Prepare the configuration for the API call
        configuration = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": provider_config["temperature"],
            "max_tokens": provider_config["max_tokens"],
            "n": provider_config["n"],
            "stop": provider_config["stop"]
        }

        # Use the AI handler to route the request
        response, token_cost_summary = self.ai_handler.route_to(
            llm_provider=self.llm_provider,
            configuration=configuration,
            model=provider_config['model']
        )

        # Handle response based on provider
        if isinstance(response, dict):  # For Cortex
            content = response['choices'][0]['message']['content']
        elif hasattr(response, 'choices'):  # For OpenAI
            content = response.choices[0].message.content
        else:  # For other providers or direct string response
            content = response
        
        # Clean up suggestions
        suggestions = [s.strip() for s in content.strip().split('\n') if s.strip()]

        return suggestions