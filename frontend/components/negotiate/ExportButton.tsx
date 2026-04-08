"use client";

import React, { useState } from "react";
import { useNegotiationStore } from "@/lib/stores/negotiationStore";
import { formatEUR } from "@/lib/utils";
import { Download, FileText, FileJson, ChevronDown } from "lucide-react";

interface Citation {
  name: string;
  url: string;
  data_type: string;
}

function extractCitations(warRoomResults: any, marketContext: any): Citation[] {
  const citationMap = new Map<string, Citation>();

  // Extract from comparables
  if (warRoomResults?.comparables?.similar_players) {
    for (const p of warRoomResults.comparables.similar_players) {
      if (p.source_url || p.citation) {
        const name = p.source || "Spotrac";
        const key = `${name}-${p.name || ""}`;
        if (!citationMap.has(key)) {
          citationMap.set(key, {
            name,
            url: p.source_url || "",
            data_type: "comparable",
          });
        }
      }
    }
  }

  // Extract from analysis text patterns like "[Data: Transfermarkt (2025), Spotrac, Capology 2024-25]"
  const analysisTexts = [
    warRoomResults?.comparables?.analysis,
    warRoomResults?.offer_analysis?.analysis,
    warRoomResults?.clause_risk?.analysis,
    warRoomResults?.strategy?.analysis,
    warRoomResults?.fact_check?.analysis,
    warRoomResults?.reasoning,
  ].filter(Boolean);

  for (const text of analysisTexts) {
    const dataMatch = text.match(/\[Data:\s*([^\]]+)\]/);
    if (dataMatch) {
      const sources = dataMatch[1].split(",").map((s: string) => s.trim());
      for (const source of sources) {
        if (!citationMap.has(source)) {
          citationMap.set(source, {
            name: source,
            url: "",
            data_type: "salary",
          });
        }
      }
    }
  }

  // Add market context sources
  if (marketContext) {
    if (!citationMap.has("Transfermarkt")) {
      citationMap.set("Transfermarkt", {
        name: "Transfermarkt",
        url: "https://www.transfermarkt.com",
        data_type: "market_value",
      });
    }
    if (!citationMap.has("Capology")) {
      citationMap.set("Capology", {
        name: "Capology",
        url: "https://www.capology.com",
        data_type: "salary",
      });
    }
  }

  return Array.from(citationMap.values());
}

function computeValidationMetrics(
  rounds: any[],
  marketContext: any,
  maxRounds: number,
  currentRound: number,
  status: string,
  walkAwayThreshold: number
) {
  // Market realism: is latest offer base_salary within p25-p75?
  let marketRealism = 50;
  const latestRound = rounds.length > 0 ? rounds[rounds.length - 1] : null;
  if (latestRound?.term_sheet && marketContext) {
    const baseSalary = latestRound.term_sheet.base_salary_eur;
    const p25 = marketContext.p25_eur;
    const p75 = marketContext.p75_eur;
    const median = marketContext.median_eur;
    if (baseSalary >= p25 && baseSalary <= p75) {
      // Within range - score based on closeness to median
      const distFromMedian = Math.abs(baseSalary - median);
      const rangeHalf = (p75 - p25) / 2;
      marketRealism = Math.round(100 - (distFromMedian / rangeHalf) * 30);
    } else if (baseSalary < p25) {
      const deviation = (p25 - baseSalary) / p25;
      marketRealism = Math.max(0, Math.round(40 - deviation * 100));
    } else {
      const deviation = (baseSalary - p75) / p75;
      marketRealism = Math.max(0, Math.round(40 - deviation * 100));
    }
    marketRealism = Math.max(0, Math.min(100, marketRealism));
  }

  // Outcome quality: compare to walk-away threshold and market median
  let clubSatisfaction = 50;
  let playerSatisfaction = 50;
  if (latestRound?.term_sheet && marketContext) {
    const totalValue = latestRound.term_sheet.total_value_eur;
    const median = marketContext.median_eur;
    // Club is happier when paying below median
    clubSatisfaction = Math.round(
      Math.max(0, Math.min(100, 50 + ((median - totalValue) / median) * 100))
    );
    // Player is happier when earning above median
    playerSatisfaction = Math.round(
      Math.max(0, Math.min(100, 50 + ((totalValue - median) / median) * 100))
    );
    if (status === "accepted") {
      clubSatisfaction = Math.min(100, clubSatisfaction + 10);
      playerSatisfaction = Math.min(100, playerSatisfaction + 10);
    }
  }

  // Efficiency: how quickly the deal was reached
  const efficiency =
    maxRounds > 0 ? Math.round(((maxRounds - currentRound) / maxRounds) * 100) : 0;

  // Compliance rate
  const compliantRounds = rounds.filter(
    (r) => r.constraint_violations.length === 0
  ).length;
  const complianceRate =
    rounds.length > 0 ? Math.round((compliantRounds / rounds.length) * 100) : 100;

  return {
    market_realism: marketRealism,
    outcome_quality: { club_satisfaction: clubSatisfaction, player_satisfaction: playerSatisfaction },
    efficiency,
    compliance_rate: complianceRate,
  };
}

function generateTextReport(exportData: any): string {
  const lines: string[] = [];
  const sep = "=".repeat(60);
  const subsep = "-".repeat(40);

  lines.push(sep);
  lines.push("NEGOTIATION REPORT");
  lines.push(sep);
  lines.push(`Date: ${exportData.metadata.date}`);
  lines.push(`Player: ${exportData.metadata.player_name}`);
  lines.push(`Club: ${exportData.metadata.club_name}`);
  lines.push(`User Side: ${exportData.metadata.user_side === "club" ? "Club GM" : "Player Agent"}`);
  lines.push("");

  // Executive Summary
  lines.push(subsep);
  lines.push("EXECUTIVE SUMMARY");
  lines.push(subsep);
  const statusLabel =
    exportData.outcome.status === "accepted"
      ? "Deal Accepted"
      : exportData.outcome.status === "walked_away"
        ? "Walked Away - No Deal"
        : "Max Rounds Reached - No Deal";
  lines.push(`Outcome: ${statusLabel}`);
  lines.push(`Total Rounds: ${exportData.outcome.total_rounds}`);
  if (exportData.final_terms) {
    lines.push(`Final Total Value: ${formatEUR(exportData.final_terms.total_value_eur)}`);
    lines.push(`Final Base Salary: ${formatEUR(exportData.final_terms.base_salary_eur)}`);
  }
  if (exportData.validation_metrics) {
    lines.push(`Market Realism Score: ${exportData.validation_metrics.market_realism}/100`);
    lines.push(`Efficiency: ${exportData.validation_metrics.efficiency}%`);
  }
  lines.push("");

  // Negotiation Timeline
  lines.push(subsep);
  lines.push("NEGOTIATION TIMELINE");
  lines.push(subsep);
  for (const r of exportData.all_rounds) {
    const sideLabel = r.side === "club" ? "Club" : "Player";
    const salary = r.term_sheet ? formatEUR(r.term_sheet.base_salary_eur) : "N/A";
    const total = r.term_sheet ? formatEUR(r.term_sheet.total_value_eur) : "N/A";
    lines.push(`Round ${r.round_number} [${sideLabel}] ${r.action}`);
    lines.push(`  Base Salary: ${salary} | Total Value: ${total}`);
    if (r.reasoning) lines.push(`  Reasoning: ${r.reasoning}`);
    if (r.constraint_violations.length > 0) {
      lines.push(`  Violations: ${r.constraint_violations.join("; ")}`);
    }
    lines.push("");
  }

  // Market Analysis
  lines.push(subsep);
  lines.push("MARKET ANALYSIS");
  lines.push(subsep);
  if (exportData.market_context) {
    const mc = exportData.market_context;
    lines.push(`Predicted Value: ${formatEUR(mc.predicted_value_eur)}`);
    lines.push(`Salary Range: P25 ${formatEUR(mc.p25_eur)} | Median ${formatEUR(mc.median_eur)} | P75 ${formatEUR(mc.p75_eur)}`);
    if (mc.comparables && mc.comparables.length > 0) {
      lines.push("Comparables:");
      for (const c of mc.comparables) {
        lines.push(`  - ${c.player_name} at ${c.club}: ${formatEUR(c.salary_eur)}`);
      }
    }
  }
  lines.push("");

  // Risk Assessment
  lines.push(subsep);
  lines.push("RISK ASSESSMENT");
  lines.push(subsep);
  if (exportData.war_room_analysis?.clause_risk) {
    const cr = exportData.war_room_analysis.clause_risk;
    if (cr.analysis) lines.push(cr.analysis);
    if (cr.risks?.length > 0) {
      lines.push("Risks:");
      for (const r of cr.risks) {
        lines.push(`  - ${typeof r === "string" ? r : JSON.stringify(r)}`);
      }
    }
    if (cr.missing_protections?.length > 0) {
      lines.push("Missing Protections:");
      for (const m of cr.missing_protections) {
        lines.push(`  - ${typeof m === "string" ? m : JSON.stringify(m)}`);
      }
    }
  } else {
    lines.push("No clause/risk analysis available.");
  }
  lines.push("");

  // Final Terms
  lines.push(subsep);
  lines.push("FINAL TERMS");
  lines.push(subsep);
  if (exportData.final_terms) {
    const ft = exportData.final_terms;
    lines.push(`Base Salary: ${formatEUR(ft.base_salary_eur)}`);
    lines.push(`Signing Bonus: ${formatEUR(ft.signing_bonus_eur)}`);
    lines.push(`Performance Bonus: ${formatEUR(ft.performance_bonus_eur)}`);
    lines.push(`Contract Years: ${ft.contract_years}${ft.option_year ? " + option year" : ""}`);
    lines.push(`Release Clause: ${formatEUR(ft.release_clause_eur)}`);
    lines.push(`Image Rights: ${ft.image_rights_pct}%`);
    lines.push(`No-Trade Clause: ${ft.no_trade_clause ? "Yes" : "No"}`);
    lines.push(`Total Value: ${formatEUR(ft.total_value_eur)}`);
  } else {
    lines.push("No final terms (negotiation did not conclude with a deal).");
  }
  lines.push("");

  // Sources
  lines.push(subsep);
  lines.push("SOURCES");
  lines.push(subsep);
  if (exportData.citations && exportData.citations.length > 0) {
    for (const c of exportData.citations) {
      const urlPart = c.url ? ` (${c.url})` : "";
      lines.push(`- ${c.name}${urlPart} [${c.data_type}]`);
    }
  } else {
    lines.push("No external sources cited.");
  }
  lines.push("");
  lines.push(sep);
  lines.push("End of Report");

  return lines.join("\n");
}

export default function ExportButton() {
  const [showDropdown, setShowDropdown] = useState(false);
  const rounds = useNegotiationStore((s) => s.rounds);
  const status = useNegotiationStore((s) => s.status);
  const warRoomResults = useNegotiationStore((s) => s.warRoomResults);
  const playerName = useNegotiationStore((s) => s.playerName);
  const clubName = useNegotiationStore((s) => s.clubName);
  const currentRound = useNegotiationStore((s) => s.currentRound);
  const maxRounds = useNegotiationStore((s) => s.maxRounds);
  const marketContext = useNegotiationStore((s) => s.marketContext);
  const userSide = useNegotiationStore((s) => s.userSide);
  const requestId = useNegotiationStore((s) => s.requestId);
  const walkAwayThreshold = useNegotiationStore((s) => s.walkAwayThreshold);

  const buildExportData = async () => {
    const latestRound = rounds.length > 0 ? rounds[rounds.length - 1] : null;
    const citations = extractCitations(warRoomResults, marketContext);

    // Try to fetch server-side metrics first, fall back to client-side
    let validationMetrics = computeValidationMetrics(
      rounds,
      marketContext,
      maxRounds,
      currentRound,
      status,
      walkAwayThreshold
    );

    if (requestId) {
      try {
        const resp = await fetch(`/api/backend/metrics/${requestId}`);
        if (resp.ok) {
          const serverMetrics = await resp.json();
          if (serverMetrics) {
            validationMetrics = {
              market_realism: serverMetrics.market_realism ?? validationMetrics.market_realism,
              outcome_quality: serverMetrics.outcome_quality ?? validationMetrics.outcome_quality,
              efficiency: serverMetrics.efficiency ?? validationMetrics.efficiency,
              compliance_rate: serverMetrics.compliance_rate ?? validationMetrics.compliance_rate,
            };
          }
        }
      } catch {
        // Use client-side metrics as fallback
      }
    }

    return {
      metadata: {
        player_name: playerName,
        club_name: clubName,
        user_side: userSide,
        date: new Date().toISOString(),
        max_rounds: maxRounds,
      },
      outcome: {
        status,
        total_rounds: currentRound,
      },
      final_terms: latestRound?.term_sheet || null,
      all_rounds: rounds.map((r) => ({
        round_number: r.round_number,
        side: r.side,
        action: r.action,
        term_sheet: r.term_sheet,
        reasoning: r.reasoning,
        constraint_violations: r.constraint_violations,
        timestamp: r.timestamp,
      })),
      market_context: marketContext
        ? {
            predicted_value_eur: marketContext.predicted_value_eur,
            source_citation: "Transfermarkt market value prediction",
            salary_range: {
              p25_eur: marketContext.p25_eur,
              median_eur: marketContext.median_eur,
              p75_eur: marketContext.p75_eur,
              methodology_basis: "Comparable player salary analysis via Capology and Spotrac data",
            },
            comparables: marketContext.comparables,
          }
        : null,
      war_room_analysis: warRoomResults
        ? {
            comparables: warRoomResults.comparables || null,
            clause_risk: warRoomResults.clause_risk || null,
            strategy: warRoomResults.strategy || null,
            fact_check: warRoomResults.fact_check || null,
            recommended_action: warRoomResults.recommended_action,
            recommended_counter: warRoomResults.recommended_counter,
            reasoning: warRoomResults.reasoning,
          }
        : null,
      citations,
      validation_metrics: validationMetrics,
    };
  };

  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const filePrefix = `negotiation-${playerName.replace(/\s+/g, "-").toLowerCase()}-${clubName.replace(/\s+/g, "-").toLowerCase()}`;

  const handleExportJSON = async () => {
    setShowDropdown(false);
    const data = await buildExportData();
    downloadFile(JSON.stringify(data, null, 2), `${filePrefix}.json`, "application/json");
  };

  const handleExportReport = async () => {
    setShowDropdown(false);
    const data = await buildExportData();
    const report = generateTextReport(data);
    downloadFile(report, `${filePrefix}-report.txt`, "text/plain");
  };

  return (
    <div className="relative">
      <button
        data-tour="export-button"
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      >
        <Download className="h-3.5 w-3.5" />
        Export
        <ChevronDown className="h-3 w-3" />
      </button>

      {showDropdown && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setShowDropdown(false)}
          />
          <div className="absolute right-0 top-full z-50 mt-1 w-44 rounded-lg border border-border bg-card shadow-lg">
            <button
              onClick={handleExportJSON}
              className="flex w-full items-center gap-2 px-3 py-2 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <FileJson className="h-3.5 w-3.5" />
              Export JSON
            </button>
            <button
              onClick={handleExportReport}
              className="flex w-full items-center gap-2 px-3 py-2 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <FileText className="h-3.5 w-3.5" />
              Export Report (.txt)
            </button>
          </div>
        </>
      )}
    </div>
  );
}
