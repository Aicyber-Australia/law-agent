"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  CheckCircle2,
  Target,
  Clock,
  DollarSign,
  ListChecks,
  FileText,
  Users,
  Calendar,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Types matching backend ConsolidatedAnalysis
export interface TimelineEvent {
  date: string | null;
  description: string;
  significance: string;
}

export interface Party {
  role: string;
  name: string | null;
  is_user: boolean;
}

export interface Evidence {
  type: string;
  description: string;
  status: string;
  strength: string;
}

export interface RiskFactor {
  description: string;
  severity: string;
  mitigation: string | null;
}

export interface StrategyOption {
  name: string;
  description: string;
  pros: string[];
  cons: string[];
  estimated_cost: string | null;
  estimated_timeline: string | null;
}

export interface ConsolidatedAnalysis {
  // Facts
  timeline: TimelineEvent[];
  parties: Party[];
  evidence: Evidence[];
  key_facts: string[];
  fact_gaps: string[];
  narrative: string;
  // Risks
  overall_risk: string;
  strengths: string[];
  weaknesses: string[];
  risks: RiskFactor[];
  time_sensitive: string | null;
  // Strategy
  recommended: StrategyOption;
  alternatives: StrategyOption[];
  immediate_actions: string[];
}

interface AnalysisOutputProps {
  analysis: ConsolidatedAnalysis;
  className?: string;
}

export function AnalysisOutput({ analysis, className }: AnalysisOutputProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["situation", "strengths", "risks", "strategy", "actions"])
  );

  // Guard against incomplete analysis data
  if (!analysis) {
    return null;
  }

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  const getRiskColor = (risk: string | undefined | null) => {
    switch ((risk || "").toLowerCase()) {
      case "high":
        return "bg-red-100 text-red-800 border-red-200";
      case "medium":
        return "bg-amber-100 text-amber-800 border-amber-200";
      case "low":
        return "bg-green-100 text-green-800 border-green-200";
      default:
        return "bg-slate-100 text-slate-800 border-slate-200";
    }
  };

  const getRiskBgColor = (risk: string | undefined | null) => {
    switch ((risk || "").toLowerCase()) {
      case "high":
        return "bg-red-50";
      case "medium":
        return "bg-amber-50";
      case "low":
        return "bg-green-50";
      default:
        return "bg-slate-50";
    }
  };

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header with Risk Level */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Case Analysis</h2>
        <span
          className={cn(
            "px-3 py-1 rounded-full text-sm font-medium border",
            getRiskColor(analysis.overall_risk)
          )}
        >
          {(analysis.overall_risk || "UNKNOWN").toUpperCase()} RISK
        </span>
      </div>

      {/* Time Sensitive Alert */}
      {analysis.time_sensitive && (
        <div className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <Clock className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-amber-800">Time Sensitive</p>
            <p className="text-sm text-amber-700">{analysis.time_sensitive}</p>
          </div>
        </div>
      )}

      {/* Situation Section */}
      <CollapsibleSection
        title="Your Situation"
        icon={<FileText className="h-4 w-4" />}
        isExpanded={expandedSections.has("situation")}
        onToggle={() => toggleSection("situation")}
      >
        <p className="text-slate-700 leading-relaxed">{analysis.narrative}</p>

        {analysis.key_facts?.length > 0 && (
          <div className="mt-4">
            <h4 className="text-sm font-medium text-slate-600 mb-2">
              Key Facts
            </h4>
            <ul className="space-y-1">
              {analysis.key_facts.map((fact, i) => (
                <li
                  key={i}
                  className="text-sm text-slate-700 flex items-start gap-2"
                >
                  <span className="text-slate-400 mt-1">•</span>
                  {fact}
                </li>
              ))}
            </ul>
          </div>
        )}

        {analysis.parties?.length > 0 && (
          <div className="mt-4 flex items-center gap-2 text-sm text-slate-600">
            <Users className="h-4 w-4" />
            <span>
              Parties:{" "}
              {analysis.parties.map((p) => p.name || p.role).join(", ")}
            </span>
          </div>
        )}
      </CollapsibleSection>

      {/* Strengths Section */}
      {analysis.strengths?.length > 0 && (
        <CollapsibleSection
          title="What's In Your Favor"
          icon={<CheckCircle2 className="h-4 w-4 text-green-600" />}
          isExpanded={expandedSections.has("strengths")}
          onToggle={() => toggleSection("strengths")}
          className="border-green-200 bg-green-50/50"
        >
          <ul className="space-y-2">
            {analysis.strengths.map((strength, i) => (
              <li
                key={i}
                className="text-sm text-slate-700 flex items-start gap-2"
              >
                <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0 mt-0.5" />
                {strength}
              </li>
            ))}
          </ul>
        </CollapsibleSection>
      )}

      {/* Risks Section */}
      <CollapsibleSection
        title="Risks & Concerns"
        icon={<AlertTriangle className="h-4 w-4 text-amber-600" />}
        isExpanded={expandedSections.has("risks")}
        onToggle={() => toggleSection("risks")}
        className={cn("border-slate-200", getRiskBgColor(analysis.overall_risk))}
        badge={
          <span
            className={cn(
              "px-2 py-0.5 rounded text-xs font-medium border",
              getRiskColor(analysis.overall_risk)
            )}
          >
            {(analysis.overall_risk || "UNKNOWN").toUpperCase()}
          </span>
        }
      >
        {analysis.weaknesses?.length > 0 && (
          <div className="mb-4">
            <h4 className="text-sm font-medium text-slate-600 mb-2">
              Weaknesses
            </h4>
            <ul className="space-y-1">
              {analysis.weaknesses.map((weakness, i) => (
                <li
                  key={i}
                  className="text-sm text-slate-700 flex items-start gap-2"
                >
                  <span className="text-amber-500 mt-1">•</span>
                  {weakness}
                </li>
              ))}
            </ul>
          </div>
        )}

        {analysis.risks?.length > 0 && (
          <div className="space-y-3">
            {analysis.risks.map((risk, i) => (
              <div
                key={i}
                className="p-3 bg-white rounded-lg border border-slate-200"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm text-slate-700 font-medium">
                    {risk.description}
                  </p>
                  <span
                    className={cn(
                      "px-2 py-0.5 rounded text-xs font-medium border shrink-0",
                      getRiskColor(risk.severity)
                    )}
                  >
                    {(risk.severity || "UNKNOWN").toUpperCase()}
                  </span>
                </div>
                {risk.mitigation && (
                  <p className="text-sm text-slate-600 mt-2">
                    <span className="font-medium">Mitigation:</span>{" "}
                    {risk.mitigation}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </CollapsibleSection>

      {/* Strategy Section */}
      {analysis.recommended && (
        <CollapsibleSection
          title="Recommended Strategy"
          icon={<Target className="h-4 w-4 text-primary" />}
          isExpanded={expandedSections.has("strategy")}
          onToggle={() => toggleSection("strategy")}
          className="border-primary/20 bg-primary/5"
        >
          <div className="space-y-4">
            {/* Main Strategy */}
            <div>
              <h4 className="font-medium text-slate-900">
                {analysis.recommended.name}
              </h4>
              <p className="text-sm text-slate-700 mt-1">
                {analysis.recommended.description}
              </p>

            <div className="flex flex-wrap gap-3 mt-3">
              {analysis.recommended.estimated_cost && (
                <div className="flex items-center gap-1.5 text-sm text-slate-600">
                  <DollarSign className="h-4 w-4" />
                  <span>{analysis.recommended.estimated_cost}</span>
                </div>
              )}
              {analysis.recommended.estimated_timeline && (
                <div className="flex items-center gap-1.5 text-sm text-slate-600">
                  <Calendar className="h-4 w-4" />
                  <span>{analysis.recommended.estimated_timeline}</span>
                </div>
              )}
            </div>

            {(analysis.recommended.pros?.length > 0 ||
              analysis.recommended.cons?.length > 0) && (
              <div className="grid grid-cols-2 gap-4 mt-3">
                {analysis.recommended.pros?.length > 0 && (
                  <div>
                    <h5 className="text-xs font-medium text-green-700 mb-1">
                      Pros
                    </h5>
                    <ul className="text-sm text-slate-600 space-y-0.5">
                      {analysis.recommended.pros.map((pro, i) => (
                        <li key={i}>+ {pro}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {analysis.recommended.cons?.length > 0 && (
                  <div>
                    <h5 className="text-xs font-medium text-red-700 mb-1">
                      Cons
                    </h5>
                    <ul className="text-sm text-slate-600 space-y-0.5">
                      {analysis.recommended.cons.map((con, i) => (
                        <li key={i}>- {con}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Alternative Strategies */}
          {analysis.alternatives?.length > 0 && (
            <div className="pt-3 border-t border-slate-200">
              <h4 className="text-sm font-medium text-slate-600 mb-2">
                Alternatives
              </h4>
              <div className="space-y-2">
                {analysis.alternatives.map((alt, i) => (
                  <div
                    key={i}
                    className="p-2 bg-white rounded border border-slate-200"
                  >
                    <p className="text-sm font-medium text-slate-800">
                      {alt.name}
                    </p>
                    <p className="text-xs text-slate-600 mt-0.5">
                      {alt.description}
                    </p>
                    {(alt.estimated_cost || alt.estimated_timeline) && (
                      <p className="text-xs text-slate-500 mt-1">
                        {alt.estimated_cost && `Cost: ${alt.estimated_cost}`}
                        {alt.estimated_cost && alt.estimated_timeline && " • "}
                        {alt.estimated_timeline &&
                          `Timeline: ${alt.estimated_timeline}`}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </CollapsibleSection>
      )}

      {/* Immediate Actions Section */}
      {analysis.immediate_actions?.length > 0 && (
        <CollapsibleSection
          title="Immediate Actions"
          icon={<ListChecks className="h-4 w-4 text-primary" />}
          isExpanded={expandedSections.has("actions")}
          onToggle={() => toggleSection("actions")}
        >
          <ol className="space-y-2">
            {analysis.immediate_actions.map((action, i) => (
              <li key={i} className="flex items-start gap-3">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary text-sm font-medium shrink-0">
                  {i + 1}
                </span>
                <span className="text-sm text-slate-700 pt-0.5">{action}</span>
              </li>
            ))}
          </ol>
        </CollapsibleSection>
      )}

      {/* Fact Gaps */}
      {analysis.fact_gaps?.length > 0 && (
        <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
          <h4 className="text-sm font-medium text-slate-600 mb-2">
            Information That Would Help
          </h4>
          <ul className="text-sm text-slate-600 space-y-1">
            {analysis.fact_gaps.map((gap, i) => (
              <li key={i}>• {gap}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// Collapsible Section Component
interface CollapsibleSectionProps {
  title: string;
  icon: React.ReactNode;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  className?: string;
  badge?: React.ReactNode;
}

function CollapsibleSection({
  title,
  icon,
  isExpanded,
  onToggle,
  children,
  className,
  badge,
}: CollapsibleSectionProps) {
  return (
    <div className={cn("border rounded-lg overflow-hidden", className)}>
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-3 hover:bg-slate-50/50 transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="font-medium text-slate-900">{title}</span>
          {badge}
        </div>
        {isExpanded ? (
          <ChevronUp className="h-4 w-4 text-slate-500" />
        ) : (
          <ChevronDown className="h-4 w-4 text-slate-500" />
        )}
      </button>
      {isExpanded && (
        <div className="px-3 pb-3 pt-1 border-t border-slate-100">
          {children}
        </div>
      )}
    </div>
  );
}
