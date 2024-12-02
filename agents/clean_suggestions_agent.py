from typing import List, Dict
import pandas as pd
from sfn_blueprint import SFNAgent
from sfn_blueprint import Task
from sfn_blueprint import SFNAIHandler
from sfn_blueprint import SFNPromptManager
from config.model_config import MODEL_CONFIG, DEFAULT_LLM_MODEL, DEFAULT_LLM_PROVIDER

import os

class SFNCleanSuggestionsAgent(SFNAgent):
    def __init__(self ,llm_provider: str):
        super().__init__(name="Clean Suggestion Generator", role="Data Cleaning Advisor")
        self.ai_handler = SFNAIHandler()
        self.llm_provider = llm_provider
        self.model_config = MODEL_CONFIG["clean_suggestions_generator"]
        parent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
        prompt_config_path = os.path.join(parent_path, 'config', 'prompt_config.json')
        self.prompt_manager = SFNPromptManager(prompt_config_path)

    def execute_task(self, task: Task) -> List[str]:
        """
        Execute the cleaning suggestion generation task.
        
        :param task: Task object containing the DataFrame to be analyzed
        :return: List of cleaning suggestions
        """
        if not isinstance(task.data, pd.DataFrame):
            raise ValueError("Task data must be a pandas DataFrame")

        # Perform data analysis
        analysis = self._analyze_data(task.data)
        
        # Get suggestions using the analysis
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
        
        :param analysis: Dictionary containing data analysis results
        :return: List of cleaning suggestions
        """
        # Get prompts using PromptManager
        system_prompt, user_prompt = self.prompt_manager.get_prompt(
            agent_type='clean_suggestions_generator',
            llm_provider=DEFAULT_LLM_PROVIDER,
            **analysis
        )
        
        # Prepare the configuration for the API call
        configuration = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.model_config["temperature"],
            "max_tokens": self.model_config["max_tokens"],
            "n": self.model_config["n"],
            "stop": self.model_config["stop"]
        }

        # Use the AI handler to route the request
        response, token_cost_summary = self.ai_handler.route_to(
            llm_provider=DEFAULT_LLM_PROVIDER, 
            configuration=configuration, 
            model=self.model_config['model']
        )

        if self.llm_provider == 'cortex':
            suggestions = response['choices'][0]['messages'].strip().split('\n')
        else:
            suggestions = response.choices[0].message.content.strip().split('\n')
        
        # Clean up suggestions (remove empty strings and leading/trailing whitespace)
        suggestions = [s.strip() for s in suggestions if s.strip()]
        
        return suggestions