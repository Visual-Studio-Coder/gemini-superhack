import json
from datetime import datetime
import psycopg2
import os

# Database connection helper (duplicated from app.py for standalone usage if needed, 
# but ideally we'd import or pass the connection)
def get_db_connection():
    if os.environ.get("USE_MOCK_DB") == "true":
        return None # Return None to signal mock usage
        
    try:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            database=os.environ.get("DB_NAME", "gemini_bingo"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD", "postgres"),
            port=os.environ.get("DB_PORT", "5432")
        )
        return conn
    except Exception as e:
        print(f"DB Connection Error: {e}")
        return None

def mark_event_tool(room_id: int, event_text: str):
    """
    Marks a Bingo event as 'triggered' (happened) in the game room.
    
    Args:
        room_id: The ID of the room.
        event_text: The text of the event that occurred (e.g., "Touchdown", "Fumble").
        
    Returns:
        dict: A status message indicating success or failure.
    """
    print(f"🔧 Tool Call: mark_event_tool(room_id={room_id}, event_text='{event_text}')")
    
    # In a real app with shared state, we'd import the MOCK_STORE from app.py
    # or rely on the DB. specific to the 'app.py' context.
    # For now, we will handle the logic assuming this is called FROM app.py context
    # or we construct a standalone handler.
    
    # OPTION: We can define this INSIDE app.py to share MOCK_STORE scope easily.
    # But for separation, let's keep it here and assume simpler DB access
    # OR simpler: Return the action to the caller (app.py) to execute.
    
    # ACTUALLY: The best way with the SDK is to pass the function itself.
    # So I will define the logic here, but it might need to access app state.
    
    # Let's try to connect to DB.
    conn = get_db_connection()
    if not conn:
        # Fallback to Mock / Print for now if no DB (since we are using MOCK_STORE in app.py)
        # If we are using MOCK_STORE, this external file can't easily see it without circular imports.
        # STRATEGY: Define the tool schema here, but implement the logic in app.py
        # REVISION: I will write this file as a module to be imported by app.py, 
        # but the actual implementation might need to be wrapped in app.py to access MOCK_STORE.
        return {"status": "mock_db_update_needed", "event": event_text}

    try:
        cur = conn.cursor()
        
        # 1. Get current events
        cur.execute("SELECT events_json FROM room WHERE id = %s", (room_id,))
        res = cur.fetchone()
        if not res:
            return {"status": "error", "message": "Room not found"}
            
        r_events = res[0] # real DB returns list/tuple
        
        # 2. Update status
        updated = False
        new_events = []
        for e in r_events:
            if e['text'] == event_text and not e.get('triggered', False):
                e['triggered'] = True
                updated = True
            new_events.append(e)
            
        if updated:
            cur.execute("UPDATE room SET events_json = %s WHERE id = %s", (json.dumps(new_events), room_id))
            conn.commit()
            print(f"✅ Event marked in DB: {event_text}")
            return {"status": "success", "message": f"Marked '{event_text}' as triggered."}
        else:
            return {"status": "ignored", "message": f"Event '{event_text}' already triggered or not found."}
            
    except Exception as e:
        print(f"Error in mark_event_tool: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        if conn:
            cur.close()
            conn.close()
