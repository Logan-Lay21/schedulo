import os
from groq import Groq
from fastapi import HTTPException

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


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
