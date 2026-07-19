
import os
import json
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv("backend/.env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
print(f"API Key found: {bool(GEMINI_API_KEY)}")

client = genai.Client(api_key=GEMINI_API_KEY)

# Mock Tool
def mark_event_tool(room_id: int, event_text: str):
    print(f"\n✅ SYSTEM: mark_event_tool CALLED!")
    print(f"   Room: {room_id}")
    print(f"   Event: {event_text}")
    print("   (In the real app, this would update the DB and notify players)\n")
    return {"status": "success", "event": event_text}

def run_test():
    # 1. Download a known video clip (short)
    # Using a sample NFL play or similar would be ideal, but for copyright/availability 
    # let's use a generic 'American Football' clip if available, or just a sample video.
    # Actually, I'll use a small dummy video generation or a known URL.
    # Let's try downloading a very short clip using the same logic as backend (yt-dlp)
    # This is a specific verifiable clip (e.g. 5 sec of football)
    
    # "American Football - Touchdown" example from valid creative commons or similar
    # Using a placeholder URL for testing. 
    # NOTE: The user asked for a "test video". 
    # I will download a specific short clip.
    # "American Football for Beginners" - More likely to be available than NFL clips
    youtube_url = "https://www.youtube.com/watch?v=3t6hM5tRlfA" 
    
    print(f"Downloading test video: {youtube_url}...")
    import subprocess
    chunk_name = "test_clip.mp4"
    if os.path.exists(chunk_name):
        os.remove(chunk_name)
    
    # Try downloading
    try:
        subprocess.run([
            ".venv/bin/yt-dlp", "-f", "best[ext=mp4]", 
            "--force-overwrites", 
            "-o", chunk_name, 
            youtube_url
        ], check=True)
    except Exception as e:
        print(f"Download failed: {e}. Generating dummy video for API test...")
        # Generate 5s dummy video
        subprocess.run([
            "ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=5:size=1280x720:rate=30", 
            "-c:v", "libx264", chunk_name
        ], check=True)

    # Trim/Process (if downloaded)
    # ffmpeg -i test_clip.mp4 -t 15 -c copy test_trim.mp4
    if os.path.exists(chunk_name):
        subprocess.run([
            "ffmpeg", "-y", "-i", chunk_name, "-t", "30", "-c:v", "copy", "-c:a", "copy", "test_trim.mp4"
        ], stderr=subprocess.DEVNULL)
    else:
        print("Fatal: Could not produce video.")
        return
    
    print("Video ready. Uploading to Gemini...")
    
    with open("test_trim.mp4", "rb") as f:
        video_asset = client.files.upload(file=f, config={'mime_type': 'video/mp4'})

    while video_asset.state.name == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(1)
        video_asset = client.files.get(name=video_asset.name)
    print(" Uploaded!")

    # Define events we EXPECT (based on the video)
    # The video is "Julian Edelman's Miraculous Catch"
    events = [
        "Touchdown",
        "Interception",
        "Amazing Catch", # Expected
        "Fumble",
        "Field Goal"
    ]
    
    print(f"\nAsking Gemini to find: {events}")
    
    prompt = f"""
    You are an expert NFL Referee observing a game. 
    Watch this video clip closely.
    
    Here is a list of Bingo events that players are waiting for:
    {json.dumps(events)}
    
    Your job is to DETECT if any of these specific events happen in this clip.
    If an event happens, you MUST call the `mark_event_tool` function with:
    - room_id: 999
    - event_text: The exact text of the event from the list.
    
    Only mark events that are CLEARLY visible or audible in this clip.
    If no events from the list occur, simply output "No events detected."
    """
    
    print("\n--- GEMINI THOUGHT PROCESS ---")
    try:
        response = client.models.generate_content(
            model='gemini-3-pro-preview',
            contents=[video_asset, prompt],
            config=types.GenerateContentConfig(
                tools=[mark_event_tool],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False)
            )
        )
        
        # Manually inspect for function calls to print clearly
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                     print(f"🤖 TOOL CALL TRIGGERED: {part.function_call.name}")
                     print(f"   Args: {part.function_call.args}")
        
        print(f"📝 Final Response: {response.text}")
        
    except Exception as e:
        print(f"Error: {e}")
        
    # Cleanup
    try:
        client.files.delete(name=video_asset.name)
    except:
        pass

if __name__ == "__main__":
    run_test()
