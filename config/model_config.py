from sfn_blueprint import MODEL_CONFIG

MODEL_CONFIG["clean_suggestions_generator"] = {
    "model": "gpt-4o-mini", #"gpt-3.5-turbo",
    "temperature": 0.5,
    "max_tokens": 500,
    "n": 1,
    "stop": None
}