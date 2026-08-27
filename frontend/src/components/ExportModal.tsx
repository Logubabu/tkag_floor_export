import React, { useState } from 'react';
import { X, Download, FileCode, Layers, FileText, CheckCircle2, Terminal } from 'lucide-react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ExportModal: React.FC<ExportModalProps> = ({ isOpen, onClose }) => {
  const { activeProjectId, stories, selectedStory, selectedStoryIds } = useStore();
  const [isExporting, setIsExporting] = useState(false);
  const [exportDxf, setExportDxf] = useState(true);
  const [exportCpt, setExportCpt] = useState(false);
  const [exportJson, setExportJson] = useState(false);
  const [exportPy, setExportPy] = useState(false);

  if (!isOpen) return null;

  // Filter selected stories or default to currently viewed floor or all floors
  const selectedStoriesFromCheckboxes = stories.filter((s) => selectedStoryIds.includes(s.id));
  const floorsToExport = selectedStoriesFromCheckboxes.length > 0
    ? selectedStoriesFromCheckboxes
    : (selectedStory ? [selectedStory] : stories);

  const handleDownloadPackage = async () => {
    if (floorsToExport.length === 0) {
      alert('Please select at least one floor for extraction & export.');
      return;
    }

    if (!exportDxf && !exportCpt && !exportJson && !exportPy) {
      alert('Please select at least one file format to export (DXF or CPT).');
      return;
    }

    setIsExporting(true);
    try {
      // 1. Ensure selected floors are extracted first
      const storyNames = floorsToExport.map((s) => s.name);
      const batchRes = await api.extractBatchFloors(
        activeProjectId,
        storyNames,
        useStore.getState().extractionMode
      );

      const floorIds = batchRes.extracted_floors.map((item: any) => item.floor_id);

      // 2. Trigger direct browser download with format selection
      await api.downloadRamPackage(activeProjectId, floorIds, {
        include_dxf: exportDxf,
        include_cpt: exportCpt,
        include_json: exportJson,
        include_py: exportPy,
      });
    } catch (err: any) {
      alert(`Export error: ${err.message}`);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Download className="w-5 h-5 text-cyan-400" />
            <div>
              <h2 className="font-semibold text-slate-100 text-sm">RAM Concept Export Manager</h2>
              <p className="text-xs text-slate-400 font-mono">
                Selected: <span className="text-cyan-400 font-bold">{floorsToExport.length} Floor(s)</span>
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

        {/* Body */}
        <div className="p-6 space-y-4 text-xs">
          {/* Selected Floors Summary List */}
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-200 flex items-center gap-2">
                <Layers className="w-4 h-4 text-cyan-400" />
                Selected Floors to Extract ({floorsToExport.length})
              </h3>
            </div>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {floorsToExport.map((s) => (
                <span
                  key={s.id}
                  className="px-2.5 py-1 bg-cyan-950/60 border border-cyan-800/60 text-cyan-300 rounded-md font-mono text-[11px]"
                >
                  {s.name} ({s.elevation}m)
                </span>
              ))}
            </div>
          </div>

          {/* Select Output File Formats */}
          <div className="space-y-2">
            <h3 className="font-semibold text-slate-200 text-xs">Select Output File Formats:</h3>

            {/* DXF Option */}
            <label className={`p-3 rounded-lg border flex items-center justify-between cursor-pointer transition ${
              exportDxf ? 'bg-cyan-950/40 border-cyan-700/60' : 'bg-slate-950/40 border-slate-800 hover:border-slate-700'
            }`}>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={exportDxf}
                  onChange={(e) => setExportDxf(e.target.checked)}
                  className="w-4 h-4 rounded accent-cyan-500"
                />
                <FileText className="w-5 h-5 text-cyan-400 shrink-0" />
                <div>
                  <p className="font-semibold text-slate-200">AutoCAD Drawing Exchange (.DXF)</p>
                  <p className="text-[11px] text-slate-400">
                    RAM Concept standard layer mapped: SLAB_OUTLINE, OPENINGS, COLUMNS, BEAMS
                  </p>
                </div>
              </div>
            </label>

            {/* CPT Option */}
            <label className={`p-3 rounded-lg border flex items-center justify-between cursor-pointer transition ${
              exportCpt ? 'bg-cyan-950/40 border-cyan-700/60' : 'bg-slate-950/40 border-slate-800 hover:border-slate-700'
            }`}>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={exportCpt}
                  onChange={(e) => setExportCpt(e.target.checked)}
                  className="w-4 h-4 rounded accent-cyan-500"
                />
                <FileCode className="w-5 h-5 text-emerald-400 shrink-0" />
                <div>
                  <p className="font-semibold text-slate-200">RAM Concept Native File (.CPT)</p>
                  <p className="text-[11px] text-slate-400">
                    Direct RAM Concept model file format
                  </p>
                </div>
              </div>
            </label>

            {/* Python Automation Script Option */}
            <label className={`p-3 rounded-lg border flex items-center justify-between cursor-pointer transition ${
              exportPy ? 'bg-cyan-950/40 border-cyan-700/60' : 'bg-slate-950/40 border-slate-800 hover:border-slate-700'
            }`}>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={exportPy}
                  onChange={(e) => setExportPy(e.target.checked)}
                  className="w-4 h-4 rounded accent-cyan-500"
                />
                <Terminal className="w-5 h-5 text-purple-400 shrink-0" />
                <div>
                  <p className="font-semibold text-slate-200">RAM Concept Python COM Automation Script (.PY)</p>
                  <p className="text-[11px] text-slate-400">
                    Automated Python macro script using RAM Concept COM API
                  </p>
                </div>
              </div>
            </label>

            {/* Intermediate JSON Option */}
            <label className={`p-3 rounded-lg border flex items-center justify-between cursor-pointer transition ${
              exportJson ? 'bg-cyan-950/40 border-cyan-700/60' : 'bg-slate-950/40 border-slate-800 hover:border-slate-700'
            }`}>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={exportJson}
                  onChange={(e) => setExportJson(e.target.checked)}
                  className="w-4 h-4 rounded accent-cyan-500"
                />
                <FileCode className="w-5 h-5 text-amber-400 shrink-0" />
                <div>
                  <p className="font-semibold text-slate-200">Intermediate Structural Model (.JSON)</p>
                  <p className="text-[11px] text-slate-400">
                    Structured floor schema containing slabs, beams, columns, walls, & loads
                  </p>
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-950/50 flex justify-between items-center gap-3">
          <button
            onClick={async () => {
              if (floorsToExport.length === 0) return alert('Select a story first.');
              try {
                const sName = floorsToExport[0].name;
                const batchRes = await api.extractBatchFloors(activeProjectId, [sName], useStore.getState().extractionMode);
                const fid = batchRes.extracted_floors[0].floor_id;
                const pushRes = await api.exportLiveRamConcept(activeProjectId, fid);
                alert(pushRes.message || 'Pushed to live RAM Concept COM API!');
              } catch (e: any) {
                alert(e.message || 'Failed to push to RAM Concept COM session.');
              }
            }}
            disabled={floorsToExport.length === 0}
            className="px-4 py-2 bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-800 text-emerald-300 text-xs font-semibold rounded-lg transition"
            title="Push selected floor directly into active RAM Concept application via COM API"
          >
            Push to RAM Concept (COM API)
          </button>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 transition"
            >
              Close
            </button>
            <button
              onClick={handleDownloadPackage}
              disabled={isExporting || floorsToExport.length === 0}
              className="px-5 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg transition shadow-lg shadow-cyan-950/50 flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              <span>
                {isExporting
                  ? 'Preparing ZIP Package...'
                  : `Download Package (${floorsToExport.length} Floor${floorsToExport.length > 1 ? 's' : ''})`}
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
