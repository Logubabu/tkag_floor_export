import React from 'react';
import { X, Layers, Activity, CheckCircle2 } from 'lucide-react';
import { useStore } from '../store/useStore';
import { ExtractionMode } from '../types';

interface ExtractionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (mode: ExtractionMode) => void;
}

export const ExtractionModal: React.FC<ExtractionModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
}) => {
  const { selectedStory, extractionMode, setExtractionMode, isExtracting } = useStore();

  if (!isOpen) return null;

  const modes: { mode: ExtractionMode; title: string; desc: string; badge: string }[] = [
    {
      mode: 'Mode A — Slab Only',
      title: 'Mode A — Slab Geometry Only',
      desc: 'Extracts floor slabs, slab openings, thickness, area properties, and slab surface loads.',
      badge: 'Basic Geometry',
    },
    {
      mode: 'Mode B — Slab + Supporting Elements',
      title: 'Mode B — Slab + Supporting Structural Elements',
      desc: 'Extracts slabs, openings, beams, supporting columns (above & below), and shear walls.',
      badge: 'Recommended',
    },
    {
      mode: 'Mode C — Complete Floor Model',
      title: 'Mode C — Complete Structural Model',
      desc: 'Extracts full floor system, supporting columns/walls, equivalent spring boundary conditions, live load patterns, and point loads.',
      badge: 'Full Analysis',
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-cyan-400" />
            <div>
              <h2 className="font-semibold text-slate-100 text-sm">Floor Extraction Configuration</h2>
              <p className="text-xs text-slate-400 font-mono">
                Target Floor: <span className="text-cyan-400 font-semibold">{selectedStory?.name || 'Selected Story'}</span>
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

        {/* Modal Body */}
        <div className="p-6 space-y-3">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
            Select Extraction Mode
          </label>

          {modes.map((item) => {
            const isSelected = extractionMode === item.mode;
            return (
              <div
                key={item.mode}
                onClick={() => setExtractionMode(item.mode)}
                className={`p-4 rounded-xl border cursor-pointer transition flex items-start gap-3 ${
                  isSelected
                    ? 'bg-cyan-950/40 border-cyan-500 shadow-md shadow-cyan-950/30'
                    : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="mt-0.5">
                  <CheckCircle2
                    className={`w-5 h-5 ${isSelected ? 'text-cyan-400' : 'text-slate-700'}`}
                  />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="text-xs font-semibold text-slate-200">{item.title}</h3>
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                        isSelected ? 'bg-cyan-900/60 text-cyan-300' : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {item.badge}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">{item.desc}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-950/50 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 transition"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(extractionMode)}
            disabled={isExtracting}
            className="px-5 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg transition shadow-lg shadow-cyan-950/50 flex items-center gap-2"
          >
            {isExtracting ? 'Extracting...' : 'Run Extraction'}
          </button>
        </div>
      </div>
    </div>
  );
};
