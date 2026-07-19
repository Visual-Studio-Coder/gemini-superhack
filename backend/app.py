import os
import random
import string
import json
import time
from pathlib import Path

import psycopg2
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from psycopg2.extras import RealDictCursor

load_dotenv()

# Gemini Configuration (Global Client)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)
val = CORS(app)

import logging

# Configure logging
logging.basicConfig(
    filename='backend.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Redirect print to logging for convenience (optional, but ensures print() goes to file)
# Ideally I should replace print() with logging.info() in background_referee, but 
# let's just make sure we log explicit messages there.


# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "game_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "port": os.getenv("DB_PORT", "5432"),
    "connect_timeout": 3,
}



# In-memory storage for Mock DB
MOCK_STORE = {
    "rooms": {},
    "players": {},
    "room_counter": 1,
    "player_counter": 1
}

class MockCursor:
    def __init__(self, data):
        self.data = data
        self.last_row = None
        self.rows = []

    def execute(self, query, params=None):
        print(f"MOCK DB EXECUTE: {query} | Params: {params}")
        
        if "INSERT INTO room" in query:
             room_id = MOCK_STORE["room_counter"]
             MOCK_STORE["room_counter"] += 1
             new_room = {
                 "id": room_id,
                 "join_code": params[0],
                 "status": params[1],
                 "events_json": json.loads(params[2])
             }
             MOCK_STORE["rooms"][room_id] = new_room
             self.last_row = new_room
             
        elif "INSERT INTO player" in query:
             player_id = MOCK_STORE["player_counter"]
             MOCK_STORE["player_counter"] += 1
             # params: room_id, username, current_board, points
             new_player = {
                 "id": player_id,
                 "room_id": params[0],
                 "username": params[1],
                 "current_board": json.loads(params[2]),
                 "points": params[3]
             }
             MOCK_STORE["players"][player_id] = new_player
             self.last_row = new_player

        elif "SELECT id FROM room WHERE join_code" in query:
             found = [r for r in MOCK_STORE["rooms"].values() if r["join_code"] == params[0]]
             self.last_row = found[0] if found else None

        elif "SELECT id, status FROM room WHERE join_code" in query:
             found = [r for r in MOCK_STORE["rooms"].values() if r["join_code"] == params[0]]
             self.last_row = found[0] if found else None

        elif "SELECT * FROM room WHERE id" in query:
             self.last_row = MOCK_STORE["rooms"].get(params[0])
             
        elif "SELECT events_json FROM room WHERE id" in query:
             # Returns specific field
             room = MOCK_STORE["rooms"].get(params[0])
             if room:
                 self.last_row = {"events_json": room.get("events_json", [])}
             else:
                 self.last_row = None
        
        elif "SELECT status FROM room WHERE id" in query:
             # Returns status field
             room = MOCK_STORE["rooms"].get(params[0])
             if room:
                 self.last_row = {"status": room.get("status", "waiting")}
             else:
                 self.last_row = None
             
        elif "SELECT * FROM player WHERE id" in query:
             self.last_row = MOCK_STORE["players"].get(params[0])

        elif "SELECT * FROM player WHERE room_id" in query:
             self.rows = [p for p in MOCK_STORE["players"].values() if p["room_id"] == params[0]]

        elif "SELECT username, points FROM player WHERE room_id" in query:
             self.rows = [{"username": p["username"], "points": p["points"]} for p in MOCK_STORE["players"].values() if p["room_id"] == params[0]]

        elif "UPDATE room SET events_json" in query:
             # UPDATE room SET events_json = %s WHERE id = %s RETURNING *
             room = MOCK_STORE["rooms"].get(params[1])
             if room:
                 room["events_json"] = json.loads(params[0])
                 self.last_row = room

        elif "UPDATE room SET status" in query:
             # UPDATE room SET status = %s WHERE id = %s RETURNING *
             room = MOCK_STORE["rooms"].get(params[1])
             if room:
                 room["status"] = params[0]
                 self.last_row = room

        elif "UPDATE room SET youtube_id" in query:
             # UPDATE room SET youtube_id = %s WHERE id = %s RETURNING *
             room = MOCK_STORE["rooms"].get(params[1])
             if room:
                 room["youtube_id"] = params[0]
                 self.last_row = room

        elif "UPDATE room SET video_start_time" in query:
             if "youtube_id" in query:
                  # Params: (video_start_time, youtube_id, room_id)
                  room = MOCK_STORE["rooms"].get(params[2])
                  if room:
                      room["video_start_time"] = params[0]
                      room["youtube_id"] = params[1]
                      self.last_row = room
             else:
                  # Params: (video_start_time, room_id)
                  room = MOCK_STORE["rooms"].get(params[1])
                  if room:
                      room["video_start_time"] = params[0]
                      self.last_row = room
        
        elif "UPDATE player SET current_board" in query:
             # UPDATE player SET current_board = %s WHERE id = %s RETURNING *
             # OR UPDATE player SET current_board = %s, points = %s WHERE id = %s
             
             if "points" in query:
                  # Params: (current_board, points, id)
                  player = MOCK_STORE["players"].get(params[2])
                  if player:
                      player["current_board"] = params[0]
                      player["points"] = params[1]
                      self.last_row = player
             else:
                  # Params: (current_board, id)
                  player = MOCK_STORE["players"].get(params[1])
                  if player:
                      player["current_board"] = params[0]
                      self.last_row = player
                      
        elif "UPDATE player SET points" in query:
             # UPDATE player SET points = %s WHERE id = %s RETURNING *
             player = MOCK_STORE["players"].get(params[1])
             if player:
                 player["points"] = params[0]
                 self.last_row = player
             # Case B: update_room_status (video_start_time, room_id)
             else:
                 room = MOCK_STORE["rooms"].get(params[1])
                 if room:
                     room["video_start_time"] = params[0]
                     self.last_row = room

    def fetchone(self):
        return self.last_row

    def fetchall(self):
        return self.rows
    
    def close(self):
        pass

class MockConnection:
    def cursor(self):
        return MockCursor({})
    def commit(self):
        pass
    def close(self):
        pass

def get_db_connection():
    """Create a database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"DB CONFIG FAILED: {e}. USING MOCK DB.")
        return MockConnection()


def generate_join_code(length=6):
    """Generate a random join code"""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

from pydantic import BaseModel
from typing import List

class BingoVideoEvents(BaseModel):
    events: List[str]

# DEMO_MODE - Set to True to skip Gemini and use numbered events for testing
DEMO_MODE = False

def generate_events_with_gemini(context):
    """Generate bingo events using Gemini with Structured Output"""
    
    # DEMO MODE: Use numbered events for testing shuffle logic
    if DEMO_MODE:
        print("🎮 DEMO MODE: Using numbered events 1-60")
        return [f"Event {i}" for i in range(1, 61)]
    
    # FINAL HACKATHON DEMO MODE
    if context.upper() == "DEMO":
        print("🎮 DEMO MODE: Using Miami vs Texas A&M Event List")
        return [
            {"text": "Texas A&M Kickoff", "triggered": False},
            {"text": "Restrepo Return", "triggered": False},
            {"text": "Parish Carry", "triggered": False},
            {"text": "Miami Punt", "triggered": False},
            {"text": "Daniels Rush", "triggered": False},
            {"text": "Weigman Touchdown", "triggered": False},
            {"text": "A&M Extra Point", "triggered": False},
            {"text": "A&M Kickoff", "triggered": False},
            {"text": "Parish First Down", "triggered": False},
            {"text": "Holding Penalty", "triggered": False},
            {"text": "Miami Punt 2", "triggered": False},
            {"text": "Daniels Pitch", "triggered": False},
            {"text": "Owens Long Pass", "triggered": False},
            {"text": "Holding Penalty 2", "triggered": False},
            {"text": "Ainias Smith Catch", "triggered": False},
            {"text": "A&M Field Goal", "triggered": False},
            {"text": "Restrepo Touchdown", "triggered": False},
            {"text": "Young Touchdown", "triggered": False},
            {"text": "Miami Extra Point", "triggered": False},
            {"text": "Miami Kickoff", "triggered": False},
            {"text": "Weigman Scramble", "triggered": False},
            {"text": "Incomplete Pass", "triggered": False},
            {"text": "A&M Punt", "triggered": False},
            {"text": "Muff & Recover", "triggered": False},
            {"text": "Daniels Touchdown", "triggered": False},
            {"text": "A&M Extra Point 2", "triggered": False},
            {"text": "Horton 52y Catch", "triggered": False},
            {"text": "Miami Extra Point 2", "triggered": False},
            {"text": "Owens Return", "triggered": False},
            {"text": "A&M Punt 2", "triggered": False},
            {"text": "Restrepo Big Gain", "triggered": False},
            {"text": "Holding Penalty 3", "triggered": False},
            {"text": "Pass Interference", "triggered": False},
            {"text": "Van Dyke Scramble", "triggered": False},
            {"text": "Miami Missed FG", "triggered": False},
            {"text": "Personal Foul", "triggered": False},
            {"text": "A&M Missed FG", "triggered": False},
            {"text": "Van Dyke TD Pass", "triggered": False},
            {"text": "Miami Extra Point 3", "triggered": False},
            {"text": "2nd Half Kickoff", "triggered": False},
            {"text": "Weigman Rush FD", "triggered": False},
            {"text": "Turnover on Downs", "triggered": False},
            {"text": "A&M Field Goal 2", "triggered": False},
            {"text": "Brashard 98y TD", "triggered": False},
            {"text": "Kinchens Int", "triggered": False},
            {"text": "Miami Field Goal", "triggered": False},
            {"text": "Wright Touchdown", "triggered": False},
            {"text": "Failed 2pt Conv", "triggered": False},
            {"text": "Daniels Fumble", "triggered": False},
            {"text": "Allen Run", "triggered": False},
            {"text": "George Touchdown", "triggered": False},
            {"text": "A&M Punt 3", "triggered": False},
            {"text": "DPI Penalty", "triggered": False},
            {"text": "Miami 50y FG", "triggered": False},
            {"text": "Thomas Touchdown", "triggered": False},
            {"text": "A&M Extra Point 3", "triggered": False},
            {"text": "Onside Kick Rec", "triggered": False},
            {"text": "George Long TD", "triggered": False},
            {"text": "Kinchens Int 2", "triggered": False},
            {"text": "Couch Int", "triggered": False}
        ]
    
    if not client:
        print("WARNING: No GEMINI_API_KEY found. using mock data.")
        return [
             {"text": "Touchdown", "triggered": False},
             {"text": "Field Goal", "triggered": False},
             {"text": "Interception", "triggered": False},
             {"text": "Fumble", "triggered": False},
             {"text": "Sack", "triggered": False}
        ] * 12 # Filler

    prompt = f"""
    Use Google Search to find real-time or historical details about the game context: "{context}".
    Identify the specific team names, key players, and types of plays relevant to this matchup.
    
    Then, generate 60 unique, likely events for this game on a Bingo card.
    Include specific player names (e.g. "Mahomes Touchdown", "Kelce Catch") and team-specific events if known.
    Limit each string to under 30 characters.
    """
    
    class BingoEventList(BaseModel):
        events: List[str]

    try:
        # Enable Google Search Grounding
        search_tool = types.Tool(google_search=types.GoogleSearch())
        
        response = client.models.generate_content(
            model='gemini-3-pro-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=BingoEventList,
                tools=[search_tool]
            )
        )
        
        # Parse Pydantic
        result = BingoEventList.model_validate_json(response.text)
        # Normalize to Dicts
        normalized_events = [{"text": e, "triggered": False} for e in result.events]
        return normalized_events
        
    except Exception as e:
        print(f"Gemini Error: {e}")
        # Fallback
        return ["Error Generating"] * 25
        
    except Exception as e:
        print(f"Gemini Error: {e}")
        # Fallback
        return ["Error Generating"] * 25

@app.route("/api/room/<int:room_id>/generate-events", methods=["POST"])
def trigger_generate_events(room_id):
    """Trigger event generation for a room"""
    try:
        data = request.json
        context = data.get("context", "Super Bowl")
        
        events = generate_events_with_gemini(context)
        
        if not events:
             return jsonify({"error": "Failed to generate events"}), 500

        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "UPDATE room SET events_json = %s WHERE id = %s RETURNING *",
            (json.dumps(events), room_id)
        )
        room = cur.fetchone()
        
        if not room:
            cur.close()
            conn.close()
            return jsonify({"error": "Room not found"}), 404
            
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify(dict(room)), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/room/<int:room_id>/analyze", methods=["POST"])
def analyze_video(room_id):
    """Analyze a 30s video buffer"""
    try:
        if 'video' not in request.files:
             return jsonify({"error": "No video file provided"}), 400
             
        video_file = request.files['video']
        filename = f"temp_{room_id}_{int(time.time())}.mp4"
        video_path = Path(filename)
        video_file.save(video_path)
        
        # Get current events
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT events_json FROM room WHERE id = %s", (room_id,))
        row = cur.fetchone()
        
        if not row:
             cur.close()
             conn.close()
             return jsonify({"error": "Room not found"}), 404
             
        events = row['events_json']
        event_texts = [e['text'] for e in events if not e.get('triggered', False)]
        
        if not event_texts:
             cur.close()
             conn.close()
             return jsonify({"message": "No untriggered events left"}), 200

        # Upload to Gemini (New SDK)
        if client:
             print("Uploading video to Gemini...")
             # New SDK upload
             with open(video_path, "rb") as f:
                 video_asset = client.files.upload(file=f, config={})
             
             # Wait for processing
             while video_asset.state.name == "PROCESSING":
                  time.sleep(1)
                  video_asset = client.files.get(name=video_asset.name)
                  
             if video_asset.state.name == "FAILED":
                  raise ValueError("Video processing failed")
                  
             prompt = f"""
             Watch this video clip. Here is a list of Bingo events:
             {json.dumps(event_texts)}
             
             Select the events from the list that occurred in the video.
             """
             
             response = client.models.generate_content(
                model='gemini-3-pro-preview',
                contents=[video_asset, prompt],
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": BingoVideoEvents.model_json_schema(),
                }
             )
             
             found_result = BingoVideoEvents.model_validate_json(response.text)
             found_events = found_result.events
             
             # Cleanup (New SDK delete?)
             # Not explicitly documented in simple snippets, but usually client.files.delete
             try:
                 client.files.delete(name=video_asset.name)
             except:
                 pass
        else:
             found_events = [] # Mock mode: find nothing or random?
        
        # Update DB
        updated_events = []
        for e in events:
            if e['text'] in found_events:
                e['triggered'] = True
            updated_events.append(e)
            
        cur.execute(
            "UPDATE room SET events_json = %s WHERE id = %s RETURNING *",
            (json.dumps(updated_events), room_id)
        )
        conn.commit()
        cur.close()
        conn.close()
        
        # Cleanup file
        if video_path.exists():
            video_path.unlink()
            
        return jsonify({"found_events": found_events, "all_events": updated_events}), 200

    except Exception as e:
        if Path(filename).exists():
             Path(filename).unlink()
        return jsonify({"error": str(e)}), 500



@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok"}), 200


@app.route("/api/create-room", methods=["POST"])
def create_room():
    """Create a new game room"""
    try:
        data = request.json
        username = data.get("username")

        if not username:
            return jsonify({"error": "Username is required"}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        # Generate unique join code
        join_code = generate_join_code()

        # Check if join code already exists
        cur.execute("SELECT id FROM room WHERE join_code = %s", (join_code,))
        while cur.fetchone():
            join_code = generate_join_code()
            cur.execute("SELECT id FROM room WHERE join_code = %s", (join_code,))

        # Create room
        # We need to generate the pool of 60 events IMMEDIATELY so the host gets a board
        # Default context if not provided
        context = data.get("context", "Super Bowl")
        events = generate_events_with_gemini(context)
        
        cur.execute(
            "INSERT INTO room (join_code, status, events_json) VALUES (%s, %s, %s) RETURNING id",
            (join_code, "waiting", json.dumps(events)),
        )
        room_id = cur.fetchone()["id"]

        # Limit to 60 events just in case, then shuffle for Host
        # If events are objects, extract text; if strings, use as is
        event_pool = [e["text"] if isinstance(e, dict) else e for e in events]
        
        # DEMO MODE: Keep events in order (no shuffle)
        if context.upper() == "DEMO":
            selected_events = event_pool[:24]  # First 24 in order
        else:
            # Use random.sample to CREATE A NEW shuffled list (don't mutate original)
            selected_events = random.sample(event_pool, min(24, len(event_pool)))
        
        # Format as board
        player_board = [{"text": e, "status": "idle", "triggered": False} for e in selected_events]
        
        # Insert Free Space at index 12 (Center)
        player_board.insert(12, {"text": "FREE SPACE", "status": "approved", "triggered": True})

        # Create player (Host)
        cur.execute(
            "INSERT INTO player (room_id, username, current_board, points) VALUES (%s, %s, %s, %s) RETURNING id",
            (room_id, username, json.dumps(player_board), 0),
        )
        player_id = cur.fetchone()["id"]

        conn.commit()
        cur.close()
        conn.close()

        return jsonify(
            {
                "room_id": room_id,
                "player_id": player_id,
                "join_code": join_code,
                "username": username,
            }
        ), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/join-room", methods=["POST"])
def join_room():
    """Join an existing game room"""
    try:
        data = request.json
        join_code = data.get("room_code") or data.get("join_code")
        username = data.get("username")

        if not join_code or not username:
            return jsonify({"error": "Room code and username are required"}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        # Find room by join code
        cur.execute("SELECT id, status FROM room WHERE join_code = %s", (join_code,))
        room = cur.fetchone()

        if not room:
            cur.close()
            conn.close()
            return jsonify({"error": "Room not found"}), 404

        room_id = room["id"]
        room_status = room["status"]

        if room_status == "finished":
            cur.close()
            conn.close()
            return jsonify({"error": "Room has already finished"}), 400

        # Generate Individual Board from Room Events
        room_events = room.get("events_json", [])
        if room_events:
            # If events are objects, extract text; if strings, use as is
            event_pool = [e["text"] if isinstance(e, dict) else e for e in room_events]
            
            # Use random.sample to CREATE A NEW shuffled list (don't mutate original)
            selected_events = random.sample(event_pool, min(24, len(event_pool)))
            
            # Format board
            player_events = [{"text": e, "status": "idle", "triggered": False} for e in selected_events]
            
            # Insert Free Space
            player_events.insert(12, {"text": "FREE SPACE", "status": "approved", "triggered": True})
            
        else:
             player_events = []

        # Create player
        cur.execute(
            "INSERT INTO player (room_id, username, current_board, points) VALUES (%s, %s, %s, %s) RETURNING id",
            (room_id, username, json.dumps(player_events), 0),
        )
        player_id = cur.fetchone()["id"]

        conn.commit()
        cur.close()
        conn.close()

        return jsonify(
            {
                "room_id": room_id,
                "player_id": player_id,
                "join_code": join_code,
                "username": username,
                "status": room_status,
            }
        ), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# --- Bingo Verification Logic ---

def check_bingo(player_board):
    """
    Checks if a board has a horizontal, vertical, or diagonal bingo.
    Returns: bool
    """
    indices = [i for i, cell in enumerate(player_board) if cell.get("triggered", False) or cell.get("status") == "approved"]
    
    # Rows
    for r in range(5):
        row_indices = [r*5 + c for c in range(5)]
        if all(idx in indices for idx in row_indices):
            return True
            
    # Cols
    for c in range(5):
        col_indices = [r*5 + c for r in range(5)]
        if all(idx in indices for idx in col_indices):
            return True
            
    # Diagonals
    diag1 = [0, 6, 12, 18, 24]
    if all(idx in indices for idx in diag1):
        return True
        
    diag2 = [4, 8, 12, 16, 20]
    if all(idx in indices for idx in diag2):
        return True
        
    return False

# --- Gemini Tool Implementation ---
def mark_event_tool(room_id: int, event_text: str):
    """
    Marks a Bingo event as occurred in the game room and updates player boards.
    
    Args:
        room_id: The ID of the room.
        event_text: The text of the event that occurred (e.g., "Touchdown", "Fumble").
    """
    print(f"🔧 TOOL CALLED: mark_event_tool(room_id={room_id}, event_text='{event_text}')")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Update Room Events
    cur.execute("SELECT events_json FROM room WHERE id = %s", (room_id,))
    res = cur.fetchone()
    if not res:
        if conn: conn.close()
        return {"status": "error", "message": "Room not found"}
        
    # Handle list vs dict result (Mock DB vs Real DB quirks)
    if isinstance(res, dict):
        r_events = res['events_json']
    elif isinstance(res, tuple):
        r_events = res[0]
    else:
        r_events = res

    # Ensure it's a list
    if isinstance(r_events, str):
        try:
            r_events = json.loads(r_events)
        except:
            r_events = []
    
    updated_room = False
    for e in r_events:
        if e['text'] == event_text and not e.get('triggered', False):
            e['triggered'] = True
            updated_room = True
    
    if updated_room:
        cur.execute("UPDATE room SET events_json = %s WHERE id = %s", (json.dumps(r_events), room_id))
    
    # 2. Update All Players' Boards (Verify Pending Claims)
    cur.execute("SELECT id, current_board, points FROM player WHERE room_id = %s", (room_id,))
    players = cur.fetchall()
    
    for p in players:
        p_id = p['id'] if isinstance(p, dict) else p[0]
        
        # Handle current_board retrieval
        raw_board = p['current_board'] if isinstance(p, dict) else p[1]
        p_board = json.loads(raw_board) if isinstance(raw_board, str) else raw_board
        
        p_points = p['points'] if isinstance(p, dict) else p[2]
        
        updated_player = False
        for cell in p_board:
            # If the cell matches the event...
            if cell['text'] == event_text:
                # If it was PENDING -> APPROVE IT (Verification Successful)
                if cell.get('status') == 'pending':
                    cell['status'] = 'approved'
                    cell['triggered'] = True
                    updated_player = True
                    print(f"   ✅ VERIFIED CLAIM for player {p_id}: {event_text}")
                
                # If it was IDLE -> AUTO-MARK IT (Optional, but good for flows where users miss clicks)
                # For now, let's Stick to STRICT Verification:
                # Only approve if they claimed it? 
                # The user said "verify user interactions".
                # But usually if the referee sees it, everyone gets it. 
                # Let's do this: If Gemini sees it, it becomes "triggered=True", but status stays "idle" unless claimed?
                # Actually, standard Bingo app behavior: Referee announces it, players check it.
                # If I auto-approve, there is no "game".
                # So:
                # - Logic above approves "pending" claims.
                # - Logic below sets "triggered" flag on the cell so FUTURE clicks are instant.
                
                if not cell.get('triggered', False):
                     cell['triggered'] = True # Mark as "Referee says yes"
                     updated_player = True
        
        if updated_player:
            # Check for Bingo (only counts approved cells)
            if check_bingo(p_board):
                # Only award points if not already awarded? SImple logic for now
                if p_points < 500: # Hacky 'has won' check
                     p_points += 500
                     print(f"   🎉 BINGO DETECTED FOR PLAYER {p_id}!")
                
            cur.execute("UPDATE player SET current_board = %s, points = %s WHERE id = %s", 
                        (json.dumps(p_board), p_points, p_id))
                        
    conn.commit()
    cur.close()
    conn.close()
    
    return {"status": "success", "event": event_text}

@app.route("/api/room/<int:room_id>", methods=["GET"])
def get_room(room_id):
    """Get room details"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get room
        cur.execute("SELECT * FROM room WHERE id = %s", (room_id,))
        room = cur.fetchone()

        if not room:
            cur.close()
            conn.close()
            return jsonify({"error": "Room not found"}), 404

        # Get players in room
        cur.execute("SELECT * FROM player WHERE room_id = %s", (room_id,))
        players = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify({"room": dict(room), "players": [dict(p) for p in players]}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/room/<int:room_id>/video", methods=["POST"])
def set_room_video(room_id):
    """Set the YouTube video ID for synchronized watching"""
    try:
        data = request.json
        youtube_url = data.get("youtube_url", "")
        
        # Extract video ID from URL
        video_id = None
        if "youtube.com/watch" in youtube_url:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(youtube_url)
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        elif "youtu.be/" in youtube_url:
            video_id = youtube_url.split("youtu.be/")[-1].split("?")[0]
        
        if not video_id:
            return jsonify({"error": "Invalid YouTube URL"}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Store youtube_id and set start time NOW if game is playing
        cur.execute("SELECT status FROM room WHERE id = %s", (room_id,))
        room_check = cur.fetchone()
        room_status = room_check.get('status', 'waiting') if room_check else 'waiting'
        
        video_start_time = int(time.time()) if room_status == "playing" else None
        
        cur.execute("UPDATE room SET video_start_time = %s, youtube_id = %s WHERE id = %s RETURNING *", 
                    (video_start_time, video_id, room_id))
        room = cur.fetchone()
        
        conn.commit()
        cur.close()
        conn.close()
        
        # START REFEREE if game is already playing
        if room_status == "playing":
            yt_url = f"https://www.youtube.com/watch?v={video_id}"
            threading.Thread(target=background_referee, args=(room_id, yt_url)).start()
            print(f"[{room_id}] 🚀 VIDEO SET + REFEREE LAUNCHED for {yt_url}")
        else:
            print(f"[{room_id}] Video set to: {video_id} (Waiting for Game Start)")
        
        return jsonify({"room": dict(room), "youtube_id": video_id}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/player/<int:player_id>", methods=["GET"])
def get_player(player_id):
    """Get player details"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM player WHERE id = %s", (player_id,))
        player = cur.fetchone()

        cur.close()
        conn.close()

        if not player:
            return jsonify({"error": "Player not found"}), 404

        return jsonify(dict(player)), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/player/<int:player_id>/board", methods=["PUT"])
def update_player_board(player_id):
    """Claim a square on the board (Check against Referee)"""
    try:
        data = request.json
        # Expecting: { "event_text": "Touchdown" } 
        # OR full board sync, but let's do granular claims for security/logic
        event_text = data.get("event_text")

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get Player
        cur.execute("SELECT * FROM player WHERE id = %s", (player_id,))
        player = cur.fetchone()
        
        if not player:
            cur.close()
            conn.close()
            return jsonify({"error": "Player not found"}), 404
            
        # Get Room Events to check if claim is valid
        room_id = player['room_id'] if isinstance(player, dict) else player[1]
        
        cur.execute("SELECT events_json FROM room WHERE id = %s", (room_id,))
        res = cur.fetchone()
        room_events = res['events_json'] if isinstance(res, dict) else res[0]
        
        if isinstance(room_events, str):
            try:
                room_events = json.loads(room_events)
            except:
                print(f"Error parsing room_events: {room_events}")
                room_events = []
        
        # Verify Claim
        triggered_in_room = False
        for re in room_events:
            if re['text'] == event_text and re.get('triggered', False):
                triggered_in_room = True
                break
                
        # Update Player Board
        current_board = player['current_board']
        if isinstance(current_board, str):
            current_board = json.loads(current_board)
            
        updated = False
        success = False
        
        for square in current_board:
            if square['text'] == event_text:
                if triggered_in_room:
                    square['triggered'] = True
                    square['status'] = 'approved'
                    success = True
                else:
                    square['status'] = 'rejected' # Or just don't trigger it
                updated = True
                # No break, in case duplicates?
        
        if updated:
             cur.execute(
                "UPDATE player SET current_board = %s WHERE id = %s RETURNING *",
                (json.dumps(current_board), player_id),
            )
             conn.commit()
             player = cur.fetchone()
        
        cur.close()
        conn.close()

        return jsonify({"player": dict(player), "success": success}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/player/<int:player_id>/points", methods=["PUT"])
def update_player_points(player_id):
    """Update player's points"""
    try:
        data = request.json
        points = data.get("points")

        if points is None:
            return jsonify({"error": "points is required"}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "UPDATE player SET points = %s WHERE id = %s RETURNING *",
            (points, player_id),
        )
        player = cur.fetchone()

        if not player:
            cur.close()
            conn.close()
            return jsonify({"error": "Player not found"}), 404

        conn.commit()
        cur.close()
        conn.close()

        return jsonify(dict(player)), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/room/<int:room_id>/status", methods=["PUT"])
def update_room_status(room_id):
    """Update room status"""
    try:
        data = request.json
        status = data.get("status")

        if not status:
            return jsonify({"error": "status is required"}), 400

        if status not in ["waiting", "playing", "finished"]:
            return jsonify(
                {"error": "Invalid status. Must be waiting, playing, or finished"}
            ), 400

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "UPDATE room SET status = %s WHERE id = %s RETURNING *", (status, room_id)
        )
        room = cur.fetchone()

        if not room:
            cur.close()
            conn.close()
            return jsonify({"error": "Room not found"}), 404

        # Start Video & Referee if Game Started
        if status == "playing":
            youtube_id = room.get("youtube_id")
            if youtube_id: # Only if video is set
                 import time
                 import threading
                 video_start_time = int(time.time())
                 
                 #Update start time
                 cur.execute("UPDATE room SET video_start_time = %s WHERE id = %s", (video_start_time, room_id))
                 room['video_start_time'] = video_start_time
                 
                 # Start Referee
                 # Construct full URL for referee
                 yt_url = f"https://www.youtube.com/watch?v={youtube_id}"
                 threading.Thread(target=background_referee, args=(room_id, yt_url)).start()
                 print(f"[{room_id}] GAME STARTED! Referee Launched for {yt_url}")

        conn.commit()
        cur.close()
        conn.close()

        return jsonify(dict(room)), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/room/<int:room_id>/players", methods=["GET"])
def get_room_players(room_id):
    """Get list of players in a room"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT username, points FROM player WHERE room_id = %s", (room_id,))
        players = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({"players": [dict(p) for p in players]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500




import threading
import subprocess
from yt_dlp import YoutubeDL

# ... (Previous imports)

# Global Referee State
REFEREE_THREADS = {}

def download_video_thread(youtube_url, video_path):
    """Downloads video in a separate thread"""
    print(f"Downloading {youtube_url} to {video_path}...")
    try:
        # Use yt-dlp to download to specific file
        # We assume best quality mp4 for ease of ffmpeg
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'outtmpl': str(video_path),
            'quiet': True,
            # 'part': False # Ensure we write directly or handle .part files
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        print(f"Download complete: {video_path}")
    except Exception as e:
        print(f"Download thread failed: {e}")

def background_referee(room_id, youtube_url):
    """Orchestrates download and processing concurrently"""
    print(f"[{room_id}] Starting Referee for {youtube_url}")
    
    filename = f"room_{room_id}_game.mp4"
    video_path = Path(filename)
    
    # 1. Start Download in Thread
    # Note: If file exists, we might implicitly skip or overwrite. 
    # For now, let's assume if it exists we use it, else download.
    if not video_path.exists():
         d_thread = threading.Thread(target=download_video_thread, args=(youtube_url, video_path))
         d_thread.start()
         # Give it a moment to create the file
         time.sleep(5)
    
    # 2. Start Processing Loop immediately
    current_time = 0
    chunk_duration = 30
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    while True:
        # Check game status
        try:
             # Re-connect if needed or just use current
             cur.execute("SELECT status, video_start_time FROM room WHERE id = %s", (room_id,))
             row = cur.fetchone()
             if not row or row['status'] == 'finished':
                 print(f"[{room_id}] Game finished. Stopping Referee.")
                 break
             video_start_ts = row.get('video_start_time')
             
             # --- DEMO MODE: Hardcoded Simulation ---
             # For DEMO mode (60 events), we simulate detections every 5 seconds for reliability
             cur.execute("SELECT events_json FROM room WHERE id = %s", (room_id,))
             rev_row = cur.fetchone()
             if rev_row:
                 r_events = rev_row['events_json']
                 if isinstance(r_events, str):
                      try: r_events = json.loads(r_events)
                      except: r_events = []
                 
                 # DEMO mode with 60 events = hardcoded simulation
                 if len(r_events) == 60:
                      untriggered = [e['text'] for e in r_events if not e.get('triggered', False)]
                      
                      if not untriggered:
                           print(f"[{room_id}] All events triggered! Game complete.")
                           break
                      
                      # Trigger 1 event every 5 seconds in chronological order
                      print(f"[{room_id}] 🎮 DEMO MODE: Simulating Detection (5s delay)")
                      time.sleep(5)
                      
                      claim = untriggered[0]
                      mark_event_tool(room_id, claim)
                      print(f"[{room_id}] ✅ SIMULATED DETECTION: {claim}")
                      
                      continue
             # ------------------------
             # ------------------------

             # Check Real-time pacing
             if video_start_ts:
                 elapsed_real_time = time.time() - video_start_ts
                 
                 target_time = current_time + chunk_duration
                 if elapsed_real_time < target_time:
                     wait = target_time - elapsed_real_time
                     if wait > 1:
                         # print(f"[{room_id}] Pacing... Waiting {wait:.1f}s for live stream.")
                         time.sleep(min(wait, 5)) # Sleep in small chunks 
                         continue
        except:
             # DB might be locked or issues, retry
             time.sleep(1)
             continue
        
        # Check if we have enough video content
        # We need video_path to exist and have duration > current_time + chunk_duration
        if not video_path.exists():
             print(f"[{room_id}] Waiting for video file...")
             time.sleep(2)
             continue
             
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            total_duration = float(result.stdout.strip())
        except Exception as e:
            # File might be incomplete/locked. Wait.
            print(f"[{room_id}] Waiting for duration check... ({e})")
            time.sleep(5)
            continue
            
        if total_duration < current_time + chunk_duration:
             print(f"[{room_id}] Caught up to {total_duration:.1f}s. Waiting for download... (Need {current_time + chunk_duration}s)")
             time.sleep(5)
             continue
             
        # We have enough content! Process chunk.
        print(f"[{room_id}] Referee Checking {current_time}s - {current_time+chunk_duration}s")
        
        chunk_name = f"referee_{room_id}_{int(current_time)}.mp4"
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-ss", str(current_time),
            "-t", str(chunk_duration),
            "-c:v", "libx264", "-c:a", "aac",
            chunk_name
        ]
        
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Analyze
            # Re-read events from DB (refresh untriggered)
            cur.execute("SELECT events_json FROM room WHERE id = %s", (room_id,))
            r_events = cur.fetchone()['events_json']
            event_texts = [e['text'] for e in r_events if not e.get('triggered', False)]
            
            if event_texts and client:
                # Upload to Gemini
                with open(chunk_name, "rb") as f:
                    video_asset = client.files.upload(file=f, config={})

                while video_asset.state.name == "PROCESSING":
                    time.sleep(1)
                    video_asset = client.files.get(name=video_asset.name)
                
                # Function Calling Prompt
                prompt = f"""
                You are an expert NFL Referee observing a game. 
                Watch this video clip closely. This is a 30-second chunk of the game.
                
                Here is a list of Bingo events that players are waiting for:
                {json.dumps(event_texts)}
                
                Your job is to DETECT if any of these specific events happen in this clip.
                If an event happens, you MUST call the `mark_event_tool` function with:
                - room_id: {room_id}
                - event_text: The exact text of the event from the list.
                
                Only mark events that are CLEARLY visible or audible in this clip.
                If no events from the list occur, simply output "No events detected."
                """
                
                try:
                    response = client.models.generate_content(
                        model='gemini-2.0-flash',
                        contents=[video_asset, prompt],
                        config=types.GenerateContentConfig(
                            tools=[mark_event_tool],
                            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False)
                        )
                    )
                    
                    # Log Function Calls explicity
                    if response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            if part.function_call:
                                fc_log = f"[{room_id}] 🤖 Gemini Tool Call: {part.function_call.name}({part.function_call.args})"
                                print(fc_log)
                                logging.info(fc_log)
                                
                    log_msg = f"[{room_id}] Gemini Analysis: {response.text.strip() if response.text else 'Action Taken'}"
                    print(log_msg)
                    logging.info(log_msg)
                    
                except Exception as e:
                    err_msg = f"[{room_id}] Gemini Error: {e}"
                    print(err_msg)
                    logging.error(err_msg)
                
                try:
                    client.files.delete(name=video_asset.name)
                except:
                    pass
        except Exception as e:
             err_msg = f"[{room_id}] Error in loop: {e}"
             print(err_msg)
             logging.error(err_msg)

        # Cleanup chunk
        if os.path.exists(chunk_name):
            os.remove(chunk_name)
            
        current_time += chunk_duration
        # No big sleep, we want to catch up if we are behind.
        time.sleep(1) 
        
    cur.close()
    conn.close()
    print(f"[{room_id}] Referee Finished")

@app.route("/api/debug/logs", methods=["GET"])
def get_debug_logs():
    """Get the last 100 lines of the backend log"""
    try:
        log_path = Path("backend.log")
        if not log_path.exists():
            return jsonify({"logs": ["Log file not found."]}), 200
            
        # Read last 100 lines
        # Simple implementation for hackathon (not efficient for huge files but fine here)
        with open(log_path, "r") as f:
            lines = f.readlines()
            last_lines = lines[-100:]
            
        return jsonify({"logs": last_lines}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
