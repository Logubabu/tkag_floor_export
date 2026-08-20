import React from 'react';
import { X, AlertTriangle, CheckCircle2, AlertOctagon, HelpCircle } from 'lucide-react';
import { useStore } from '../store/useStore';

interface ValidationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ValidationCard: React.FC<ValidationModalProps> = ({ isOpen, onClose }) => {
  const { validationResult, floorModel } = useStore();

  if (!isOpen || !validationResult) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200 flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <CheckCircle2
              className={`w-5 h-5 ${validationResult.is_valid ? 'text-emerald-400' : 'text-amber-400'}`}
            />
            <div>
              <h2 className="font-semibold text-slate-100 text-sm">Engineering Data Validation Report</h2>
              <p className="text-xs text-slate-400 font-mono">
                Floor: <span className="text-cyan-400">{floorModel?.story.name}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Summary Badges */}
        <div className="p-6 border-b border-slate-800 bg-slate-950/40 grid grid-cols-4 gap-3 text-xs">
          <div className="bg-slate-900 p-3 rounded-xl border border-slate-800">
            <span className="text-slate-400 block mb-1">Status</span>
            <span
              className={`font-semibold font-mono ${
                validationResult.is_valid ? 'text-emerald-400' : 'text-amber-400'
              }`}
            >
              {validationResult.is_valid ? 'PASS' : 'WARNINGS'}
            </span>
          </div>

          <div className="bg-slate-900 p-3 rounded-xl border border-slate-800">
            <span className="text-slate-400 block mb-1">Errors</span>
            <span className="font-semibold font-mono text-rose-400">
              {validationResult.summary.errors}
            </span>
          </div>

          <div className="bg-slate-900 p-3 rounded-xl border border-slate-800">
            <span className="text-slate-400 block mb-1">Warnings</span>
            <span className="font-semibold font-mono text-amber-400">
              {validationResult.summary.warnings}
            </span>
          </div>

          <div className="bg-slate-900 p-3 rounded-xl border border-slate-800">
            <span className="text-slate-400 block mb-1">Extracted Slabs</span>
            <span className="font-semibold font-mono text-cyan-400">
              {validationResult.summary.slabs}
            </span>
          </div>
        </div>

        {/* Alerts List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3">
          {validationResult.alerts.length === 0 ? (
            <div className="p-8 text-center bg-slate-950/50 rounded-xl border border-slate-850">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2 opacity-80" />
              <p className="text-xs font-semibold text-slate-200">No Validation Issues Detected</p>
              <p className="text-[11px] text-slate-400 mt-1">
                Extracted floor geometry and properties satisfy all RAM Concept structural import requirements.
              </p>
            </div>
          ) : (
            validationResult.alerts.map((alert, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-xl border flex items-start gap-3.5 text-xs ${
                  alert.level === 'ERROR'
                    ? 'bg-rose-950/30 border-rose-900/60 text-rose-200'
                    : alert.level === 'WARNING'
                    ? 'bg-amber-950/30 border-amber-900/60 text-amber-200'
                    : 'bg-slate-950 border-slate-800 text-slate-300'
                }`}
              >
                {alert.level === 'ERROR' ? (
                  <AlertOctagon className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                )}

                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold">{alert.element_type} [{alert.element_id}]</span>
                    <span className="font-mono text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-slate-900">
                      {alert.level}
                    </span>
                  </div>
                  <p className="text-slate-300 mb-2">{alert.message}</p>

                  <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80 text-[11px] flex items-start gap-2">
                    <HelpCircle className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="text-cyan-400 font-medium">Suggested Action: </span>
                      <span className="text-slate-400">{alert.action_tip}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-950/50 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition"
          >
            Close Report
          </button>
        </div>
      </div>
    </div>
  );
};
