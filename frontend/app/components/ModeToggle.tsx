"use client";

import { MessageCircle, Briefcase } from "lucide-react";
import { useMode, AppMode } from "../contexts/ModeContext";
import { cn } from "@/lib/utils";

interface ModeToggleProps {
  className?: string;
}

export function ModeToggle({ className }: ModeToggleProps) {
  const { mode, setMode } = useMode();

  const handleToggle = (newMode: AppMode) => {
    if (newMode !== mode) {
      setMode(newMode);
    }
  };

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
        Mode
      </div>

      {/* Pill Toggle */}
      <div className="relative flex p-1 bg-slate-100 rounded-lg">
        {/* Sliding background indicator */}
        <div
          className={cn(
            "absolute top-1 bottom-1 w-[calc(50%-4px)] rounded-md transition-all duration-300 ease-out",
            mode === "chat"
              ? "left-1 bg-white shadow-sm"
              : "left-[calc(50%+2px)] bg-white shadow-sm"
          )}
        />

        {/* Chat Mode Button */}
        <button
          onClick={() => handleToggle("chat")}
          className={cn(
            "relative z-10 flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-md text-sm font-medium transition-colors duration-200 cursor-pointer",
            mode === "chat"
              ? "text-primary"
              : "text-slate-500 hover:text-slate-700"
          )}
        >
          <MessageCircle className="h-4 w-4" />
          <span>Chat</span>
        </button>

        {/* Analysis Mode Button */}
        <button
          onClick={() => handleToggle("analysis")}
          className={cn(
            "relative z-10 flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-md text-sm font-medium transition-colors duration-200 cursor-pointer",
            mode === "analysis"
              ? "text-primary"
              : "text-slate-500 hover:text-slate-700"
          )}
        >
          <Briefcase className="h-4 w-4" />
          <span>Analysis</span>
        </button>
      </div>

      {/* Mode Description */}
      <p className="text-xs text-slate-500">
        {mode === "chat"
          ? "Casual Q&A for quick legal questions"
          : "Guided intake for deep case analysis"}
      </p>
    </div>
  );
}
