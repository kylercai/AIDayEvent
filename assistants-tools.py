import os
import io
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable
from openai import AzureOpenAI
from openai.types.beta import Thread
from openai.types.beta.threads import Run
from openai.types.beta.threads.messages import MessageFile
from openai.types.beta.threads.image_file_content_block import ImageFileContentBlock
from openai.types.beta.threads.text_content_block import TextContentBlock 
from openai.types import FileObject
import yfinance as yf
from PIL import Image
from utility import popup_show_image

# 定义函数，获取股票价格
# Get the stock price using the yfinance library
def get_stock_price(symbol: str) -> float:
    stock = yf.Ticker(symbol)
    price = stock.history(period="1d")["Close"].iloc[-1]
    #return price
    #convert the stock price from number to string
    print("Getting stock price for symbol: ", symbol, " Price: ", price)
    return str(price)

# 根据Azure OpenAI Assistant的输出，调用函数
# Call the function based on the output from Azure OpenAI Assistant
def call_functions(client: AzureOpenAI, thread: Thread, run: Run) -> None:
    print("Function Calling")
    required_actions = run.required_action.submit_tool_outputs.model_dump()
    #print(required_actions)
    tool_outputs = []
    import json

    for action in required_actions["tool_calls"]:
        func_name = action["function"]["name"]
        arguments = json.loads(action["function"]["arguments"])

        if func_name == "get_stock_price":
            output = get_stock_price(symbol=arguments["symbol"])
            tool_outputs.append({"tool_call_id": action["id"], "output": output})
        else:
            raise ValueError(f"Unknown function: {func_name}")

    print("Submitting outputs back to the Assistant...")
    client.beta.threads.runs.submit_tool_outputs(thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs)

# 格式化消息并显示
# Format and display messages
def format_messages(messages: Iterable[MessageFile]) -> None:
    message_list = []

    # Get all the messages till the last user message
    for message in messages:
        message_list.append(message)
        if message.role == "user":
            break

    # Reverse the messages to show the last user message first
    message_list.reverse()

    # Print the user or Assistant messages or images
    for message in message_list:
        for item in message.content:
            # Determine the content type

            if isinstance(item, TextContentBlock):
                # 显示文本内容
                # Display text content
                print(f"{message.role}:\n{item.text.value}\n")
            elif isinstance(item, ImageFileContentBlock):
                # 显示图像内容
                # Display image content
                print("Generating a chart...")
                # Retrieve image from file id
                response_content = client.files.content(item.image_file.file_id)
                data_in_bytes = response_content.read()
                # Convert bytes to image
                readable_buffer = io.BytesIO(data_in_bytes)
                image = Image.open(readable_buffer)
                # Resize image to fit in terminal
                width, height = image.size
                image = image.resize((width // 2, height // 2), Image.LANCZOS)
                # Display image
                # pop up a window to show the image
                #image.show()
                image.save("d:\\temp\\invest.PNG")

# 处理用户提出的问题
# Process the user's question
def process_message(content: str, client: AzureOpenAI, thread: Thread) -> None:
    print(f"User:\n{content}\n")
    # step 3: create a message, and add to the thread
    client.beta.threads.messages.create(thread_id=thread.id, role="user", content=content)

    # step 4: run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
        instructions="The current date and time is: " + datetime.now().strftime("%x %X") + ".",
    )

    # step 5: check the run status for processing
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run.status == "completed":
            # step 6: retrieve the assistants response and display it
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            format_messages(messages)
            break
        if run.status == "failed":
            # step 6: retrieve the assistants response and display it
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            format_messages(messages)
            # Handle failed
            break
        if run.status == "expired":
            # Handle expired
            break
        if run.status == "cancelled":
            # Handle cancelled
            break
        if run.status == "requires_action":
            # if the status is requires_action, call the function
            call_functions(client, thread, run)
        else:
            time.sleep(5)
    print("-" * 80)

# upload the file to the Azure OpenAI. if the file is already uploaded, return the file object
def upload_file(client: AzureOpenAI, path: str) -> FileObject:
    file_list=client.files.list(purpose="assistants")
    file=None
    for f in file_list:
        if f.filename == Path(path).name:
            print(path.split("/")[-1] + " already exists in the file list.")
            file = f
            break

    if file is None:
        with Path(path).open("rb") as f:
            file = client.files.create(file=f, purpose="assistants", extra_headers=None, extra_query=None, extra_body=None)
            
    return file

# get the assistant by name. if the assistant is not found, create a new assistant
def getAssistant(client: AzureOpenAI, assistant_name: str):
    assistants = client.beta.assistants.list()
    assistant=None
    for assistant in assistants:
        if assistant.name == assistant_name:
            return assistant
    # if the assistant is not found, create a new assistant
    if assistant is None:
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        assistant = client.beta.assistants.create(name=assistant_name, description="", instructions="", model=deployment_name)

    return assistant

# 定义tools列表，将tools列表添加到assistant中
# Define the tools list and add the tools list to the assistant
tools_list = [
    {"type": "code_interpreter"},
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "Retrieve the latest closing price of a stock using its ticker symbol.",
            "parameters": {
                "type": "object",
                "properties": {"symbol": {"type": "string", "description": "The ticker symbol of the stock"}},
                "required": ["symbol"],
            },
        },
    }
]

if __name__ == '__main__':
    # create the Azure OpenAI client
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_APIKEY"),  
        api_version=os.getenv("AZURE_OPENAI_APIVERSION"),
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        )

    # step 1: with the specified assistant name, create a new or retrieve an assistant if existed, 
    # and update the assistant with instructions/tools/file_ids
    assistant = getAssistant(client, "personal_finance")
    instructions="""You are a personal securities trading assistant. Please be polite, professional, helpful, and friendly. 
        Use the provided portfolio CSV file to answer the questions. If question is not related to the portfolio or you cannot answer the question, say, 'contact a representative for more assistance.' 
        If the user asks for help or says 'help', provide a list of sample questions that you can answer."""
    file_ids=[]
    file_ids.append(upload_file(client, "data/portfolio.csv").id)
    client.beta.assistants.update(assistant.id, instructions=instructions, tools=tools_list, file_ids=file_ids)

    # step 2: create a thread
    thread = client.beta.threads.create()

    process_message("Based on the provided CSV file, what investments do I own?", client, thread)
    process_message("What is the value of my portfolio? show in table for each stock I own and the total amount", client, thread)
    process_message("Chart the realized gain or loss of my investments.", client, thread)
    # process_message("根据我提供的CSV文件，我有投资哪些股票？数量和价格是多少？", client, thread)
    # process_message("查找股票的当前价格，计算每只股票的总价值，和我的投资总价值，用表格形式展示", client, thread)
    # process_message("用图表展示我的投资已经实现的收益和损失情况", client, thread)
    popup_show_image("d:\\temp\\invest.PNG")