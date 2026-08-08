from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
from typing import Optional

app = FastAPI()

# CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Local Testing & Development-ന് വേണ്ടി
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

def init_db():
    conn = sqlite3.connect("dating_app.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            location TEXT NOT NULL,
            bio TEXT,
            photo_url TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id INTEGER,
            to_user_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

class UserCreate(BaseModel):
    name: str
    age: int
    location: str
    bio: str
    photo_url: Optional[str] = None

class LikeRequest(BaseModel):
    from_user_id: int
    to_user_id: int

@app.get("/")
def home():
    return {"message": "Kinnaram API is Running!"}

@app.get("/app")
def serve_app():
    return FileResponse("index.html")

@app.get("/profiles")
def get_profiles():
    conn = sqlite3.connect("dating_app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, age, location, bio, photo_url FROM users")
    rows = cursor.fetchall()
    conn.close()
    
    profiles = []
    for row in rows:
        profiles.append({
            "id": row[0],
            "name": row[1],
            "age": row[2],
            "location": row[3],
            "bio": row[4],
            "photo_url": row[5]
        })
    return {"profiles": profiles}

@app.post("/users/add")
def add_user(user: UserCreate):
    conn = sqlite3.connect("dating_app.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, age, location, bio, photo_url) VALUES (?, ?, ?, ?, ?)",
        (user.name, user.age, user.location, user.bio, user.photo_url)
    )
    conn.commit()
    conn.close()
    return {"message": "Profile created successfully"}

@app.post("/like")
def like_user(like: LikeRequest):
    conn = sqlite3.connect("dating_app.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO likes (from_user_id, to_user_id) VALUES (?, ?)",
        (like.from_user_id, like.to_user_id)
    )
    
    # Check if mutual match
    cursor.execute(
        "SELECT * FROM likes WHERE from_user_id = ? AND to_user_id = ?",
        (like.to_user_id, like.from_user_id)
    )
    match = cursor.fetchone()
    conn.commit()
    conn.close()
    
    if match:
        return {"status": "match", "message": "It's a Match!"}
    
    return {"status": "liked", "message": "Like recorded"}
# ഹോസ്റ്റുകൾക്ക് പണം പിൻവലിക്കാനുള്ള അപേക്ഷ നൽകാനുള്ള API
@app.post("/request-withdrawal")
def request_withdrawal(host_id: int, request_amount: float):
    # ഹോസ്റ്റിന്റെ അക്കൗണ്ടിൽ ആവശ്യത്തിന് പൈസ ഉണ്ടോ എന്ന് നോക്കാം
    cursor.execute("SELECT available_balance FROM host_earnings WHERE host_id = ?", (host_id,))
    result = cursor.fetchone()

    if not result:
        return {"status": "error", "message": "ഹോസ്റ്റിനെ കണ്ടെത്താൻ കഴിഞ്ഞില്ല"}

    available_balance = result[0]

    # ചോദിച്ച തുക അക്കൗണ്ടിലുള്ളതിനേക്കാൾ കൂടുതലാണെങ്കിൽ എറർ കാണിക്കുക
    if request_amount > available_balance:
        return {"status": "error", "message": "അക്കൗണ്ടിൽ ആവശ്യത്തിന് പണമില്ല"}

    # പണം ഉണ്ടെങ്കിൽ, ബാലൻസിൽ നിന്ന് ആ തുക കുറയ്ക്കാം
    cursor.execute(
        "UPDATE host_earnings SET available_balance = available_balance - ? WHERE host_id = ?",
        (request_amount, host_id)
    )
    conn.commit()

    remaining_balance = available_balance - request_amount
    
    return {
        "status": "success",
        "message": f"{request_amount} രൂപ പിൻവലിക്കാനുള്ള അപേക്ഷ സ്വീകരിച്ചു.",
        "remaining_balance": remaining_balance
    }
