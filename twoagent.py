import os
from autogen import AssistantAgent, UserProxyAgent

config_list = [
    {
        "model": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
        "api_key": os.getenv("AZURE_OPENAI_APIKEY"),
        "base_url": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "api_type": "azure",
        "api_version": os.getenv("AZURE_OPENAI_APIVERSION")
    }
]

assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})
user_proxy = UserProxyAgent(
    "user_proxy", code_execution_config={"work_dir": "coding", "use_docker": False}
)  # IMPORTANT: set to True to run code in docker, recommended

user_proxy.initiate_chat(assistant, message="Plot a chart of sin(x) curve.")
#user_proxy.initiate_chat(assistant, message="Plot a chart of MSFT stock price change YTD.")