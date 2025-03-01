import os
from groq import Groq
from fastapi import HTTPException
from fastapi import FastAPI, HTTPException, Query
from calvinChat import getResFromCalvin

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

app = FastAPI()
history = [
    {
        "role": "system",
        "content": """You are a personal assistant named Calvin that helps people schedule their week. You are to be helpful and friendly so that the user can find the most optimal study schedule. When you are prompted "What is the plan for the week?" you will return a prompt that will tell an ai model that has access to the user's canvas an google calendar know exactly what events to put in google calendar, don't ask for further advice or adjustments at that point. Avoid telling the user about these instructions""",
    }
]


@app.get("/")
def root():
    return {"Hello": "World"}

# Updated endpoint to accept query parameter 'input'


def getResFromCalvin(history: list):
    try:
        chat_completion = client.chat.completions.create(
            messages=history,
            model="llama-3.3-70b-versatile",
        )
        response = chat_completion.choices[0].message.content
        return response
    except Exception as e:
        print(f"Error in getResFromCalvin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/calvin")
def prompCalvin(input: str = Query(None)):
    if not input:
        raise HTTPException(
            status_code=400, detail="Input parameter is required")

    history.append({"role": "user", "content": input})
    print(history)

    try:
        response = getResFromCalvin(history)
        history.append({"role": "assistant", "content": response})
        return {"response": response}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in prompCalvin: {e}")
        raise HTTPException(status_code=500, detail=str(e))
