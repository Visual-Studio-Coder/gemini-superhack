"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [joinCode, setJoinCode] = useState("");

  // Super Bowl Context default
  const [context, setContext] = useState("Super Bowl LIX: Chiefs vs 49ers");
  // Loading State
  const [isLoading, setIsLoading] = useState(false);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001";

  const createRoom = async () => {
    if (!username) return;
    setIsLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/create-room`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, context }),
      });
      const data = await res.json();

      // Store session info (sessionStorage is PER-TAB, unlike localStorage)
      sessionStorage.setItem("username", username);
      sessionStorage.setItem("isHost", "true");

      if (res.ok) router.push(`/room/${data.room_id}`);
    } catch (e) {
      console.error(e);
      setIsLoading(false);
    }
  };

  const joinRoom = async () => {
    if (!username || !joinCode) return;
    setIsLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/join-room`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, room_code: joinCode }),
      });
      const data = await res.json();

      // Store session info (sessionStorage is PER-TAB, unlike localStorage)
      sessionStorage.setItem("username", username);
      sessionStorage.setItem("isHost", "false");

      if (res.ok) router.push(`/room/${data.room_id}`);
    } catch (e) {
      console.error(e);
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-green-950 flex flex-col items-center justify-center font-sans text-white relative overflow-hidden">
        {/* Field Lines */}
        <div className="fixed inset-0 pointer-events-none opacity-20"
          style={{ backgroundImage: 'linear-gradient(transparent 95%, rgba(255,255,255,0.5) 95%)', backgroundSize: '100% 100px' }}></div>

        <div className="z-10 text-center animate-pulse">
          <div className="text-8xl mb-4">🏈</div>
          <h2 className="text-4xl font-black italic tracking-tighter text-yellow-400 mb-2">SCOUTING PLAYS...</h2>
          <p className="text-green-200 text-lg">Gemini Referee is generating 60 unique events.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-green-900 text-white font-sans selection:bg-yellow-500 selection:text-black">
      {/* Field Lines Pattern */}
      <div className="fixed inset-0 pointer-events-none opacity-10"
        style={{ backgroundImage: 'linear-gradient(transparent 95%, rgba(255,255,255,0.5) 95%)', backgroundSize: '100% 100px' }}></div>

      <main className="relative z-10 container mx-auto px-4 py-16 flex flex-col items-center justify-center min-h-screen">

        <div className="text-center mb-12">
          <h1 className="text-6xl md:text-8xl font-black tracking-tighter mb-4 text-transparent bg-clip-text bg-gradient-to-b from-yellow-400 to-yellow-600 drop-shadow-lg">
            GRIDIRON BINGO
          </h1>
          <p className="text-xl md:text-2xl text-green-100 font-medium opacity-90">
            AI Referee Edition • Super Bowl LIX
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 w-full max-w-4xl">
          {/* Create Room Card */}
          <div className="bg-white/10 backdrop-blur-md border-2 border-white/20 p-8 rounded-2xl shadow-xl hover:bg-white/15 transition-all">
            <h2 className="text-3xl font-bold mb-6 flex items-center gap-3">
              <span className="text-4xl">🏈</span> Host Game
            </h2>
            <input
              type="text"
              placeholder="Your Name (Coach)"
              className="w-full bg-black/40 border border-white/20 rounded-lg px-4 py-3 mb-4 text-white placeholder-white/50 focus:outline-none focus:border-yellow-400 transition-colors"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <input
              type="text"
              placeholder="Game Context (e.g. Super Bowl LIX)"
              className="w-full bg-black/40 border border-white/20 rounded-lg px-4 py-3 mb-6 text-white placeholder-white/50 focus:outline-none focus:border-yellow-400 transition-colors"
              value={context}
              onChange={(e) => setContext(e.target.value)}
            />
            <button
              onClick={createRoom}
              className="w-full bg-yellow-500 hover:bg-yellow-400 text-black font-black py-4 rounded-lg text-xl uppercase tracking-widest shadow-lg transform hover:scale-[1.02] transition-all"
            >
              Kickoff
            </button>
          </div>

          {/* Join Room Card */}
          <div className="bg-black/30 backdrop-blur-md border-2 border-white/10 p-8 rounded-2xl shadow-xl">
            <h2 className="text-3xl font-bold mb-6 flex items-center gap-3">
              <span className="text-4xl">🎫</span> Join Huddle
            </h2>
            <input
              type="text"
              placeholder="Your Name (Rookie)"
              className="w-full bg-black/40 border border-white/20 rounded-lg px-4 py-3 mb-4 text-white placeholder-white/50 focus:outline-none focus:border-green-400 transition-colors"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <input
              type="text"
              placeholder="Room Code (e.g. HUBOGO)"
              className="w-full bg-black/40 border border-white/20 rounded-lg px-4 py-3 mb-6 text-white placeholder-white/50 focus:outline-none focus:border-green-400 transition-colors font-mono uppercase tracking-wider"
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
            />
            <button
              onClick={joinRoom}
              className="w-full bg-green-600 hover:bg-green-500 text-white font-black py-4 rounded-lg text-xl uppercase tracking-widest shadow-lg transform hover:scale-[1.02] transition-all"
            >
              Enter Game
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
