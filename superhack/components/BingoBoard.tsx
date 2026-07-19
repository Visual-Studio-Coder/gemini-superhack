"use client";

import { motion } from "framer-motion";
import { cn } from "../lib/utils";

interface BingoEvent {
    text: string;
    triggered: boolean;
}

interface BingoBoardProps {
    events: BingoEvent[];
    onSquareClick?: (index: number) => void;
    isLoading?: boolean;
}

export function BingoBoard({ events, onSquareClick, isLoading }: BingoBoardProps) {
    // Defensive check
    const safeEvents = Array.isArray(events) ? events : [];

    if ((safeEvents.length === 0 && isLoading) || !events) {
        return (
            <div className="grid grid-cols-5 gap-2 w-full max-w-2xl aspect-square p-4">
                {Array.from({ length: 25 }).map((_, i) => (
                    <div key={i} className="bg-white/5 rounded-lg animate-pulse" />
                ))}
            </div>
        );
    }

    return (
        <div className="grid grid-cols-5 gap-3 w-full max-w-2xl bg-black/20 p-6 rounded-2xl backdrop-blur-sm border border-white/10 shadow-2xl">
            {safeEvents.map((event, index) => (
                <motion.div
                    key={index}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: index * 0.02 }}
                    onClick={() => onSquareClick && onSquareClick(index)}
                    className={cn(
                        "aspect-square flex items-center justify-center p-2 text-xs md:text-sm font-medium text-center rounded-lg cursor-pointer transition-all duration-300 relative overflow-hidden group",
                        event.triggered
                            ? "bg-gradient-to-br from-green-500 to-emerald-600 text-white shadow-lg shadow-green-500/30 scale-105 z-10 border border-green-400"
                            : "bg-white/5 hover:bg-white/10 text-gray-300 border border-white/5 hover:border-purple-500/50"
                    )}
                >
                    <span className="relative z-10">{event.text}</span>
                    {event.triggered && (
                        <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            className="absolute inset-0 bg-green-500/20 animate-pulse"
                        />
                    )}
                    <div className="absolute inset-0 bg-gradient-to-br from-white/0 to-white/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                </motion.div>
            ))}
        </div>
    );
}
