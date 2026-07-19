"use client";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { BingoBoard } from "@/components/BingoBoard";
import { VideoUploader } from "@/components/VideoUploader";

interface BingoEvent {
  text: string;
  triggered: boolean;
  status?: string; // pending, approved, rejected
}

interface Player {
  id: number;
  username: string;
  points: number;
  current_board: BingoEvent[];
}

interface Room {
  id: number;
  join_code: string;
  status: string;
  youtube_id?: string;
  video_start_time?: number;  // Unix timestamp when video was started
  events_json: any[];
}

export default function RoomPage() {
  const { id } = useParams();
  const router = useRouter();
  const [board, setBoard] = useState<BingoEvent[]>([]);
  const [roomStatus, setRoomStatus] = useState("waiting");
  const [joinCode, setJoinCode] = useState("");
  const [isHost, setIsHost] = useState(false);
  const [players, setPlayers] = useState<Player[]>([]);
  const [room, setRoom] = useState<Room | null>(null);
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [analyzing, setAnalyzing] = useState(false);

  // Debug Terminal State
  const [logs, setLogs] = useState<string[]>([]);
  const [showLogs, setShowLogs] = useState(false);
  const [syncTrigger, setSyncTrigger] = useState(0); // Used to force re-render of iframe for sync
  const [debugLogs, setDebugLogs] = useState<string[]>([]);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Poll for Debug Logs (Host Only)
  useEffect(() => {
    if (!isHost) return;

    const fetchLogs = async () => {
      try {
        // In a real app, we'd filter by Room ID or have a dedicated socket
        const res = await fetch(`${API_URL}/api/debug/logs`);
        if (res.ok) {
          const data = await res.json();
          // Simple filter for this room if possible, but logs are global in this hackathon setup
          setDebugLogs(data.logs || []);
        }
      } catch (e) {
        console.error("Log fetch error", e);
      }
    }

    const interval = setInterval(fetchLogs, 3000);
    return () => clearInterval(interval);
  }, [isHost]);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [debugLogs]);
  // Sync Video every 60 seconds
  useEffect(() => {
    if (!room?.youtube_id) return;
    const interval = setInterval(() => {
      console.log("⏰ Resyncing Video Time...");
      setSyncTrigger(prev => prev + 1);
    }, 60000); // 60 seconds
    return () => clearInterval(interval);
  }, [room?.youtube_id]);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001";

  // Polling for Room State
  const fetchRoomState = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/room/${id}`);
      if (res.status === 404) {
        alert("Room expired or not found. Redirecting to home.");
        router.push("/");
        return;
      }
      if (res.ok) {
        const data = await res.json();
        console.log("ROOM DATA:", data);
        setRoom(data.room);
        setRoomStatus(data.room.status);
        setJoinCode(data.room.join_code);
        setPlayers(data.players || []);

        // Find current user's board
        const myUsername = sessionStorage.getItem("username");
        console.log("MY USERNAME:", myUsername, "PLAYERS:", data.players);
        const storedIsHost = sessionStorage.getItem("isHost") === "true";
        setIsHost(storedIsHost);

        const me = data.players.find((p: any) => p.username === myUsername);
        console.log("ME:", me);
        if (me) {
          // Parse board if string
          const b = typeof me.current_board === "string"
            ? JSON.parse(me.current_board)
            : me.current_board;
          console.log("BOARD:", b);
          setBoard(b || []);
        }
      }
    } catch (e) {
      console.error(e);
    }
  }, [id, API_URL]);

  // Polling for Logs
  const fetchLogs = useCallback(async () => {
    if (!showLogs) return;
    try {
      const res = await fetch(`${API_URL}/api/debug/logs`);
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || []);
      }
    } catch (e) {
      console.error(e);
    }
  }, [showLogs, API_URL]);

  useEffect(() => {
    fetchRoomState();
    const interval = setInterval(fetchRoomState, 2000);
    return () => clearInterval(interval);
  }, [fetchRoomState]);

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 2000);
    return () => clearInterval(interval);
  }, [fetchLogs]);


  const startGame = async () => {
    try {
      await fetch(`${API_URL}/api/room/${id}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "playing" })
      });
    } catch (e) { console.error(e); }
  };

  const setVideo = async () => {
    if (!youtubeUrl) return alert("Enter a YouTube URL");

    try {
      // Call the new video sync endpoint
      const res = await fetch(`${API_URL}/api/room/${id}/video`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ youtube_url: youtubeUrl })
      });

      if (!res.ok) {
        const err = await res.json();
        alert(err.error || "Failed to set video");
      } else {
        console.log("Video set successfully!");
      }
    } catch (e) {
      console.error(e);
      alert("Error setting video");
    }
  };

  const handleSquareClick = async (square: BingoEvent) => {
    if (roomStatus !== "playing") return;
    if (square.status === "approved" || square.status === "rejected") return;

    // Optimistic Update
    const newBoard = board.map(s =>
      s.text === square.text ? { ...s, status: "pending" } : s
    );
    setBoard(newBoard);

    // Call API
    const myPlayer = players.find(p => p.username === sessionStorage.getItem("username"));
    if (!myPlayer) return;

    try {
      await fetch(`${API_URL}/api/player/${myPlayer.id || 1}/board`, { // Fix ID mapping
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event_text: square.text })
      });
    } catch (e) {
      console.error(e);
    }
  };

  // Memoize the iframe URL so it ONLY updates when syncTrigger fires (every 60s)
  // causing a re-sync. Otherwise, it stays stable despite re-renders.
  const iframeSrc = useMemo(() => {
    if (!room?.youtube_id) return "";

    const startOffset = room.video_start_time
      ? Math.max(0, Math.floor(Date.now() / 1000) - room.video_start_time)
      : 0;

    return `https://www.youtube.com/embed/${room.youtube_id}?autoplay=1&controls=1&mute=0&disablekb=0&modestbranding=1&rel=0&iv_load_policy=3&showinfo=0&start=${startOffset}`;
  }, [room?.youtube_id, room?.video_start_time, syncTrigger]);

  return (
    <div className="min-h-screen bg-green-950 text-white font-sans overflow-hidden">
      {/* Field Texture */}
      <div className="fixed inset-0 pointer-events-none opacity-5"
        style={{ backgroundImage: 'linear-gradient(transparent 95%, rgba(255,255,255,0.7) 95%)', backgroundSize: '100% 120px' }}></div>

      <header className="border-b border-white/10 bg-green-900/50 backdrop-blur-sm p-4 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-black italic tracking-tighter text-yellow-400">GRIDIRON BINGO</h1>
            <p className="text-xs text-green-200">Referee: Gemini AI 3.0</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="bg-black/40 px-4 py-2 rounded-lg border border-white/10">
              <span className="text-xs text-gray-400 block">JOIN CODE</span>
              <span className="font-mono text-xl font-bold tracking-widest text-white">{room?.join_code}</span>
            </div>
            <div className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${roomStatus === "playing" ? "bg-red-600 animate-pulse" : "bg-yellow-600"}`}>
              {roomStatus}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-4 md:p-8 grid md:grid-cols-12 gap-8 relative z-10 pb-32">

        {/* Left Col: Players & Controls (3 cols) */}
        <div className="md:col-span-3 space-y-6">
          <div className="bg-black/20 backdrop-blur-sm rounded-xl p-6 border border-white/10">
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
              <span>📋</span> Roster
            </h2>
            <div className="space-y-3">
              {players.map((p) => (
                <div key={p.username} className="flex justify-between items-center bg-white/5 p-3 rounded-lg">
                  <span className="font-medium">{p.username}</span>
                  <span className="font-mono text-yellow-400 font-bold">{p.points} opts</span>
                </div>
              ))}
            </div>
          </div>

          {isHost && roomStatus === "waiting" && (
            <button
              onClick={startGame}
              className="w-full bg-yellow-500 hover:bg-yellow-400 text-black font-black py-4 rounded-xl text-lg uppercase shadow-lg transform active:scale-95 transition-all"
            >
              Start Game
            </button>
          )}

          {/* Host Debug Console */}
          {isHost && (
            <div className="bg-black/80 backdrop-blur-sm rounded-xl p-4 border border-white/10 text-xs font-mono h-48 flex flex-col">
              <div className="flex justify-between items-center mb-2 border-b border-white/10 pb-1">
                <span className="text-green-400 font-bold">TERMINAL &gt;_ Referee Logs</span>
                <span className="text-gray-500 animate-pulse">● Live</span>
              </div>
              <div className="flex-1 overflow-y-auto space-y-1 custom-scrollbar">
                {debugLogs.length === 0 ? (
                  <span className="text-gray-600 italic">Waiting for system output...</span>
                ) : (
                  debugLogs.map((log, i) => (
                    <div key={i} className="break-words">
                      <span className="text-blue-500 mr-2">[{log.split(' - ')[0] || 'SYSTEM'}]</span>
                      <span className="text-gray-300">{log.split(' - ').slice(1).join(' - ') || log}</span>
                    </div>
                  ))
                )}
                <div ref={logsEndRef} />
              </div>
            </div>
          )}
        </div>

        {/* Center: The Board (6 cols) */}
        <div className="md:col-span-6 flex flex-col items-center">
          <div className="mb-4 flex justify-between w-full items-end">
            <h2 className="text-2xl font-bold italic">My Playbook</h2>
            <span className="text-sm text-green-300">Tap a play to claim it!</span>
          </div>

          {/* Custom Bingo Board Rendering for Theme */}
          <div className="grid grid-cols-5 gap-2 md:gap-3 bg-green-800 p-3 md:p-4 rounded-xl border-4 border-yellow-600 shadow-2xl w-full aspect-square max-w-[600px]">
            {board.map((square, i) => (
              <button
                key={i}
                onClick={() => handleSquareClick(square)}
                disabled={square.status === "approved" || roomStatus !== "playing"}
                className={`
                            relative flex items-center justify-center p-1 md:p-2 rounded-lg text-xs md:text-sm font-bold text-center leading-tight transition-all duration-200 aspect-square select-none
                            ${square.text === "FREE SPACE"
                    ? "bg-yellow-500 text-black border-2 border-white scale-105 z-10 shadow-lg"
                    : square.status === "approved"
                      ? "bg-yellow-500/90 text-black border-2 border-yellow-300 shadow-[0_0_15px_rgba(234,179,8,0.5)] transform scale-105 z-10"
                      : square.status === "rejected"
                        ? "bg-red-900/50 text-red-200 border border-red-500/50"
                        : "bg-green-700/50 hover:bg-green-600/80 text-white border border-green-600 hover:border-green-400"
                  }
                        `}
              >
                {square.text}
                {square.status === "pending" && (
                  <div className="absolute inset-0 bg-blue-600/80 flex items-center justify-center rounded-lg animate-pulse z-20">
                    <span className="text-[10px] uppercase font-black text-white tracking-widest">Verifying...</span>
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Right Col: Host Controls / Stream (3 cols) */}
        <div className="md:col-span-3 space-y-6">
          {isHost && (
            <div className="bg-black/20 backdrop-blur-sm rounded-xl p-6 border border-white/10">
              <h2 className="text-lg font-bold mb-4">Game Setup</h2>
              <p className="text-xs text-gray-400 mb-2">Paste YouTube URL of the Game</p>
              <div className="flex gap-2">
                <input
                  className="bg-black/50 border border-white/20 rounded px-3 py-2 w-full text-sm text-white"
                  placeholder="https://youtube.com/..."
                  value={youtubeUrl}
                  onChange={(e) => setYoutubeUrl(e.target.value)}
                />
              </div>
              <button
                onClick={setVideo}
                className="mt-3 w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 rounded text-sm uppercase"
              >
                Set Video
              </button>
            </div>
          )}

          <div className="bg-black border border-zinc-800 rounded-xl aspect-video flex items-center justify-center relative overflow-hidden shadow-2xl">
            {room?.youtube_id ? (
              <iframe
                width="100%"
                height="100%"
                src={iframeSrc}
                title="Game Stream"
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              // Removed pointer-events-none so users can click to start/unmute if autoplay fails
              // The 60s periodic sync will correct any drift if they pause
              ></iframe>
            ) : (
              <div className="text-center p-6">
                <div className="text-4xl mb-2">📺</div>
                <p className="text-zinc-500 text-sm">Waiting for Start...</p>
              </div>
            )}

            {analyzing && (
              <div className="absolute top-4 right-4 bg-red-600 text-white px-3 py-1 rounded-full text-xs font-bold animate-pulse flex items-center gap-2">
                <span className="w-2 h-2 bg-white rounded-full"></span> LIVE
              </div>
            )}
          </div>
        </div>
      </main >

      {/* AI REFEREE FEED - Shows what Gemini has detected */}
      {isHost && roomStatus === "playing" && (
        <div className="max-w-7xl mx-auto px-4 pb-24">
          <div className="bg-gradient-to-r from-green-900/50 to-emerald-900/50 p-6 rounded-xl border-2 border-green-500/50 shadow-lg shadow-green-500/20">
            <h3 className="text-2xl font-black mb-4 flex items-center gap-3 text-green-400">
              <span className="text-3xl">🤖</span> AI REFEREE DETECTIONS
              <span className="ml-auto text-sm font-normal bg-green-500/20 px-3 py-1 rounded-full animate-pulse">LIVE</span>
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {room?.events_json && Array.isArray(room.events_json) &&
                room.events_json.map((e: any, i: number) => (
                  <div
                    key={i}
                    className={`p-3 rounded-lg text-center transition-all duration-500 ${e.triggered
                      ? 'bg-green-500 text-white font-bold scale-105 shadow-lg shadow-green-500/50'
                      : 'bg-white/5 text-white/30'
                      }`}
                  >
                    <span className="text-lg">{e.triggered ? '✅' : '⏳'}</span>
                    <p className="text-xs mt-1 truncate">{e.text}</p>
                  </div>
                ))
              }
            </div>
            {(!room?.events_json || !Array.isArray(room.events_json) || room.events_json.every((e: any) => !e.triggered)) && (
              <p className="text-center text-white/30 italic mt-4">Waiting for Gemini to detect events...</p>
            )}
          </div>
        </div>
      )}

      {/* Debug Console */}
      < div className={`fixed bottom-0 left-0 right-0 bg-black/95 border-t border-green-500/30 p-4 transition-all duration-300 z-50 font-mono text-xs ${showLogs ? 'h-64' : 'h-10'}`
      }>
        <button
          onClick={() => setShowLogs(!showLogs)}
          className="absolute top-0 right-4 -mt-3 bg-green-900/80 hover:bg-green-700 text-green-100 text-[10px] uppercase font-bold tracking-wider px-3 py-1 rounded-full border border-green-500/30"
        >
          {showLogs ? 'Hide Terminal' : 'Show Referee Logs'}
        </button>

        {
          showLogs && (
            <div className="h-full overflow-y-auto space-y-1 pb-4">
              <div className="text-green-500 font-bold mb-2">root@gemini-referee:~$ tail -f game.events</div>
              {logs.map((log, i) => (
                <div key={i} className="text-green-400/80 border-b border-white/5 pb-1">
                  {log}
                </div>
              ))}
            </div>
          )
        }
        {
          !showLogs && (
            <div className="flex items-center gap-2 h-full opacity-50">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
              <span className="text-green-500/50">System Online</span>
            </div>
          )
        }
      </div >

    </div >
  );
}
