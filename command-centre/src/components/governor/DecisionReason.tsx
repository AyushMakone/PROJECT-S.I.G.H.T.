import React from 'react';
import { GovernorDecision } from '../../types';
import { CheckCircle2, XCircle, ShieldCheck, AlertCircle } from 'lucide-react';

interface DecisionReasonProps {
  governorDecision: GovernorDecision;
  className?: string;
}

export const DecisionReason: React.FC<DecisionReasonProps> = ({
  governorDecision,
  className = ''
}) => {
  const { reason, action, evaluatedConditions } = governorDecision;

  const conditionsList = [
    {
      key: 'communicationAvailable',
      label: 'Communication available',
      value: evaluatedConditions.communicationAvailable
    },
    {
      key: 'batteryAboveThreshold',
      label: 'Battery above threshold',
      value: evaluatedConditions.batteryAboveThreshold
    },
    {
      key: 'relevantObject',
      label: 'Relevant object',
      value: evaluatedConditions.relevantObject
    },
    {
      key: 'insidePriorityZone',
      label: 'Inside priority zone',
      value: evaluatedConditions.insidePriorityZone
    },
    {
      key: 'persistenceSatisfied',
      label: 'Persistence satisfied',
      value: evaluatedConditions.persistenceSatisfied
    },
    {
      key: 'evidenceRequired',
      label: 'Evidence required',
      value: evaluatedConditions.evidenceRequired
    }
  ];

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Reason Box */}
      <div className="bg-[#0b1019] rounded-lg p-4 border border-slate-800">
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400 uppercase tracking-wider mb-1.5">
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          <span>Evaluation Reason</span>
        </div>
        <p className="text-sm font-medium text-slate-200 leading-relaxed font-sans">
          {reason}
        </p>

        <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-start gap-2">
          <span className="text-[11px] font-mono text-cyan-400 uppercase font-bold shrink-0">
            Action:
          </span>
          <span className="text-xs text-slate-300 font-mono">{action}</span>
        </div>
      </div>

      {/* Evaluated Conditions Matrix */}
      <div className="bg-[#0b1019] rounded-lg p-4 border border-slate-800">
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs font-mono text-slate-400 uppercase tracking-wider">
            Evaluated Conditions
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            6 RULES EVALUATED
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 font-mono">
          {conditionsList.map((cond) => (
            <div
              key={cond.key}
              className="flex items-center justify-between p-2.5 rounded bg-[#0e1522] border border-slate-800/60"
            >
              <span className="text-xs text-slate-300">{cond.label}</span>
              <span
                className={`flex items-center gap-1 text-xs font-bold ${
                  cond.value ? 'text-emerald-400' : 'text-slate-400'
                }`}
              >
                {cond.value ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    YES
                  </>
                ) : (
                  <>
                    <XCircle className="w-3.5 h-3.5 text-slate-400" />
                    NO
                  </>
                )}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Architecture Separation Notice */}
      <div className="flex items-start gap-2 p-3 rounded bg-slate-900/60 border border-slate-800/80 text-[11px] text-slate-400">
        <AlertCircle className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
        <div>
          <strong className="text-slate-300">Modular Architecture Notice:</strong> Ground Command Centre only displays Governor outcomes. Deterministic rule evaluation executes onboard the UAV via <code className="text-cyan-300">sight-core</code>.
        </div>
      </div>
    </div>
  );
};
