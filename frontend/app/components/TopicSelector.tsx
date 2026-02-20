"use client";

import { Globe, Car } from "lucide-react";
import { cn } from "@/lib/utils";

export type LegalTopic = "general" | "parking_ticket";

interface TopicOption {
  value: LegalTopic;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const TOPICS: TopicOption[] = [
  { value: "general", label: "General", icon: Globe },
  { value: "parking_ticket", label: "Parking Ticket", icon: Car },
];

interface TopicSelectorProps {
  selectedTopic: LegalTopic;
  onTopicChange: (topic: LegalTopic) => void;
  className?: string;
}

export function TopicSelector({
  selectedTopic,
  onTopicChange,
  className,
}: TopicSelectorProps) {
  return (
    <div className={cn("space-y-3", className)}>
      <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
        Legal Topic
      </div>

      <div className="flex flex-wrap gap-2">
        {TOPICS.map((topic) => {
          const isActive = selectedTopic === topic.value;
          return (
            <button
              key={topic.value}
              onClick={() => onTopicChange(topic.value)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer border",
                isActive
                  ? "bg-white border-slate-300 text-slate-900 shadow-sm"
                  : "bg-transparent border-transparent text-slate-400 hover:text-slate-600 hover:bg-slate-50"
              )}
            >
              <topic.icon
                className={cn(
                  "h-3.5 w-3.5 transition-colors",
                  isActive ? "text-slate-700" : "text-slate-400"
                )}
              />
              <span>{topic.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
