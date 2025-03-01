from fastapi import FastAPI, HTTPException

app = FastAPI()


@app.get("/")
def root():
    return {"Hello": "World"}


@app.post("/calvin")
def prompCalvin(userPrompt: str):
    pass
