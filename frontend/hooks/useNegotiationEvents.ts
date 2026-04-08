"use client";

import { useCallback, useRef } from "react";
import { useNegotiationStore } from "@/lib/stores/negotiationStore";
import type { NegotiationRound, WarRoomResults } from "@/lib/types";

export function useNegotiationEvents() {
  const eventSourceRef = useRef<EventSource | null>(null);

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
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setConnected(false);
  }, [setConnected]);

  const connect = useCallback(
    (requestId: string) => {
      disconnect();

      // Connect directly to backend to avoid Next.js proxy buffering SSE
      const url = `http://localhost:8100/api/stream/${requestId}`;
      console.log("[SSE] Connecting to:", url);
      const es = new EventSource(url);
      eventSourceRef.current = es;

      es.onopen = () => {
        console.log("[SSE] Connected");
        setConnected(true);
        addLog("SSE connected");
      };

      // --- Backend sends named events, listen for each ---

      es.addEventListener("market_prediction", (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          console.log("[SSE] market_prediction", data);
          if (data.market_context) {
            setMarketContext(data.market_context);
          }
          addLog("Market prediction complete");
        } catch (err) {
          console.error("[SSE] parse error market_prediction", err);
        }
      });

      // AI opponent's offer/counter arrives
      es.addEventListener("opponent_offer", (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          console.log("[SSE] opponent_offer", data);

          if (data.term_sheet) {
            const round: NegotiationRound = {
              round_number: data.round || 0,
              side: data.side || "club",
              action: data.action || "PROPOSE",
              term_sheet: data.term_sheet,
              reasoning: data.reasoning || "",
              constraint_violations: data.constraint_violations || [],
              timestamp: new Date().toISOString(),
            };
            addRound(round);
          }

          addLog(
            `Opponent ${data.action}: EUR ${data.term_sheet?.base_salary_eur?.toLocaleString() || "?"}`
          );

          // Start war room analysis sequence
          updateAgent("comparables", "active");
          setActiveAgent("comparables");
        } catch (err) {
          console.error("[SSE] parse error opponent_offer", err);
        }
      });

      // Legacy event support: club_proposal
      es.addEventListener("club_proposal", (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          console.log("[SSE] club_proposal", data);

          if (data.term_sheet) {
            const round: NegotiationRound = {
              round_number: data.round || 0,
              side: "club",
              action: data.action || "PROPOSE",
              term_sheet: data.term_sheet,
              reasoning: data.reasoning || "",
              constraint_violations: [],
              timestamp: new Date().toISOString(),
            };
            addRound(round);
          }

          addLog(
            `Club ${data.action}: EUR ${data.term_sheet?.base_salary_eur?.toLocaleString() || "?"}`
          );

          // Start war room analysis
          updateAgent("comparables", "active");
          setActiveAgent("comparables");
        } catch (err) {
          console.error("[SSE] parse error club_proposal", err);
        }
      });

      // Legacy: player_response
      es.addEventListener("player_response", (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          console.log("[SSE] player_response", data);

          if (
            data.term_sheet ||
            data.action === "WALK_AWAY" ||
            data.action === "ACCEPT"
          ) {
            const round: NegotiationRound = {
              round_number: data.round || 0,
              side: "player",
              action: data.action || "COUNTER",
              term_sheet: data.term_sheet || null,
              reasoning: data.reasoning || "",
              constraint_violations: [],
              timestamp: new Date().toISOString(),
            };
            addRound(round);
          }

          addLog(
            `Player ${data.action}: ${data.term_sheet ? "EUR " + data.term_sheet.base_salary_eur?.toLocaleString() : "no offer"}`
          );

          // Start war room analysis
          updateAgent("comparables", "active");
          setActiveAgent("comparables");
        } catch (err) {
          console.error("[SSE] parse error player_response", err);
        }
      });

      // War room agent progress events
      es.addEventListener("war_room_agent", (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          console.log("[SSE] war_room_agent", data);
          const agentId = data.agent_id as string;
          const status = data.status as string;

          if (status === "active") {
            updateAgent(agentId, "active");
            setActiveAgent(agentId);
          } else if (status === "complete") {
            updateAgent(agentId, "complete");
          } else if (status === "error") {
            updateAgent(agentId, "error");
          }

          addLog(`War room agent ${agentId}: ${status}`);
        } catch (err) {
          console.error("[SSE] parse error war_room_agent", err);
        }
      });

      // War room analysis complete - all 5 agents done
      es.addEventListener("war_room_complete", (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as WarRoomResults;
          console.log("[SSE] war_room_complete", data);

          // Mark all war room agents as complete
          updateAgent("comparables", "complete");
          updateAgent("offer_analysis", "complete");
          updateAgent("clause_risk", "complete");
          updateAgent("strategy", "complete");
          updateAgent("fact_check", "complete");
          setActiveAgent(null);

          setWarRoomResults(data);
          setAwaitingDecision(true);

          addLog(
            `War room complete. Recommended: ${data.recommended_action}`
          );
        } catch (err) {
          console.error("[SSE] parse error war_room_complete", err);
        }
      });

      es.addEventListener("constraint_check", (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          console.log("[SSE] constraint_check", data);
          addLog(
            `Constraint check: ${data.valid ? "PASS" : "FAIL"} (${data.violations?.length || 0} violations)`
          );
        } catch (err) {
          console.error("[SSE] parse error constraint_check", err);
        }
      });

      es.addEventListener("negotiation_complete", (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          console.log("[SSE] negotiation_complete", data);
          const status = data.status as string;
          if (status === "ACCEPTED") setStatus("accepted");
          else if (status === "WALKED_AWAY") setStatus("walked_away");
          else setStatus("max_rounds");

          // Mark all agents complete
          updateAgent("comparables", "complete");
          updateAgent("offer_analysis", "complete");
          updateAgent("clause_risk", "complete");
          updateAgent("strategy", "complete");
          updateAgent("fact_check", "complete");
          setActiveAgent(null);
          setAwaitingDecision(false);

          addLog(
            `Negotiation complete: ${status} after ${data.total_rounds} rounds`
          );
          disconnect();
        } catch (err) {
          console.error("[SSE] parse error negotiation_complete", err);
        }
      });

      es.addEventListener("max_rounds", (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          console.log("[SSE] max_rounds", data);
          setStatus("max_rounds");
          setActiveAgent(null);
          setAwaitingDecision(false);
          addLog(`Max rounds reached: ${data.max_rounds}`);
        } catch (err) {
          console.error("[SSE] parse error max_rounds", err);
        }
      });

      es.addEventListener("error", (event: MessageEvent) => {
        try {
          const data = JSON.parse((event as any).data || "{}");
          console.error("[SSE] error event", data);
          addLog(`Error: ${data.message || "Unknown error"}`);
        } catch {
          // SSE connection error (not a named event)
        }
      });

      es.onerror = () => {
        console.warn("[SSE] Connection error/closed");
        addLog("SSE connection closed");
        setConnected(false);
      };
    },
    [
      disconnect,
      addRound,
      updateAgent,
      setStatus,
      setActiveAgent,
      setMarketContext,
      setConnected,
      setWarRoomResults,
      setAwaitingDecision,
      addLog,
    ]
  );

  return {
    isConnected: useNegotiationStore((s) => s.isConnected),
    connect,
    disconnect,
  };
}
