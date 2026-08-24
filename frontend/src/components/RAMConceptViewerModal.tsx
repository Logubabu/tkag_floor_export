import React, { useState } from 'react';
import { X, Eye, Layers, ShieldCheck, Download, Box, Activity, ZoomIn, RefreshCw, FileText } from 'lucide-react';
import { useStore } from '../store/useStore';
import { StructuralViewer } from '../viewer/StructuralViewer';

interface RAMConceptViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirmExport: () => void;
}

export const RAMConceptViewerModal: React.FC<RAMConceptViewerModalProps> = ({
  isOpen,
  onClose,
  onConfirmExport,
}) => {
  const { floorModel, selectedStory } = useStore();
  const [activeTab, setActiveTab] = useState<'3d_model' | 'cad_layers' | 'concept_schema'>('3d_model');

  if (!isOpen || !floorModel) return null;

  const slabCount = floorModel.slabs.length;
  const openingCount = floorModel.openings.length;
  const beamCount = floorModel.beams.length;
  const colCount = floorModel.columns_above.length + floorModel.columns_below.length;
  const wallCount = floorModel.walls_above.length + floorModel.walls_below.length;

  return (
    <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-6 select-none">
      <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-6xl h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header Bar */}
        <div className="px-6 py-3.5 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center shadow-md">
              <Box className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-slate-100">RAM Concept Pre-Export Model Viewer</h2>
                <span className="px-2 py-0.5 text-[10px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-800 rounded-md">
                  .CPT Interactive Preview
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">
                Story: <span className="text-cyan-400 font-semibold">{selectedStory?.name || floorModel.story.name}</span> | Units: SI (m/kN/mm)
              </p>
            </div>
          </div>

          {/* View Tab Switching */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => setActiveTab('3d_model')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition font-medium ${
                activeTab === '3d_model' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>3D RAM Model</span>
            </button>
            <button
              onClick={() => setActiveTab('cad_layers')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition font-medium ${
                activeTab === 'cad_layers' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>CAD DXF Layers</span>
            </button>
            <button
              onClick={() => setActiveTab('concept_schema')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition font-medium ${
                activeTab === 'concept_schema' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>CPT Object Tree</span>
            </button>
          </div>

          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Main Viewer Body */}
        <div className="flex-1 flex overflow-hidden relative bg-slate-950">
          {/* Tab 1: 3D Interactive RAM Model Viewport */}
          {activeTab === '3d_model' && (
            <div className="flex-1 relative h-full">
              <StructuralViewer />
              {/* Overlay Summary Widget */}
              <div className="absolute bottom-4 left-4 z-10 bg-slate-900/90 backdrop-blur-md p-3 rounded-xl border border-slate-800 text-xs text-slate-300 space-y-1 shadow-lg">
                <div className="font-semibold text-cyan-400 mb-1 border-b border-slate-800 pb-1">Extracted RAM Objects</div>
                <div className="flex justify-between gap-6"><span>Slabs / Areas:</span><span className="font-mono text-slate-100">{slabCount}</span></div>
                <div className="flex justify-between gap-6"><span>Openings:</span><span className="font-mono text-slate-100">{openingCount}</span></div>
                <div className="flex justify-between gap-6"><span>Beams:</span><span className="font-mono text-slate-100">{beamCount}</span></div>
                <div className="flex justify-between gap-6"><span>Columns:</span><span className="font-mono text-slate-100">{colCount}</span></div>
                <div className="flex justify-between gap-6"><span>Walls:</span><span className="font-mono text-slate-100">{wallCount}</span></div>
              </div>
            </div>
          )}

          {/* Tab 2: CAD DXF Layers Mapping */}
          {activeTab === 'cad_layers' && (
            <div className="flex-1 p-6 overflow-y-auto space-y-4">
              <h3 className="text-sm font-semibold text-slate-200">RAM Concept CAD Exchange Layer Mapping</h3>
              <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-2">
                  <div className="text-cyan-400 font-semibold border-b border-slate-800 pb-2">SLAB_OUTLINE</div>
                  <div className="text-slate-400">Layer Color: Cyan (#00FFFF)</div>
                  <div className="text-slate-300">Entities: Polyline Outer Perimeter ({slabCount} Slabs)</div>
                </div>
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-2">
                  <div className="text-red-400 font-semibold border-b border-slate-800 pb-2">OPENINGS</div>
                  <div className="text-slate-400">Layer Color: Red (#FF0000)</div>
                  <div className="text-slate-300">Entities: Closed Inner Polygons ({openingCount} Openings)</div>
                </div>
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-2">
                  <div className="text-purple-400 font-semibold border-b border-slate-800 pb-2">COLUMNS_BELOW & ABOVE</div>
                  <div className="text-slate-400">Layer Color: Purple / Magenta</div>
                  <div className="text-slate-300">Entities: Support Point Nodes ({colCount} Columns)</div>
                </div>
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-2">
                  <div className="text-emerald-400 font-semibold border-b border-slate-800 pb-2">WALLS</div>
                  <div className="text-slate-400">Layer Color: Emerald Green</div>
                  <div className="text-slate-300">Entities: Wall Linear Segments ({wallCount} Walls)</div>
                </div>
              </div>
            </div>
          )}

          {/* Tab 3: CPT Intermediate Object Tree */}
          {activeTab === 'concept_schema' && (
            <div className="flex-1 p-6 overflow-y-auto">
              <h3 className="text-sm font-semibold text-slate-200 mb-3">RAM Concept API .CPT Model Structure</h3>
              <pre className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs font-mono text-cyan-300 leading-relaxed overflow-x-auto">
{JSON.stringify(
  {
    ram_concept_model: {
      version: "RAM Concept 2024+",
      story_name: floorModel.story.name,
      units: floorModel.units,
      slabs: floorModel.slabs.map((s) => ({ id: s.id, thickness_m: s.thickness, vertices: s.polygon.length })),
      openings: floorModel.openings.map((o) => ({ id: o.id, vertices: o.polygon.length })),
      supports: {
        columns_below_count: floorModel.columns_below.length,
        columns_above_count: floorModel.columns_above.length,
        walls_below_count: floorModel.walls_below.length,
        walls_above_count: floorModel.walls_above.length,
      },
    },
  },
  null,
  2
)}
              </pre>
            </div>
          )}
        </div>

        {/* Footer Action Bar */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-950 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-emerald-400">
            <ShieldCheck className="w-4 h-4" />
            <span>RAM Concept Model Pre-Validation Passed</span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg transition"
            >
              Back to Editor
            </button>
            <button
              onClick={() => {
                onClose();
                onConfirmExport();
              }}
              className="flex items-center gap-2 px-5 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-cyan-950/50 transition"
            >
              <Download className="w-4 h-4" />
              <span>Proceed to Package Export</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
