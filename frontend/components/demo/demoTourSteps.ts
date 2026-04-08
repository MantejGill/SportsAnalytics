import type { TourStep } from "./GuidedTour";

export const DEMO_TOUR_STEPS: TourStep[] = [
  // --- SETUP PHASE ---
  {
    target: '[data-tour="app-header"]',
    title: "Welcome to Auto-Negotiate",
    description:
      "An AI-powered multi-agent negotiation system for football player contracts. Built with CopilotKit, LangGraph, and GPT-4o-mini. Let's walk through a full negotiation.",
    placement: "bottom",
  },
  {
    target: '[data-tour="side-selector"]',
    title: "Step 1: Choose Your Side",
    description:
      "The user picks whether they're the Club's GM or the Player's Agent. The AI controls the other side. We'll select Player Agent now.",
    placement: "bottom",
    action: { type: "click", selector: "text:Player Agent" },
    autoAdvanceMs: 2000,
  },
  {
    target: '[data-tour="setup-form"]',
    title: "Step 2: Set Parameters",
    description:
      "Player name, club, budget, walk-away threshold, and priorities are pre-filled. The system will look up Bukayo Saka's real market data from our 20-player database (Transfermarkt, Spotrac, Capology 2024-25). Starting the negotiation now...",
    placement: "top",
    action: { type: "click", selector: 'button[type="submit"]' },
    autoAdvanceMs: 3000,
  },

  // --- WAITING FOR AI ---
  {
    target: '[data-tour="app-header"]',
    title: "AI Opponent Processing",
    description:
      "The LangGraph negotiation graph is running: Market Predictor → AI Club Agent (GPT-4o-mini) → 4-Layer Constraint Checker → 5-Agent War Room. This takes ~15-20 seconds for the LLM calls. Watch the dashboard populate...",
    placement: "bottom",
    waitFor: 20000,
    autoAdvanceMs: 20000,
  },

  // --- OFFER ANALYSIS ---
  {
    target: '[data-tour="offer-card"]',
    title: "AI Opponent's Offer",
    description:
      "Arsenal's AI Club Agent proposed its opening offer. The card shows: total contract value, base salary, bonuses, contract years, clauses. Verdict badges instantly show 'Below Market Range' and 'Below Walk-Away' if applicable. All values are in EUR.",
    placement: "right",
  },
  {
    target: '[data-tour="war-room"]',
    title: "5-Agent War Room",
    description:
      "Five specialist agents analyzed the offer:\n• Comparables: Found 4 deals (Sancho, Foden, Martinelli, Vinicius Jr) with cited sources\n• Offer Analyzer: Shows percentile position vs salary range\n• Clause & Risk: LLM-powered risk flags (no-trade, release clause, etc.)\n• Strategy: BATNA/ZOPA analysis with recommended counter\n• Fact-Check: Verified term sheet math",
    placement: "top",
  },
  {
    target: '[data-tour="recommendation"]',
    title: "AI Recommendation",
    description:
      "The Decision Aggregator consolidated all 5 agents' analyses into a single recommendation with a specific counter-offer amount. The animated MovingBorder effect highlights this is the system's key output.",
    placement: "top",
  },
  {
    target: '[data-tour="decision-panel"]',
    title: "Human-in-the-Loop Decision",
    description:
      "This is the key differentiator — the system PAUSES and waits for the user's decision. Three options: ACCEPT (green), COUNTER (blue) with editable term sheet, or WALK AWAY (red). The user can follow or override the AI recommendation.",
    placement: "top",
  },

  // --- METRICS ---
  {
    target: '[data-tour="metrics-panel"]',
    title: "Validation Metrics",
    description:
      "Real-time metrics from the project spec:\n• Market Realism (0-100): salary vs comparable deals\n• Outcome Quality: satisfaction for both sides\n• Efficiency: rounds to agreement\n• Compliance: constraint violation rate\nThese update after every round.",
    placement: "left",
  },
  {
    target: '[data-tour="constraint-checker"]',
    title: "4-Layer Constraint Checker",
    description:
      "Smriti and Madhavi's constraint system validates every offer through 4 layers:\n• Layer 0: Format (JSON schema)\n• Layer 1: Contract Sanity (years, values)\n• Layer 2: Market Realism (salary band)\n• Layer 3: Protocol (no repeats, turn order)\n100% compliance means all offers passed.",
    placement: "left",
  },
  {
    target: '[data-tour="chat-sidebar"]',
    title: "Chat-Driven Negotiation",
    description:
      "The CopilotKit chat serves as the primary interface. Users can type natural language like 'counter at 13 million' or 'accept the deal'. The LLM parses intent and calls the appropriate backend action. The chat also provides market context and advisory insights.",
    placement: "left",
  },
  {
    target: '[data-tour="app-header"]',
    title: "Demo Complete!",
    description:
      "This was Auto-Negotiate — combining ML salary prediction (Abdullah), constraint-aware deal optimization (Smriti & Madhavi), and multi-agent negotiation (Mantej/Vishal) into a unified CopilotKit interface. 20 real players, cited market data, and human-in-the-loop control.",
    placement: "bottom",
  },
];
