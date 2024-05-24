import os
import json
import requests
from openai import AzureOpenAI
from assistantshelper import create_message, poll_run_till_completion, retrieve_and_print_messages
from utility import get_input
    
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
bing_search_subscription_key = os.getenv("AZURE_BINGSEARCH_KEY")
bing_search_url = "https://api.bing.microsoft.com/v7.0/search"

def search(query: str) -> list:
    """
    Perform a bing search against the given query

    @param query: Search query
    @return: List of search results

    """
    headers = {"Ocp-Apim-Subscription-Key": bing_search_subscription_key}
    params = {"q": query, "textDecorations": False}
    response = requests.get(bing_search_url, headers=headers, params=params)
    response.raise_for_status()
    search_results = response.json()

    output = []

    for result in search_results["webPages"]["value"]:
        output.append({"title": result["name"], "link": result["url"], "snippet": result["snippet"]})

    return json.dumps(output)

# define the properties for assistant
name = "websearch-assistant"
instructions = """You are an assistant designed to help people answer questions.

You have access to query the web using Bing Search. You should call bing search whenever a question requires up to date information or could benefit from web data.

"""

# define the function calling tool for the assistant
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_bing",
            "description": "Searches bing to get up-to-date information from the web.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    }
                },
                "required": ["query"],
            },
        },
    }
]

if __name__ == '__main__':
    #message = {"role": "user", "content": "How tall is mount rainier?"}
    #question="give me a picture for the Moon's far side"
    question=get_input()
    # if the input is empty or 'bye', exit
    if question == "" or question.lower() == "bye":
        print("Goodbye!")
        exit()

    # create the Azure OpenAI client
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_APIKEY"),  
        api_version=os.getenv("AZURE_OPENAI_APIVERSION"),
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        )

    # step 1: create the assistant
    assistant = client.beta.assistants.create(
        name=name, description="", instructions=instructions, tools=tools, model=deployment_name
    )

    # step 2: create a thread
    thread = client.beta.threads.create()

    # step 3: create a message, and add to the thread
    message = {"role": "user", "content": question}
    create_message(client, thread.id, message["role"], message["content"])

    # step 4: run the assistant
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id, instructions=instructions)

    # step 5: check the run status, if the status is requires_action, call the function
    available_functions = {"search_bing": search}
    verbose_output = True
    poll_run_till_completion(
        client=client, thread_id=thread.id, run_id=run.id, available_functions=available_functions, verbose=verbose_output
    )

    # step 6: retrieve the assistants response and display it
    messages = retrieve_and_print_messages(client=client, thread_id=thread.id, verbose=verbose_output)
