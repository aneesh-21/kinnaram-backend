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

# 1 രൂപ മെസ്സേജ് ചാർജ്ജ്
@app.post("/charge-message")
def charge_message(user_id: int):
    return deduct_user_balance(user_id, 1.0)

# 10 രൂപ വോയിസ് കോൾ ചാർജ്ജ്
@app.post("/charge-voice-call")
def charge_voice_call(user_id: int):
    return deduct_user_balance(user_id, 10.0)

# 15 രൂപ വീഡിയോ കോൾ ചാർജ്ജ്
@app.post("/charge-video-call")
def charge_video_call(user_id: int):
    return deduct_user_balance(user_id, 15.0)

# വാലറ്റിൽ നിന്ന് പണം കുറയ്ക്കുന്ന കോമൺ ഫങ്ഷൻ
def deduct_user_balance(user_id: int, amount: float):
    cursor.execute("SELECT balance FROM user_wallets WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if not result or result[0] < amount:
        return {"status": "error", "message": "ബാലൻസ് കുറവാണ്, റീചാർജ് ചെയ്യുക"}
    
    cursor.execute(
        "UPDATE user_wallets SET balance = balance - ? WHERE user_id = ?",
        (amount, user_id)
    )
    conn.commit()
    return {"status": "success", "message": f"{amount} രൂപ ഈടാക്കി"}
# ഹോസ്റ്റിനുള്ള ഷെയർ കണക്കാക്കി പണം നൽകുന്ന കോമൺ ഫങ്ഷൻ
def process_host_payout(host_id: int, user_paid_amount: float, host_share_amount: float):
    cursor.execute(
        "INSERT INTO host_earnings (host_id, total_earned, available_balance) VALUES (?, ?, ?) "
        "ON CONFLICT(host_id) DO UPDATE SET "
        "total_earned = total_earned + ?, "
        "available_balance = available_balance + ?",
        (host_id, host_share_amount, host_share_amount, host_share_amount, host_share_amount)
    )
    conn.commit()

# 1. മെസ്സേജ് അയക്കുമ്പോൾ (യൂസർ 1 രൂപ തരുമ്പോൾ ഹോസ്റ്റിന് 0.05 രൂപ കിട്ടും)
@app.post("/charge-message")
def charge_message(user_id: int, host_id: int):
    res = deduct_user_balance(user_id, 1.0)
    if res["status"] == "error":
        return res
    
    process_host_payout(host_id, 1.0, 0.05)
    return {"status": "success", "message": "മെസ്സേജ് അയച്ചു, പണം ഈടാക്കി"}

# 2. വോയിസ് കോൾ മിനിറ്റിന് (യൂസർ 10 രൂപ തരുമ്പോൾ ഹോസ്റ്റിന് 7 രൂപ കിട്ടും)
@app.post("/charge-voice-call")
def charge_voice_call(user_id: int, host_id: int, minutes: float = 1.0):
    total_cost = 10.0 * minutes
    host_amount = 7.0 * minutes
    
    res = deduct_user_balance(user_id, total_cost)
    if res["status"] == "error":
        return res
        
    process_host_payout(host_id, total_cost, host_amount)
    return {"status": "success", "message": f"വോയിസ് കോൾ ചാർജ് ചെയ്തു: {total_cost} രൂപ"}

# 3. വീഡിയോ കോൾ മിനിറ്റിന് (യൂസർ 15 രൂപ തരുമ്പോൾ ഹോസ്റ്റിന് 12 രൂപ കിട്ടും)
@app.post("/charge-video-call")
def charge_video_call(user_id: int, host_id: int, minutes: float = 1.0):
    total_cost = 15.0 * minutes
    host_amount = 12.0 * minutes
    
    res = deduct_user_balance(user_id, total_cost)
    if res["status"] == "error":
        return res
        
    process_host_payout(host_id, total_cost, host_amount)
    return {"status": "success", "message": f"വീഡിയോ കോൾ ചാർജ് ചെയ്തു: {total_cost} രൂപ"}
# അഡ്മിൻ ബാലൻസ് സേവ് ചെയ്യാനുള്ള ടേബിൾ
cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin_earnings (
        id INTEGER PRIMARY KEY,
        total_balance REAL DEFAULT 0.0
    )
''')
conn.commit()

# അഡ്മിൻ ബാലൻസ് അപ്ഡേറ്റ് ചെയ്യുന്ന ഫങ്ഷൻ
def add_admin_earnings(amount: float):
    cursor.execute(
        "INSERT INTO admin_earnings (id, total_balance) VALUES (1, ?) "
        "ON CONFLICT(id) DO UPDATE SET total_balance = total_balance + ?",
        (amount, amount)
    )
    conn.commit()

# 1. മെസ്സേജ് അയക്കുമ്പോൾ (ഹോസ്റ്റിന് 0.05, ബാക്കി 0.95 അഡ്മിന്)
@app.post("/charge-message")
def charge_message(user_id: int, host_id: int):
    res = deduct_user_balance(user_id, 1.0)
    if res["status"] == "error":
        return res
    
    process_host_payout(host_id, 1.0, 0.05)
    add_admin_earnings(0.95)
    return {"status": "success", "message": "മെസ്സേജ് അയച്ചു, പണം ഈടാക്കി"}

# 2. വോയിസ് കോൾ (ഹോസ്റ്റിന് 7 രൂപ/മിനിറ്റ്, ബാക്കി 3 രൂപ അഡ്മിന്)
@app.post("/charge-voice-call")
def charge_voice_call(user_id: int, host_id: int, minutes: float = 1.0):
    total_cost = 10.0 * minutes
    host_amount = 7.0 * minutes
    admin_amount = 3.0 * minutes
    
    res = deduct_user_balance(user_id, total_cost)
    if res["status"] == "error":
        return res
        
    process_host_payout(host_id, total_cost, host_amount)
    add_admin_earnings(admin_amount)
    return {"status": "success", "message": f"വോയിസ് കോൾ ചാർജ് ചെയ്തു: {total_cost} രൂപ"}

# 3. വീഡിയോ കോൾ (ഹോസ്റ്റിന് 12 രൂപ/മിനിറ്റ്, ബാക്കി 3 രൂപ അഡ്മിന്)
@app.post("/charge-video-call")
def charge_video_call(user_id: int, host_id: int, minutes: float = 1.0):
    total_cost = 15.0 * minutes
    host_amount = 12.0 * minutes
    admin_amount = 3.0 * minutes
    
    res = deduct_user_balance(user_id, total_cost)
    if res["status"] == "error":
        return res
        
    process_host_payout(host_id, total_cost, host_amount)
    add_admin_earnings(admin_amount)
    return {"status": "success", "message": f"വീഡിയോ കോൾ ചാർജ് ചെയ്തു: {total_cost} രൂപ"}

# അഡ്മിന് കിട്ടിയ മൊത്തം തുക പരിശോധിക്കാനുള്ള API
@app.get("/admin-balance")
def get_admin_balance():
    cursor.execute("SELECT total_balance FROM admin_earnings WHERE id = 1")
    result = cursor.fetchone()
    balance = result[0] if result else 0.0
    return {"admin_balance": balance}
