"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../lib/utils";

interface VideoUploaderProps {
    onUpload: (file: File) => Promise<void>;
    isAnalyzing: boolean;
}

export function VideoUploader({ onUpload, isAnalyzing }: VideoUploaderProps) {
    const [dragActive, setDragActive] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            onUpload(e.dataTransfer.files[0]);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        e.preventDefault();
        if (e.target.files && e.target.files[0]) {
            onUpload(e.target.files[0]);
        }
    };

    return (
        <div className="w-full max-w-md">
            <div
                className={cn(
                    "relative h-32 flex flex-col items-center justify-center border-2 border-dashed rounded-xl transition-all duration-300",
                    dragActive
                        ? "border-purple-500 bg-purple-500/10 scale-105"
                        : "border-gray-600 bg-black/20 hover:border-purple-500/50 hover:bg-black/40",
                    isAnalyzing ? "opacity-50 pointer-events-none" : "cursor-pointer"
                )}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
            >
                <input
                    ref={inputRef}
                    type="file"
                    className="hidden"
                    accept="video/*"
                    onChange={handleChange}
                />

                <AnimatePresence mode="wait">
                    {isAnalyzing ? (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex flex-col items-center gap-2"
                        >
                            <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin" />
                            <p className="text-purple-300 font-medium">Gemini 1.5 Pro Analyzing...</p>
                        </motion.div>
                    ) : (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex flex-col items-center gap-1"
                        >
                            <p className="text-gray-300 font-medium">Upload 30s Video Clip</p>
                            <p className="text-xs text-gray-500">Drag & drop or Click to Browse</p>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
