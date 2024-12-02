from sfn_blueprint import MODEL_CONFIG

DEFAULT_LLM_PROVIDER= 'cortex' #'openai'
DEFAULT_LLM_MODEL='snowflake-arctic' # 'gpt-4o-mini'

MODEL_CONFIG["clean_suggestions_generator"] = {
    "model": DEFAULT_LLM_MODEL, #"gpt-3.5-turbo",
    "temperature": 0.5,
    "max_tokens": 500,
    "n": 1,
    "stop": None
}