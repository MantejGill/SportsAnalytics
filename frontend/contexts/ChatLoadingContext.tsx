"use client";

import React, { createContext, useContext, useState, type ReactNode } from "react";

interface ChatLoadingContextValue {
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
}

const ChatLoadingContext = createContext<ChatLoadingContextValue>({
  isLoading: false,
  setIsLoading: () => {},
});

export function ChatLoadingProvider({ children }: { children: ReactNode }) {
  const [isLoading, setIsLoading] = useState(false);

  return (
    <ChatLoadingContext.Provider value={{ isLoading, setIsLoading }}>
      {children}
    </ChatLoadingContext.Provider>
  );
}

export function useChatLoading() {
  const context = useContext(ChatLoadingContext);
  if (!context) {
    throw new Error("useChatLoading must be used within ChatLoadingProvider");
  }
  return context;
}
