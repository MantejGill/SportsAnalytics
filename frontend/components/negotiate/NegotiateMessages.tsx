"use client";

import React, { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { useNegotiationStore } from "@/lib/stores/negotiationStore";
import { Badge } from "@/components/ui/badge";
import { Bot, User } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
}

interface NegotiateMessagesProps {
  messages: Message[];
  inProgress: boolean;
  children?: React.ReactNode;
}

function NegotiationStatusInline() {
  const status = useNegotiationStore((s) => s.status);
  const currentRound = useNegotiationStore((s) => s.currentRound);
  const activeAgent = useNegotiationStore((s) => s.activeAgent);
  const agents = useNegotiationStore((s) => s.agents);

  if (status === "idle") return null;

  const active = agents.find((a) => a.id === activeAgent);

  return (
    <div className="mx-2 my-1 rounded-lg border border-border bg-card/50 p-3 text-xs">
      <div className="flex items-center gap-2">
        <Badge
          variant={
            status === "negotiating"
              ? "default"
              : status === "accepted"
                ? "success"
                : "destructive"
          }
        >
          {status === "negotiating"
            ? `Round ${currentRound}`
            : status.replace("_", " ").toUpperCase()}
        </Badge>
        {active && (
          <span className="text-muted-foreground">
            Active: <span className="text-foreground">{active.name}</span>
          </span>
        )}
      </div>
    </div>
  );
}

export default function NegotiateMessages({
  messages,
  inProgress,
  children,
}: NegotiateMessagesProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, inProgress]);

  return (
    <div ref={scrollRef} className="flex flex-1 flex-col overflow-y-auto p-4">
      {messages.length === 0 && (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
          <div className="rounded-full bg-primary/10 p-4">
            <Bot className="h-8 w-8 text-primary" />
          </div>
          <h3 className="text-lg font-semibold">Auto-Negotiate Assistant</h3>
          <p className="max-w-xs text-sm text-muted-foreground">
            Start a contract negotiation by telling me the player name, club,
            and budget. I will orchestrate the multi-agent negotiation for you.
          </p>
        </div>
      )}

      {messages.map((message) => (
        <div
          key={message.id}
          className={cn(
            "mb-4 flex gap-3 slide-in",
            message.role === "user" ? "flex-row-reverse" : "flex-row"
          )}
        >
          <div
            className={cn(
              "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
              message.role === "user"
                ? "bg-negotiate-club/20 text-negotiate-club"
                : "bg-primary/20 text-primary"
            )}
          >
            {message.role === "user" ? (
              <User className="h-4 w-4" />
            ) : (
              <Bot className="h-4 w-4" />
            )}
          </div>
          <div
            className={cn(
              "max-w-[80%] rounded-lg px-4 py-2 text-sm",
              message.role === "user"
                ? "bg-negotiate-club/10 text-foreground"
                : "bg-muted text-foreground"
            )}
          >
            <p className="whitespace-pre-wrap">{message.content}</p>
          </div>
        </div>
      ))}

      <NegotiationStatusInline />

      {inProgress && (
        <div className="mb-4 flex gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/20 text-primary">
            <Bot className="h-4 w-4" />
          </div>
          <div className="flex items-center gap-1 rounded-lg bg-muted px-4 py-2">
            <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:0ms]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:150ms]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:300ms]" />
          </div>
        </div>
      )}

      {children}
    </div>
  );
}
