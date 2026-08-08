from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def read_index():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return {"message": "index.html not found"}
