"use client";

import React, { useEffect, useRef } from "react";
import { cn, formatEUR, formatRound } from "@/lib/utils";
import { useNegotiationStore } from "@/lib/stores/negotiationStore";
import { Badge } from "@/components/ui/badge";
import { Building2, UserRound, Handshake, XCircle } from "lucide-react";

export default function OfferTimeline() {
  const rounds = useNegotiationStore((s) => s.rounds);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [rounds]);

  if (rounds.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center p-8 text-center">
        <Handshake className="mb-3 h-10 w-10 text-muted-foreground/40" />
        <p className="text-sm text-muted-foreground">
          No offers yet. Start a negotiation to see the timeline.
        </p>
      </div>
    );
  }

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
      <div className="relative ml-4 border-l border-border">
        {rounds.map((round, idx) => {
          const isClub = round.side === "club";
          const isAccept = round.action === "ACCEPT";
          const isWalkAway = round.action === "WALK_AWAY";

          return (
            <div key={idx} className="relative mb-6 ml-6 slide-in">
              {/* Dot on the timeline */}
              <div
                className={cn(
                  "absolute -left-[31px] flex h-5 w-5 items-center justify-center rounded-full border-2",
                  isAccept
                    ? "border-negotiate-success bg-negotiate-success/20"
                    : isWalkAway
                      ? "border-negotiate-danger bg-negotiate-danger/20"
                      : isClub
                        ? "border-negotiate-club bg-negotiate-club/20"
                        : "border-negotiate-player bg-negotiate-player/20"
                )}
              >
                {isAccept ? (
                  <Handshake className="h-2.5 w-2.5 text-negotiate-success" />
                ) : isWalkAway ? (
                  <XCircle className="h-2.5 w-2.5 text-negotiate-danger" />
                ) : isClub ? (
                  <Building2 className="h-2.5 w-2.5 text-negotiate-club" />
                ) : (
                  <UserRound className="h-2.5 w-2.5 text-negotiate-player" />
                )}
              </div>

              {/* Content */}
              <div
                className={cn(
                  "rounded-lg border p-3",
                  isAccept
                    ? "border-negotiate-success/30 bg-negotiate-success/5"
                    : isWalkAway
                      ? "border-negotiate-danger/30 bg-negotiate-danger/5"
                      : "border-border bg-card"
                )}
              >
                <div className="mb-2 flex items-center gap-2">
                  <span className="text-xs font-medium text-muted-foreground">
                    {formatRound(round.round_number)}
                  </span>
                  <Badge
                    variant={isClub ? "default" : "success"}
                    className={cn(
                      "text-[10px]",
                      isClub
                        ? "bg-negotiate-club/20 text-negotiate-club"
                        : "bg-negotiate-player/20 text-negotiate-player"
                    )}
                  >
                    {isClub ? "Club" : "Player"}
                  </Badge>
                  <Badge
                    variant={
                      isAccept
                        ? "success"
                        : isWalkAway
                          ? "destructive"
                          : "outline"
                    }
                    className="text-[10px]"
                  >
                    {round.action}
                  </Badge>
                </div>

                {round.term_sheet ? (
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Total</span>
                    <span className="font-medium">
                      {formatEUR(round.term_sheet.total_value_eur)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Base</span>
                    <span className="font-medium">
                      {formatEUR(round.term_sheet.base_salary_eur)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Years</span>
                    <span className="font-medium">
                      {round.term_sheet.contract_years}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Release</span>
                    <span className="font-medium">
                      {formatEUR(round.term_sheet.release_clause_eur)}
                    </span>
                  </div>
                </div>
                ) : (
                <div className="text-xs text-muted-foreground italic">No term sheet (walk away)</div>
                )}

                {round.reasoning && (
                  <p className="mt-2 text-[11px] leading-snug text-muted-foreground">
                    {round.reasoning}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
