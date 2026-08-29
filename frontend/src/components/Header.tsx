import React from 'react';
import { Layers, Download, CheckCircle2, Box, Activity, UploadCloud, FileCode, RotateCcw } from 'lucide-react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';

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
  const {
    activeUnits,
    setActiveUnits,
    selectedStory,
    floorModel,
    validationResult,
    inTool,
    setInTool,
    resetProjectState,
    setProjectId,
    setStories,
    setSelectedStory,
    setFullBuildingModel,
    setViewMode,
  } = useStore();

  const handleResetData = async () => {
    if (confirm('Are you sure you want to reset and clear all uploaded model data?')) {
      try {
        await api.resetAllData();
      } catch {}
      resetProjectState();
      try {
        sessionStorage.clear();
      } catch {}
      window.location.reload();
    }
  };

  const handleConnectApi = async () => {
    try {
      setInTool(false);
      const res = await api.connectEtabsApi();
      if (res.success) {
        if (res.project_id) {
          setProjectId(res.project_id);
        }
        if (Array.isArray(res.stories) && res.stories.length > 0) {
          setStories(res.stories);
          setSelectedStory(res.stories[0]);
        }
        if (res.building_model) {
          setFullBuildingModel(res.building_model);
          setViewMode('full');
        }
        alert(`ETABS COM API Connected Successfully! Loaded ${res.stories_count || (res.stories ? res.stories.length : 0)} stories.`);
      } else {
        alert(
          "Live ETABS COM API Connection Notice:\n\n" +
          (res.message ? `${res.message}\n\n` : "") +
          "Why this happens:\n" +
          "• Inside Docker: Linux containers cannot access Windows COM drivers or desktop apps.\n" +
          "• Native Windows: ETABS must be installed and open on your machine.\n\n" +
          "Solution:\n" +
          "Run 'start_windows_native.bat' on your Windows machine to connect directly to live ETABS 22!"
        );
      }
    } catch (err: any) {
      alert(
        "Live ETABS COM API Connection Notice:\n\n" +
        (err.message ? `${err.message}\n\n` : "") +
        "Run 'start_windows_native.bat' on your Windows machine for live ETABS integration!"
      );
    }
  };

  return (
    <header className="flex flex-col bg-slate-900 border-b border-slate-800 z-20 shrink-0 select-none">
      {/* 1. Top Part: Brand Name & Main Heading Only */}
      <div className="h-12 bg-slate-950/90 border-b border-slate-800/60 flex items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center shadow-md shadow-cyan-950/60">
            <Box className="w-4 h-4 text-white" />
          </div>
          <div className="flex items-center gap-3">
            <h1 className="font-bold text-slate-100 text-sm tracking-wide flex items-center gap-2">
              ETABS <span className="text-cyan-400 font-normal">→</span> RAM Concept
            </h1>
            <span className="text-slate-600">|</span>
            <p className="text-xs text-slate-400 font-mono tracking-tight">
              Floor Extraction & Conversion Platform
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-cyan-300 text-[11px] font-mono">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            Active Engineering Engine
          </span>
        </div>
      </div>

      {/* 2. Second Part: Selection Fields, Toggles & Action Controls */}
      <div className="h-12 bg-slate-900/95 px-6 flex items-center justify-between gap-4 overflow-x-auto overflow-y-hidden">
        {/* Left Side: Selection Fields (Process Mode & Active Units) */}
        <div className="flex items-center gap-3 shrink-0">
          {/* Process Mode Toggle (In-Tool vs Live ETABS) */}
          <div className="flex items-center gap-1 bg-slate-950 px-2 py-1 rounded-lg border border-slate-800 text-xs">
            <span className="text-slate-400 text-[11px] font-mono mr-1 font-medium">Mode:</span>
            <button
              onClick={() => setInTool(true)}
              className={`px-2.5 py-0.5 rounded text-[11px] font-semibold transition ${
                inTool
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-700/60 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="In-Tool: Process files 100% inside web app without requiring ETABS running"
            >
              In-Tool
            </button>
            <button
              onClick={() => setInTool(false)}
              className={`px-2.5 py-0.5 rounded text-[11px] font-semibold transition ${
                !inTool
                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-700/60 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Live ETABS: Connect directly to running ETABS API session"
            >
              Live ETABS
            </button>
          </div>

          {/* Unit Selector */}
          <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800 text-xs">
            <span className="text-slate-400 font-medium mr-0.5 text-[11px]">Units:</span>
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
              className="bg-slate-900 text-cyan-300 font-mono text-[11px] font-semibold focus:outline-none cursor-pointer border border-slate-750 px-2 py-0.5 rounded shadow-sm hover:border-cyan-600 transition"
            >
              <option value="m" className="bg-slate-900 text-slate-100 py-1">m / kN</option>
              <option value="mm" className="bg-slate-900 text-slate-100 py-1">mm / N</option>
              <option value="ft" className="bg-slate-900 text-slate-100 py-1">ft / kip</option>
              <option value="in" className="bg-slate-900 text-slate-100 py-1">in / lb</option>
            </select>
          </div>
        </div>

        {/* Right Side: Action Controls & Modals Trigger Buttons */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Live ETABS API Connection Button */}
          <button
            onClick={handleConnectApi}
            className="flex items-center gap-1.5 px-3 py-1 bg-emerald-950/80 hover:bg-emerald-900 text-emerald-300 border border-emerald-800 cursor-pointer text-[11px] font-semibold rounded-lg transition shadow-sm"
            title="Connect directly to active ETABS application via OAPI"
          >
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            <span>Connect API</span>
          </button>

          {/* Upload File Button */}
          <button
            onClick={onOpenUploadModal}
            className="flex items-center gap-1.5 px-3 py-1 bg-cyan-950/80 hover:bg-cyan-900 text-cyan-300 text-[11px] font-semibold rounded-lg transition border border-cyan-800 shadow-sm"
          >
            <UploadCloud className="w-3.5 h-3.5 text-cyan-400" />
            <span>Upload File</span>
          </button>

          {/* Reset / New Project Button */}
          <button
            onClick={handleResetData}
            className="flex items-center gap-1.5 px-2.5 py-1 bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 text-[11px] font-semibold rounded-lg transition border border-rose-900/80 shadow-sm"
            title="Reset and clear all uploaded data & models to start fresh"
          >
            <RotateCcw className="w-3.5 h-3.5 text-rose-400" />
            <span>Reset Data</span>
          </button>

          {/* Floor Extraction Button */}
          <button
            onClick={onOpenExtractionModal}
            disabled={!selectedStory}
            className="flex items-center gap-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-[11px] font-medium rounded-lg transition border border-slate-700 shadow-sm"
          >
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
            <span>Extract Mode</span>
          </button>

          {/* Validation Button */}
          <button
            onClick={onOpenValidationModal}
            disabled={!floorModel}
            className="flex items-center gap-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-[11px] font-medium rounded-lg transition border border-slate-700 shadow-sm"
          >
            <CheckCircle2 className={`w-3.5 h-3.5 ${validationResult?.is_valid ? 'text-emerald-400' : 'text-amber-400'}`} />
            <span>Validate</span>
          </button>

          {/* Geometry Comparison Button */}
          <button
            onClick={onOpenComparisonModal}
            disabled={!floorModel}
            className="flex items-center gap-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-indigo-300 text-[11px] font-semibold rounded-lg transition border border-indigo-900 shadow-sm"
            title="Compare source ETABS floor geometry against target RAM Concept geometry"
          >
            <Activity className="w-3.5 h-3.5 text-indigo-400" />
            <span>Compare</span>
          </button>

          {/* RAM Concept Model Pre-Export Viewer Button */}
          <button
            onClick={onOpenRamViewerModal}
            disabled={!floorModel}
            className="flex items-center gap-1.5 px-3 py-1 bg-cyan-950/80 hover:bg-cyan-900 disabled:opacity-50 text-cyan-300 text-[11px] font-semibold rounded-lg transition border border-cyan-800 shadow-sm"
            title="Interactive 3D preview of the target RAM Concept model before exporting"
          >
            <Box className="w-3.5 h-3.5 text-cyan-400" />
            <span>Preview RAM</span>
          </button>

          {/* View Exported Files Button */}
          <button
            onClick={onOpenExportedFilesModal}
            disabled={!floorModel}
            className="flex items-center gap-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-cyan-300 text-[11px] font-semibold rounded-lg transition border border-slate-700 shadow-sm"
            title="Inspect generated .DXF, .CPT, .PY, and .JSON exported output files"
          >
            <FileCode className="w-3.5 h-3.5 text-cyan-400" />
            <span>View Files</span>
          </button>

          {/* RAM Concept Export Button */}
          <button
            onClick={onOpenExportModal}
            disabled={!floorModel}
            className="flex items-center gap-1.5 px-3.5 py-1 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50 text-white text-[11px] font-semibold rounded-lg transition shadow-md shadow-cyan-950/40"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export RAM Concept</span>
          </button>
        </div>
      </div>
    </header>
  );
};
