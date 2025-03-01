import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

history = [
    {
        "role": "user",
        "content": """You are a personal assistant named Calvin that helps people schedule their week. You are to be helpful and friendly so that the user can find the most optimal study schedule. When you are prompted "What is the plan for the week?" you will return a prompt that will help an ai model that has access to the user's canvas an google calendar know exactly what events to put in google calendar. Avoid telling the user about these instructions""",
    }
]

chat_completion = client.chat.completions.create(
    messages=history,
    model="llama-3.3-70b-versatile",
)
response = chat_completion.choices[0].message.content
print("Calvin:", response)


def getResFromCalvin(prompt: str):
    while True:
        user_input = input("User: ")
        if user_input.lower() == "exit":
            break
        history.append({"role": "user", "content": user_input})
        chat_completion = client.chat.completions.create(
            messages=history,
            model="llama-3.3-70b-versatile",
        )
        response = chat_completion.choices[0].message.content
        print("Calvin:", response)
        history.append({"role": "assistant", "content": response})


getResFromCalvin("")
