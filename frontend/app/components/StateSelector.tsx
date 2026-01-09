"use client";

import { useState } from "react";

const STATES = [
  { code: "VIC", name: "Victoria" },
  { code: "NSW", name: "New South Wales" },
  { code: "QLD", name: "Queensland" },
  { code: "SA", name: "South Australia" },
  { code: "WA", name: "Western Australia" },
  { code: "TAS", name: "Tasmania" },
  { code: "NT", name: "Northern Territory" },
  { code: "ACT", name: "Australian Capital Territory" },
];

interface StateSelectorProps {
  selectedState: string | null;
  onStateChange: (state: string) => void;
}

export function StateSelector({ selectedState, onStateChange }: StateSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);

  const selectedStateName = STATES.find((s) => s.code === selectedState)?.name;

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition text-sm"
      >
        <span className="text-slate-500">📍</span>
        <span className={selectedState ? "text-slate-800" : "text-slate-400"}>
          {selectedStateName || "Select your state"}
        </span>
        <svg
          className={`w-4 h-4 text-slate-400 transition ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-56 bg-white border border-slate-200 rounded-lg shadow-lg z-50">
          {STATES.map((state) => (
            <button
              key={state.code}
              onClick={() => {
                onStateChange(state.code);
                setIsOpen(false);
              }}
              className={`w-full text-left px-4 py-2 text-sm hover:bg-slate-50 first:rounded-t-lg last:rounded-b-lg ${
                selectedState === state.code ? "bg-blue-50 text-blue-700" : "text-slate-700"
              }`}
            >
              <span className="font-medium">{state.code}</span>
              <span className="text-slate-500 ml-2">- {state.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
