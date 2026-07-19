import requests
import json
import time

BASE_URL = "http://localhost:5001/api"

def debug_create_room():
    print("Creating Room...")
    try:
        res = requests.post(f"{BASE_URL}/create-room", json={"username": "DebugBot", "context": "Super Bowl"})
        if res.status_code != 200:
            print(f"Status Code: {res.status_code}")
            print(f"Response: {res.text}")
            # Continue anyway if we got JSON
            
        data = res.json()
        player_id = data['player_id']
        room_id = data['room_id']
        print(f"Room {room_id} Created. Player {player_id}.")
        
        # Get Room State to check board
        res = requests.get(f"{BASE_URL}/room/{room_id}")
        room_data = res.json()
        
        # Find player
        player = next(p for p in room_data['players'] if p['id'] == player_id)
        board = json.loads(player['current_board']) if isinstance(player['current_board'], str) else player['current_board']
        
        print("\n--- BOARD STATUS SAMPLE ---")
        for i, cell in enumerate(board[:5]):
            print(f"Cell {i}: {cell.get('text')} -> STATUS: {cell.get('status')}")
            
        # Check for 'pending'
        pending = [c for c in board if c.get('status') == 'pending']
        if pending:
            print(f"\n❌ ERROR: Found {len(pending)} PENDING cells!")
        else:
            print("\n✅ SUCCESS: No pending cells found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_create_room()
