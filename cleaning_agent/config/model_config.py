from sfn_blueprint import MODEL_CONFIG

DEFAULT_LLM_PROVIDER = 'openai' #'cortex'
DEFAULT_LLM_MODEL = 'gpt-4o-mini' # 'snowflake-arctic'

MODEL_CONFIG["clean_suggestions_generator"] = {
    "openai": {
        "model": DEFAULT_LLM_MODEL,
        "temperature": 0.5,
        "max_tokens": 500,
        "n": 1,
        "stop": None
    },
    "cortex": {
        "model": "snowflake-arctic",
        "temperature": 0.5,
        "max_tokens": 500,
        "n": 1,
        "stop": None
    },
    "anthropic": {
        "model": "claude-2",
        "temperature": 0.5,
        "max_tokens": 500,
        "n": 1,
        "stop": None
    }
}