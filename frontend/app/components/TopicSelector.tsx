"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Scale } from "lucide-react";

export type LegalTopic = "general" | "parking_ticket" | "insurance_claim";

const TOPICS = [
  { value: "general" as LegalTopic, label: "General" },
  { value: "parking_ticket" as LegalTopic, label: "Parking Ticket" },
  { value: "insurance_claim" as LegalTopic, label: "Insurance Claim" },
];

interface TopicSelectorProps {
  selectedTopic: LegalTopic;
  onTopicChange: (topic: LegalTopic) => void;
  className?: string;
}

export function TopicSelector({
  selectedTopic,
  onTopicChange,
}: TopicSelectorProps) {
  return (
    <div className="space-y-3">
      <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
        Legal Topic
      </div>
      <Select
        value={selectedTopic}
        onValueChange={(v) => onTopicChange(v as LegalTopic)}
      >
        <SelectTrigger className="w-full h-10">
          <Scale className="mr-2 h-4 w-4 text-muted-foreground" />
          <SelectValue placeholder="Select a topic" />
        </SelectTrigger>
        <SelectContent>
          {TOPICS.map((topic) => (
            <SelectItem key={topic.value} value={topic.value}>
              {topic.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
