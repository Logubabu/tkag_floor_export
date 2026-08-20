import React from 'react';
import { Info, Box, Tag, Ruler, Cpu, X } from 'lucide-react';
import { useStore } from '../store/useStore';

export const PropertyPanel: React.FC = () => {
  const { selectedElement, setSelectedElement, floorModel } = useStore();

  if (!selectedElement) {
    return (
      <aside className="w-80 bg-slate-900 border-l border-slate-800 p-6 flex flex-col items-center justify-center text-center z-10 shrink-0">
        <div className="w-12 h-12 rounded-full bg-slate-800/80 flex items-center justify-center mb-3 text-slate-500">
          <Info className="w-6 h-6" />
        </div>
        <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
          Element Property Inspector
        </h3>
        <p className="text-xs text-slate-400 max-w-[200px]">
          Click any slab, beam, column, or wall in the 3D view to inspect geometry and structural properties.
        </p>
      </aside>
    );
  }

  return (
    <aside className="w-80 bg-slate-900 border-l border-slate-800 flex flex-col h-full z-10 shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Box className="w-4 h-4 text-cyan-400" />
          <h2 className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
            {selectedElement.type} Details
          </h2>
        </div>
        <button
          onClick={() => setSelectedElement(null)}
          className="p-1 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Details List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex items-center justify-between">
          <span className="text-slate-400 font-medium">Element Tag ID:</span>
          <span className="font-mono text-cyan-400 font-bold">{selectedElement.id}</span>
        </div>

        <div className="space-y-2">
          <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Structural Attributes
          </h4>
          <div className="bg-slate-950/60 rounded-lg border border-slate-800 divide-y divide-slate-800/80">
            {Object.entries(selectedElement.details).map(([key, val]) => (
              <div key={key} className="flex items-center justify-between p-2.5">
                <span className="text-slate-400 capitalize">{key.replace('_', ' ')}:</span>
                <span className="font-mono text-slate-200">{String(val)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Source ETABS Traceability note */}
        <div className="bg-cyan-950/30 border border-cyan-900/50 p-3 rounded-lg text-[11px] text-cyan-300">
          <p className="font-medium flex items-center gap-1.5 mb-1">
            <Cpu className="w-3.5 h-3.5" />
            Source Model Traceability
          </p>
          <p className="text-cyan-400/80 leading-relaxed">
            Mapped directly from ETABS source object <code className="bg-cyan-950 px-1 py-0.5 rounded text-cyan-200">{selectedElement.id}</code>. Preserved for RAM Concept export traceability.
          </p>
        </div>
      </div>
    </aside>
  );
};
