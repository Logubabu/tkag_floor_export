import React from 'react';
import { Layers, Download, CheckCircle2, Box, Activity, UploadCloud } from 'lucide-react';
import { useStore } from '../store/useStore';

interface HeaderProps {
  onOpenUploadModal: () => void;
  onOpenExtractionModal: () => void;
  onOpenValidationModal: () => void;
  onOpenExportModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenUploadModal,
  onOpenExtractionModal,
  onOpenValidationModal,
  onOpenExportModal,
}) => {
  const { activeUnits, setActiveUnits, selectedStory, floorModel, validationResult } = useStore();

  return (
    <header className="h-16 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-6 z-20 shrink-0">
      {/* Brand & Project Identity */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-950/50">
          <Box className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="font-semibold text-slate-100 text-sm tracking-wide flex items-center gap-2">
            ETABS <span className="text-slate-500 font-normal">→</span> RAM Concept
          </h1>
          <p className="text-xs text-slate-400 font-mono">Floor Extraction & Conversion Platform</p>
        </div>
      </div>

      {/* Active Story & Extraction Quick Status */}
      {selectedStory && (
        <div className="hidden md:flex items-center gap-4 bg-slate-950/60 px-4 py-1.5 rounded-lg border border-slate-800 text-xs">
          <div className="flex items-center gap-2 text-cyan-400 font-medium">
            <Layers className="w-4 h-4" />
            <span>{selectedStory.name}</span>
          </div>
          <div className="w-px h-3 bg-slate-800" />
          <div className="text-slate-400">
            Elev: <span className="text-slate-200 font-mono">{selectedStory.elevation} m</span>
          </div>
          <div className="w-px h-3 bg-slate-800" />
          <div className="text-slate-400">
            Height: <span className="text-slate-200 font-mono">{selectedStory.height} m</span>
          </div>
        </div>
      )}

      {/* Actions & Unit Selector */}
      <div className="flex items-center gap-3">
        {/* Unit Selector */}
        <div className="flex items-center gap-1 bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800 text-xs">
          <span className="text-slate-500 font-medium mr-1">Units:</span>
          <select
            value={activeUnits.length}
            onChange={(e) => setActiveUnits({ ...activeUnits, length: e.target.value })}
            className="bg-transparent text-slate-200 font-mono focus:outline-none cursor-pointer"
          >
            <option value="m">m / kN</option>
            <option value="mm">mm / N</option>
            <option value="ft">ft / kip</option>
            <option value="in">in / lb</option>
          </select>
        </div>

        {/* Upload File Button */}
        <button
          onClick={onOpenUploadModal}
          className="flex items-center gap-2 px-3.5 py-1.5 bg-cyan-950/80 hover:bg-cyan-900 text-cyan-300 text-xs font-semibold rounded-lg transition border border-cyan-800 shadow-sm"
        >
          <UploadCloud className="w-4 h-4 text-cyan-400" />
          <span>Upload .E2K File</span>
        </button>

        {/* Floor Extraction Button */}
        <button
          onClick={onOpenExtractionModal}
          disabled={!selectedStory}
          className="flex items-center gap-2 px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-medium rounded-lg transition border border-slate-700 shadow-sm"
        >
          <Activity className="w-4 h-4 text-cyan-400" />
          <span>Extract Mode</span>
        </button>

        {/* Validation Button */}
        <button
          onClick={onOpenValidationModal}
          disabled={!floorModel}
          className="flex items-center gap-2 px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-medium rounded-lg transition border border-slate-700 shadow-sm"
        >
          <CheckCircle2 className={`w-4 h-4 ${validationResult?.is_valid ? 'text-emerald-400' : 'text-amber-400'}`} />
          <span>Validate</span>
        </button>

        {/* RAM Concept Export Button */}
        <button
          onClick={onOpenExportModal}
          disabled={!floorModel}
          className="flex items-center gap-2 px-4 py-1.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg transition shadow-md shadow-cyan-950/40"
        >
          <Download className="w-4 h-4" />
          <span>Export RAM Concept</span>
        </button>
      </div>
    </header>
  );
};
