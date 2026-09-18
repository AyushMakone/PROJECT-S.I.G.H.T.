import React from 'react';
import { useSimulation } from '../../hooks/useSimulation';
import { DecisionBadge } from '../governor/DecisionBadge';
import { ShieldCheck, ArrowRight, CheckCircle2, XCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

export const GovernorStatus: React.FC = () => {
  const { governor } = useSimulation();

  const cond = governor.evaluatedConditions;

  return (
    <div className="bg-[#0b1019] rounded-xl p-4 border border-slate-800 font-mono flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            <span className="text-xs text-slate-300 font-bold uppercase tracking-wider">
              CURRENT GOVERNOR DECISION
            </span>
          </div>
          <Link
            to="/governor"
            className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
          >
            <span>Details</span>
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>

        {/* Hero Decision display */}
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-3">
            <DecisionBadge decision={governor.decision} size="lg" pulse={true} />
            <div className="text-xs">
              <span className="text-[10px] text-slate-400 block uppercase">EVALUATED AT</span>
              <span className="text-slate-200 font-semibold">{governor.timestamp}</span>
            </div>
          </div>
        </div>

        {/* Reason summary */}
        <p className="text-xs text-slate-300 font-sans leading-relaxed mb-3">
          {governor.reason}
        </p>

        {/* Evaluated Conditions Quick Matrix */}
        <div className="grid grid-cols-2 gap-1.5 text-[11px] pt-2 border-t border-slate-800/80">
          <div className="flex items-center justify-between p-1.5 rounded bg-[#0d1422]">
            <span className="text-slate-400 truncate">Relevant Object:</span>
            <span className={cond.relevantObject ? 'text-emerald-400 font-bold' : 'text-slate-400'}>
              {cond.relevantObject ? 'YES' : 'NO'}
            </span>
          </div>

          <div className="flex items-center justify-between p-1.5 rounded bg-[#0d1422]">
            <span className="text-slate-400 truncate">Priority Zone:</span>
            <span className={cond.insidePriorityZone ? 'text-emerald-400 font-bold' : 'text-slate-400'}>
              {cond.insidePriorityZone ? 'YES' : 'NO'}
            </span>
          </div>

          <div className="flex items-center justify-between p-1.5 rounded bg-[#0d1422]">
            <span className="text-slate-400 truncate">Persistence:</span>
            <span className={cond.persistenceSatisfied ? 'text-emerald-400 font-bold' : 'text-slate-400'}>
              {cond.persistenceSatisfied ? 'YES' : 'NO'}
            </span>
          </div>

          <div className="flex items-center justify-between p-1.5 rounded bg-[#0d1422]">
            <span className="text-slate-400 truncate">Evidence Req:</span>
            <span className={cond.evidenceRequired ? 'text-purple-400 font-bold' : 'text-slate-400'}>
              {cond.evidenceRequired ? 'YES' : 'NO'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
