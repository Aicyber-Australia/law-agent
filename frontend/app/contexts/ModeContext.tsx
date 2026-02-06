"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";

export type AppMode = "chat" | "analysis";

interface ModeContextValue {
  mode: AppMode;
  setMode: (mode: AppMode) => void;
}

const ModeContext = createContext<ModeContextValue | undefined>(undefined);

const STORAGE_KEY = "auslaw-mode";

export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<AppMode>("chat");
  const [isHydrated, setIsHydrated] = useState(false);

  // Load mode from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "chat" || stored === "analysis") {
      setModeState(stored);
    }
    setIsHydrated(true);
  }, []);

  // Persist mode to localStorage and update data attribute
  const setMode = (newMode: AppMode) => {
    setModeState(newMode);
    localStorage.setItem(STORAGE_KEY, newMode);
  };

  // Update data-mode attribute on document for CSS theming
  useEffect(() => {
    if (isHydrated) {
      document.documentElement.setAttribute("data-mode", mode);
    }
  }, [mode, isHydrated]);

  // Prevent flash of wrong theme during hydration
  if (!isHydrated) {
    return (
      <div data-mode="chat" className="contents">
        {children}
      </div>
    );
  }

  return (
    <ModeContext.Provider value={{ mode, setMode }}>
      {children}
    </ModeContext.Provider>
  );
}

export function useMode() {
  const context = useContext(ModeContext);
  // Return default values during SSR/static generation (context not available)
  if (!context) {
    return {
      mode: "chat" as AppMode,
      setMode: () => {},
    };
  }
  return context;
}
