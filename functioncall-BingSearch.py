import os
import json
import requests
from openai import AzureOpenAI
from utility import get_input

# client = OpenAI()
client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_APIKEY"),
        api_version=os.getenv("AZURE_OPENAI_APIVERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )

aoai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
bing_search_subscription_key = os.getenv("AZURE_BINGSEARCH_KEY")
bing_search_url = "https://api.bing.microsoft.com/v7.0/search"

#定义函数，实现对bing搜索的调用
# Define a function to call Bing search
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

#定义消息列表，第一个消息是系统消息
# Define a message list, the first message is a system message
messages = [{"role": "system", "content": "You are an AI assistant that helps people find information. If you don't know the answer, you can say 'I don't know'."}]

#通过AOAI和function calling tool调用bing搜索，对用户的问题生成回答
# Call Bing search through AOAI and function calling tool to generate answers to user questions
def generateAnswer(question) -> any:
    # Step 1: 定义模型可以使用的function tool
    # Define the function tools that the model can use
    available_functions = {"search_bing": search}
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

    # Step 2: 把用户问题加入到消息列表中，把消息列表和tools传递给模型，获取模型返回的tools调用信息，把tools调用信息加入到消息列表中
    # Add the user question to the message list, pass the message list and tools to the model, get the tools call information returned by the model, and add the tools call information to the message list
    message={"role": "user", "content": question}
    messages.append(message)
    response = client.chat.completions.create(
        model=aoai_deployment,
        messages=messages,
        tools=tools,
        tool_choice="auto",  # auto is default, but we'll be explicit
    )
    response_message = response.choices[0].message
    messages.append(response_message)

    # Step 3: 检查模型是否需要调用functions，如果需要，逐个调用functions，把functions的返回信息加入到消息列表中
    # Check if the model needs to call functions. If so, call the functions one by one and add the return information of the functions to the message list
    tool_calls = response_message.tool_calls
    second_response=None
    if tool_calls:
        # Note: the JSON response may not always be valid; be sure to handle errors
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_response = function_to_call(**json.loads(tool_call.function.arguments))
            #messages.append({"tool_call_id": tool_call.id, "output": function_response})
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )  # 把functions的返回信息加入到消息列表中，匹配tool_call_id和name


        # Step 4: 把消息列表传递给模型（包括系统提示，用户问题，模型的tools调用信息，各个function tool的调用结果），模型基于所有信息做内容生成
        # Pass the message list to the model (including system prompts, user questions, model tools call information, and the call results of each function tool), and the model generates content based on all information
        second_response = client.chat.completions.create(
            model=aoai_deployment,
            messages=messages,
        )  # get a new response from the model where it can see the function response
        messages.append(second_response.choices[0].message)
        
    return second_response

if __name__ == '__main__':
    print("-" * 80)
    #获取用户输入的问题
    # Get the user input question
    question=get_input()

    #循环响应用户的问题，直到用户输入“bye”，退出循环
    # Respond to the user's question in a loop until the user enters "bye" to exit the loop
    while question != "bye":
        response = generateAnswer(question)
        #if response is not None:
        if response is not None:
            print(response.choices[0].message.role, ": ", response.choices[0].message.content)
        else:
            print("I'm sorry, I did not find the answer by searching the web.")

        question=get_input()

    print("Goodbye!")
