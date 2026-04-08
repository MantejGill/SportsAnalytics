"use client";

import React, { useState, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import { formatEUR } from "@/lib/utils";
import type { TermSheet } from "@/lib/types";
import { Calculator, Send } from "lucide-react";

interface CounterOfferFormProps {
  recommended: TermSheet | null;
  latestOffer: TermSheet | null;
  playerName: string;
  onSubmit: (termSheet: TermSheet) => void;
  onCancel: () => void;
}

export default function CounterOfferForm({
  recommended,
  latestOffer,
  playerName,
  onSubmit,
  onCancel,
}: CounterOfferFormProps) {
  const base = recommended || latestOffer;

  const [baseSalary, setBaseSalary] = useState(base?.base_salary_eur ?? 0);
  const [signingBonus, setSigningBonus] = useState(base?.signing_bonus_eur ?? 0);
  const [performanceBonus, setPerformanceBonus] = useState(
    base?.performance_bonus_eur ?? 0
  );
  const [contractYears, setContractYears] = useState(base?.contract_years ?? 4);
  const [optionYear, setOptionYear] = useState(base?.option_year ?? false);
  const [releaseClause, setReleaseClause] = useState(
    base?.release_clause_eur ?? 0
  );
  const [imageRights, setImageRights] = useState(base?.image_rights_pct ?? 0);
  const [noTrade, setNoTrade] = useState(base?.no_trade_clause ?? false);

  useEffect(() => {
    if (base) {
      setBaseSalary(base.base_salary_eur);
      setSigningBonus(base.signing_bonus_eur);
      setPerformanceBonus(base.performance_bonus_eur);
      setContractYears(base.contract_years);
      setOptionYear(base.option_year);
      setReleaseClause(base.release_clause_eur);
      setImageRights(base.image_rights_pct);
      setNoTrade(base.no_trade_clause);
    }
  }, [base]);

  const totalValue = useMemo(() => {
    return baseSalary * contractYears + signingBonus + performanceBonus;
  }, [baseSalary, contractYears, signingBonus, performanceBonus]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      player_name: playerName,
      position: base?.position ?? "",
      base_salary_eur: baseSalary,
      signing_bonus_eur: signingBonus,
      performance_bonus_eur: performanceBonus,
      contract_years: contractYears,
      option_year: optionYear,
      release_clause_eur: releaseClause,
      total_value_eur: totalValue,
      image_rights_pct: imageRights,
      no_trade_clause: noTrade,
    });
  };

  return (
    <motion.form
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      onSubmit={handleSubmit}
      className="space-y-4 rounded-xl border border-primary/30 bg-card p-5"
    >
      <div className="flex items-center gap-2">
        <Calculator className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold">Build Your Counter-Offer</h3>
      </div>

      {/* Total preview */}
      <div className="rounded-lg bg-primary/10 p-3 text-center">
        <p className="text-xs text-muted-foreground">Projected Total Value</p>
        <p className="text-xl font-bold text-primary">{formatEUR(totalValue)}</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <FormField
          label="Base Salary (EUR/yr)"
          type="number"
          value={baseSalary}
          onChange={setBaseSalary}
          step={100_000}
        />
        <FormField
          label="Signing Bonus (EUR)"
          type="number"
          value={signingBonus}
          onChange={setSigningBonus}
          step={100_000}
        />
        <FormField
          label="Performance Bonus (EUR)"
          type="number"
          value={performanceBonus}
          onChange={setPerformanceBonus}
          step={100_000}
        />
        <FormField
          label="Contract Years"
          type="number"
          value={contractYears}
          onChange={setContractYears}
          min={1}
          max={7}
          step={1}
        />
        <FormField
          label="Release Clause (EUR)"
          type="number"
          value={releaseClause}
          onChange={setReleaseClause}
          step={1_000_000}
        />
        <FormField
          label="Image Rights (%)"
          type="number"
          value={imageRights}
          onChange={setImageRights}
          min={0}
          max={100}
          step={5}
        />

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={optionYear}
              onChange={(e) => setOptionYear(e.target.checked)}
              className="h-4 w-4 rounded border-input bg-background"
            />
            Option Year
          </label>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={noTrade}
              onChange={(e) => setNoTrade(e.target.checked)}
              className="h-4 w-4 rounded border-input bg-background"
            />
            No-Trade Clause
          </label>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          type="submit"
          className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
        >
          <Send className="h-4 w-4" />
          Submit Counter-Offer
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-border px-4 py-2.5 text-sm text-muted-foreground transition-colors hover:bg-muted"
        >
          Cancel
        </button>
      </div>
    </motion.form>
  );
}

function FormField({
  label,
  type,
  value,
  onChange,
  min,
  max,
  step,
}: {
  label: string;
  type: "number";
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
}) {
  return (
    <div className="space-y-1">
      <label className="text-[10px] font-medium text-muted-foreground">
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        min={min}
        max={max}
        step={step}
        className="w-full rounded-lg border border-input bg-background px-3 py-1.5 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      />
    </div>
  );
}
