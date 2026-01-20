"""
OpenRouter Models Data
Hardcoded list of popular models available on OpenRouter.
Source: https://openrouter.ai/models (public data)
"""

# Popular OpenRouter models (subset for simplicity)
OPENROUTER_MODELS = [
    # OpenAI Models
    {"id": "openai/gpt-4-turbo", "name": "GPT-4 Turbo", "provider": "OpenAI"},
    {"id": "openai/gpt-4", "name": "GPT-4", "provider": "OpenAI"},
    {"id": "openai/gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "provider": "OpenAI"},
    {"id": "openai/gpt-4o", "name": "GPT-4o", "provider": "OpenAI"},
    {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "provider": "OpenAI"},
    
    # Anthropic Models
    {"id": "anthropic/claude-3-opus", "name": "Claude 3 Opus", "provider": "Anthropic"},
    {"id": "anthropic/claude-3-sonnet", "name": "Claude 3 Sonnet", "provider": "Anthropic"},
    {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku", "provider": "Anthropic"},
    {"id": "anthropic/claude-2", "name": "Claude 2", "provider": "Anthropic"},
    
    # Google Models
    {"id": "google/gemini-pro", "name": "Gemini Pro", "provider": "Google"},
    {"id": "google/gemini-pro-vision", "name": "Gemini Pro Vision", "provider": "Google"},
    {"id": "google/palm-2", "name": "PaLM 2", "provider": "Google"},
    
    # Meta Models
    {"id": "meta-llama/llama-3-70b", "name": "Llama 3 70B", "provider": "Meta"},
    {"id": "meta-llama/llama-3-8b", "name": "Llama 3 8B", "provider": "Meta"},
    {"id": "meta-llama/llama-2-70b", "name": "Llama 2 70B", "provider": "Meta"},
    
    # Mistral AI Models
    {"id": "mistralai/mistral-large", "name": "Mistral Large", "provider": "Mistral AI"},
    {"id": "mistralai/mistral-medium", "name": "Mistral Medium", "provider": "Mistral AI"},
    {"id": "mistralai/mistral-small", "name": "Mistral Small", "provider": "Mistral AI"},
    {"id": "mistralai/mixtral-8x7b", "name": "Mixtral 8x7B", "provider": "Mistral AI"},
    
    # Other Popular Models
    {"id": "cohere/command-r-plus", "name": "Command R+", "provider": "Cohere"},
    {"id": "cohere/command-r", "name": "Command R", "provider": "Cohere"},
    {"id": "perplexity/pplx-70b-online", "name": "Perplexity 70B Online", "provider": "Perplexity"},
    {"id": "microsoft/phi-3-medium", "name": "Phi-3 Medium", "provider": "Microsoft"},
    {"id": "databricks/dbrx", "name": "DBRX", "provider": "Databricks"},
]
