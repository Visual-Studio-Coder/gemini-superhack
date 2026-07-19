#!/usr/bin/env python3
"""
Quick test script to verify Gemini can analyze the demo video
and detect events from our hardcoded list.
"""

import os
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("backend/.env")

from google import genai
from google.genai import types

# Setup
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("❌ No GEMINI_API_KEY found in backend/.env")
    exit(1)

client = genai.Client(api_key=API_KEY)

# Demo video and events
VIDEO_URL = "https://youtu.be/7T9aM-rU1E0"
DEMO_EVENTS = [
    "Texas A&M Kickoff", "Restrepo Return", "Parish Carry", "Miami Punt",
    "Daniels Rush", "Weigman Touchdown", "A&M Extra Point", "A&M Kickoff",
    "Parish First Down", "Holding Penalty"
]  # First 10 events (should happen in first ~2 mins)

def download_first_30s():
    """Download first 30 seconds of video directly"""
    output = Path("test_clip_30s.mp4")
    
    if output.exists():
        print(f"✅ Using existing clip: {output}")
        return output
    
    print(f"📥 Downloading ONLY first 30s of {VIDEO_URL}...")
    
    # Use --download-sections to only grab first 30 seconds (video only, no audio issues)
    subprocess.run([
        "yt-dlp", 
        "--download-sections", "*0-30",
        "-f", "232",  # Video only (720p) - avoids audio stream issues
        "-o", str(output), 
        VIDEO_URL, 
        "--no-warnings"
    ], check=True)
    
    print(f"✅ Created: {output}")
    return output

def analyze_with_gemini(video_path: Path):
    """Upload video and ask Gemini to detect events"""
    print(f"\n🤖 Uploading to Gemini...")
    
    with open(video_path, "rb") as f:
        video_asset = client.files.upload(file=f, config={"mime_type": "video/mp4"})
    
    # Wait for processing
    print("⏳ Processing video...")
    while video_asset.state.name == "PROCESSING":
        time.sleep(2)
        video_asset = client.files.get(name=video_asset.name)
        print(f"   State: {video_asset.state.name}")
    
    if video_asset.state.name == "FAILED":
        print("❌ Video processing failed!")
        return
    
    print("✅ Video ready!")
    
    # Build prompt
    prompt = f"""
    You are an NFL referee watching this football game clip.
    
    Here is a list of possible Bingo events:
    {DEMO_EVENTS}
    
    Watch the video carefully. Which of these events ACTUALLY HAPPEN in this clip?
    
    For each event you detect, explain briefly what you saw that confirms it.
    Be specific about timestamps if possible.
    
    Output format:
    DETECTED: [event name] - [brief explanation]
    
    If an event doesn't happen, don't mention it.
    """
    
    print("\n🔍 Asking Gemini to analyze...")
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[video_asset, prompt]
    )
    
    print("\n" + "="*60)
    print("🎯 GEMINI'S ANALYSIS:")
    print("="*60)
    print(response.text)
    print("="*60)
    
    # Cleanup
    try:
        client.files.delete(name=video_asset.name)
    except:
        pass

if __name__ == "__main__":
    print("🏈 Super Bowl Bingo - Video Analysis Test")
    print("="*50)
    
    video = download_first_30s()
    analyze_with_gemini(video)
    
    print("\n✅ Test complete!")
