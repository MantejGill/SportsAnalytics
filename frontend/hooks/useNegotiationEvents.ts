"use client";

import { useCallback, useRef } from "react";
import { useNegotiationStore } from "@/lib/stores/negotiationStore";
import type { NegotiationRound, WarRoomResults } from "@/lib/types";

const POLL_INTERVAL_MS = 3000;

export function useNegotiationEvents() {
  const pollerRef  = useRef<ReturnType<typeof setInterval> | null>(null);
  const seenEvents = useRef<number>(0);

  const {
    addRound,
    updateAgent,
    setStatus,
    setActiveAgent,
    setMarketContext,
    setConnected,
    setWarRoomResults,
    setAwaitingDecision,
    addLog,
  } = useNegotiationStore();

  const disconnect = useCallback(() => {
    if (pollerRef.current) {
      clearInterval(pollerRef.current);
      pollerRef.current = null;
    }
    seenEvents.current = 0;
    setConnected(false);
  }, [setConnected]);

  const processEvent = useCallback(
    (etype: string, edata: any) => {
      if (etype === "market_prediction") {
        if (edata.market_context) setMarketContext(edata.market_context);
        addLog("Market prediction complete");

      } else if (etype === "opponent_offer" || etype === "club_proposal") {
        if (edata.term_sheet) {
          const round: NegotiationRound = {
            round_number: edata.round || edata.round_number || 0,
            side: edata.side || "club",
            action: edata.action || "PROPOSE",
            term_sheet: edata.term_sheet,
            reasoning: edata.reasoning || "",
            constraint_violations: edata.constraint_violations || [],
            timestamp: new Date().toISOString(),
          };
          addRound(round);
        }
        addLog(`Opponent ${edata.action}: EUR ${edata.term_sheet?.base_salary_eur?.toLocaleString() || "?"}`);
        updateAgent("comparables", "active");
        setActiveAgent("comparables");

      } else if (etype === "player_response") {
        if (edata.term_sheet || edata.action === "WALK_AWAY" || edata.action === "ACCEPT") {
          const round: NegotiationRound = {
            round_number: edata.round || 0,
            side: "player",
            action: edata.action || "COUNTER",
            term_sheet: edata.term_sheet || null,
            reasoning: edata.reasoning || "",
            constraint_violations: [],
            timestamp: new Date().toISOString(),
          };
          addRound(round);
        }
        addLog(`Player ${edata.action}`);
        updateAgent("comparables", "active");
        setActiveAgent("comparables");

      } else if (etype === "war_room_agent") {
        const agentId = edata.agent_id as string;
        const st = edata.status as string;
        if (st === "active")    { updateAgent(agentId, "active");   setActiveAgent(agentId); }
        else if (st === "complete") updateAgent(agentId, "complete");
        else if (st === "error")    updateAgent(agentId, "error");
        addLog(`War room agent ${agentId}: ${st}`);

      } else if (etype === "war_room_complete") {
        const data = edata as WarRoomResults;
        updateAgent("comparables",   "complete");
        updateAgent("offer_analysis","complete");
        updateAgent("clause_risk",   "complete");
        updateAgent("strategy",      "complete");
        updateAgent("fact_check",    "complete");
        setActiveAgent(null);
        setWarRoomResults(data);
        setAwaitingDecision(true);
        addLog(`War room complete. Recommended: ${data.recommended_action}`);

      } else if (etype === "constraint_check") {
        addLog(`Constraint check: ${edata.valid ? "PASS" : "FAIL"} (${edata.violations?.length || 0} violations)`);

      } else if (etype === "negotiation_complete") {
        const st = (edata.status as string) || "";
        if (st === "ACCEPTED")    setStatus("accepted");
        else if (st === "WALKED_AWAY") setStatus("walked_away");
        else setStatus("max_rounds");
        updateAgent("comparables",   "complete");
        updateAgent("offer_analysis","complete");
        updateAgent("clause_risk",   "complete");
        updateAgent("strategy",      "complete");
        updateAgent("fact_check",    "complete");
        setActiveAgent(null);
        setAwaitingDecision(false);
        addLog(`Negotiation complete: ${st} after ${edata.total_rounds} rounds`);
        disconnect();

      } else if (etype === "max_rounds") {
        setStatus("max_rounds");
        setActiveAgent(null);
        setAwaitingDecision(false);
        addLog(`Max rounds reached`);
        disconnect();
      }
    },
    [addRound, updateAgent, setStatus, setActiveAgent, setMarketContext,
     setWarRoomResults, setAwaitingDecision, addLog, disconnect]
  );

  const connect = useCallback(
    (requestId: string) => {
      disconnect();
      setConnected(true);
      addLog("Polling connected");

      const backendBase = process.env.NEXT_PUBLIC_BACKEND_URL || "";
      // Use Next.js rewrite proxy (/api/backend/*) when no explicit backend URL,
      // otherwise hit the backend directly.
      const stateUrl = backendBase
        ? `${backendBase}/api/negotiation/${requestId}`
        : `/api/backend/negotiation/${requestId}`;

      pollerRef.current = setInterval(async () => {
        try {
          const res = await fetch(stateUrl);
          if (!res.ok) return;
          const data = await res.json();

          const events: any[] = data.events || [];
          const newEvents = events.slice(seenEvents.current);
          seenEvents.current = events.length;

          for (const evt of newEvents) {
            const etype = evt.type || evt.event || "";
            const edata = evt.data ?? evt;
            processEvent(etype, edata);
          }

          // Check terminal state
          const status = data.status || "";
          if (status === "completed" || status === "error") {
            clearInterval(pollerRef.current!);
            pollerRef.current = null;
          }
        } catch (err) {
          console.warn("[Poll] fetch error:", err);
        }
      }, POLL_INTERVAL_MS);
    },
    [disconnect, setConnected, addLog, processEvent]
  );

  return {
    isConnected: useNegotiationStore((s) => s.isConnected),
    connect,
    disconnect,
  };
}
