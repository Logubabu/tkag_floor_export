import React from 'react';
import { Layers, Download, CheckCircle2, Box, Activity, UploadCloud, FileCode } from 'lucide-react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import { formatLength } from '../utils/unitConverter';

interface HeaderProps {
  onOpenUploadModal: () => void;
  onOpenExtractionModal: () => void;
  onOpenValidationModal: () => void;
  onOpenExportModal: () => void;
  onOpenComparisonModal: () => void;
  onOpenRamViewerModal: () => void;
  onOpenExportedFilesModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenUploadModal,
  onOpenExtractionModal,
  onOpenValidationModal,
  onOpenExportModal,
  onOpenComparisonModal,
  onOpenRamViewerModal,
  onOpenExportedFilesModal,
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
            Elev: <span className="text-slate-200 font-mono">{formatLength(selectedStory.elevation, activeUnits.length)}</span>
          </div>
          <div className="w-px h-3 bg-slate-800" />
          <div className="text-slate-400">
            Height: <span className="text-slate-200 font-mono">{formatLength(selectedStory.height, activeUnits.length)}</span>
          </div>
        </div>
      )}

      {/* Actions & Unit Selector */}
      <div className="flex items-center gap-3">
        {/* Unit Selector */}
        <div className="flex items-center gap-1.5 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 text-xs">
          <span className="text-slate-400 font-medium mr-0.5">Units:</span>
          <select
            value={activeUnits.length}
            onChange={(e) => {
              const val = e.target.value;
              let forceVal = 'kN';
              if (val === 'mm') forceVal = 'N';
              else if (val === 'ft') forceVal = 'kip';
              else if (val === 'in') forceVal = 'lb';
              setActiveUnits({ length: val, force: forceVal });
            }}
            className="bg-slate-900 text-cyan-300 font-mono font-semibold focus:outline-none cursor-pointer border border-slate-750 px-2 py-0.5 rounded shadow-sm hover:border-cyan-600 transition"
          >
            <option value="m" className="bg-slate-900 text-slate-100 py-1">m / kN</option>
            <option value="mm" className="bg-slate-900 text-slate-100 py-1">mm / N</option>
            <option value="ft" className="bg-slate-900 text-slate-100 py-1">ft / kip</option>
            <option value="in" className="bg-slate-900 text-slate-100 py-1">in / lb</option>
          </select>
        </div>

        {/* Live ETABS API Connection Button */}
        <button
          onClick={async () => {
            try {
              const res = await api.connectEtabsApi();
              alert(`ETABS COM API Connected Successfully! Loaded ${res.stories_count} stories.`);
              window.location.reload();
            } catch (err: any) {
              alert(err.message || 'Failed to connect to live ETABS COM session.');
            }
          }}
          className="flex items-center gap-2 px-3 py-1.5 bg-emerald-950/80 hover:bg-emerald-900 text-emerald-300 text-xs font-semibold rounded-lg transition border border-emerald-800 shadow-sm"
          title="Connect directly to active ETABS application via OAPI"
        >
          <Activity className="w-4 h-4 text-emerald-400" />
          <span>Connect ETABS (API)</span>
        </button>

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

        {/* Geometry Comparison Button */}
        <button
          onClick={onOpenComparisonModal}
          disabled={!floorModel}
          className="flex items-center gap-2 px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-indigo-300 text-xs font-semibold rounded-lg transition border border-indigo-900 shadow-sm"
          title="Compare source ETABS floor geometry against target RAM Concept geometry"
        >
          <Activity className="w-4 h-4 text-indigo-400" />
          <span>Compare Geometry</span>
        </button>

        {/* RAM Concept Model Pre-Export Viewer Button */}
        <button
          onClick={onOpenRamViewerModal}
          disabled={!floorModel}
          className="flex items-center gap-2 px-3 py-1.5 bg-cyan-950/80 hover:bg-cyan-900 disabled:opacity-50 text-cyan-300 text-xs font-semibold rounded-lg transition border border-cyan-800 shadow-sm"
          title="Interactive 3D preview of the target RAM Concept model before exporting"
        >
          <Box className="w-4 h-4 text-cyan-400" />
          <span>Preview RAM Model</span>
        </button>

        {/* View Exported Files Button */}
        <button
          onClick={onOpenExportedFilesModal}
          disabled={!floorModel}
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-cyan-300 text-xs font-semibold rounded-lg transition border border-slate-700 shadow-sm"
          title="Inspect generated .DXF, .CPT, .PY, and .JSON exported output files"
        >
          <FileCode className="w-4 h-4 text-cyan-400" />
          <span>View Exported Files</span>
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
