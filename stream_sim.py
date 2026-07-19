import os
import time
import argparse
import subprocess
import requests
from pathlib import Path

def stream_simulation(video_path, room_id, api_url="http://localhost:5001"):
    """
    Simulates a live stream by cutting a video into 30s chunks 
    and uploading them to the backend analyzer.
    """
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return

    print(f"Starting Stream Simulation for Room {room_id}")
    print(f"Source: {video_path}")
    print(f"Target: {api_url}/api/room/{room_id}/analyze")
    
    chunk_duration = 30
    current_time = 0
    chunk_index = 0
    
    # Get total duration
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            print("Failed to get video duration.")
            return

        total_duration = float(result.stdout.strip())
        print(f"Total Duration: {total_duration:.2f} seconds")
    except Exception as e:
        print(f"Error getting duration: {e}")
        return

    # WAIT FOR START
    print("Waiting for Host to Start Game...")
    while True:
        try:
            r = requests.get(f"{api_url}/api/room/{room_id}")
            if r.status_code == 200:
                status = r.json().get("room", {}).get("status")
                if status == "playing":
                    print("Game Started! Stream beginning...")
                    break
            time.sleep(2)
        except:
             time.sleep(2)

    while current_time < total_duration:
        chunk_filename = f"chunk_{chunk_index}.mp4"
        
        print(f"\n--- Processing Chunk {chunk_index} ({current_time}s - {current_time + chunk_duration}s) ---")
        
        # Cut chunk
        # ffmpeg -i input.mp4 -ss 00:00:30 -t 30 -c copy output.mp4
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-ss", str(current_time),
            "-t", str(chunk_duration),
            "-c:v", "libx264", "-c:a", "aac", # Re-encode to ensure compatibility
             chunk_filename
        ]
        
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            print(f"Chunk {chunk_index} created.")
            
            # Upload
            with open(chunk_filename, "rb") as f:
                print("Uploading to Referee...")
                response = requests.post(
                    f"{api_url}/api/room/{room_id}/analyze",
                    files={"video": f}
                )
                
            if response.status_code == 200:
                data = response.json()
                found = data.get("found_events", [])
                if found:
                     print(f"🎉 EVENTS DETECTED: {found}")
                else:
                     print("No events detected.")
            else:
                print(f"Upload failed: {response.text}")
                
        except Exception as e:
            print(f"Error processing chunk: {e}")
            
        # Cleanup
        if os.path.exists(chunk_filename):
            os.remove(chunk_filename)
            
        # Move time forward
        current_time += chunk_duration
        chunk_index += 1
        
        # Wait to simulate real-time (optional, maybe speed it up)
        print("Waiting 10s before next chunk (simulating buffer)...")
        time.sleep(10)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate a live stream for Gemini Bingo")
    parser.add_argument("video_path", help="Path to the video file")
    parser.add_argument("--room", required=True, help="Room ID to stream to")
    parser.add_argument("--api", default="http://localhost:5001", help="Backend API URL")
    
    args = parser.parse_args()
    stream_simulation(args.video_path, args.room, args.api)
