import React from 'react';
import { Box, Layers, ArrowRight, Activity, Download, FileText, Plus } from 'lucide-react';
import { DropZone } from '../components/DropZone';
import { useStore } from '../store/useStore';

interface DashboardPageProps {
  onNavigateToViewer: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigateToViewer }) => {
  const { stories } = useStore();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Header Banner */}
      <div className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md px-8 py-6">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-950/50">
              <Box className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-100 tracking-wide">
                ETABS to RAM Concept Floor Exporter
              </h1>
              <p className="text-xs text-slate-400 font-mono">
                Structural Engineering Floor Extraction & Data Pipeline Platform
              </p>
            </div>
          </div>

          <button
            onClick={onNavigateToViewer}
            className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold rounded-lg shadow-md transition flex items-center gap-2"
          >
            <span>Open 3D Model Viewer</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-8 space-y-8">
        {/* Quick Upload Section */}
        <section className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-xl">
          <div className="max-w-xl mx-auto text-center mb-6">
            <h2 className="text-base font-semibold text-slate-100 mb-1">
              Ingest Structural Building Model
            </h2>
            <p className="text-xs text-slate-400">
              Upload an ETABS <code className="text-cyan-400 font-mono">.e2k</code> text export or select a sample preloaded model to extract floor geometry, supporting columns, and wall reactions.
            </p>
          </div>

          <DropZone onUploadSuccess={() => onNavigateToViewer()} />
        </section>

        {/* Recent Models & Extraction History */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-3">
            <div className="w-9 h-9 rounded-lg bg-cyan-950 text-cyan-400 flex items-center justify-center">
              <Layers className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200">1. Story Detection</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Automatically parses story elevations, master floor height assignments, and grid coordinates from ETABS building files.
            </p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-950 text-emerald-400 flex items-center justify-center">
              <Activity className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200">2. Smart Support Extraction</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Extracts floor slabs, slab openings, intersecting floor beams, and upper/lower supporting columns & shear walls.
            </p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-3">
            <div className="w-9 h-9 rounded-lg bg-amber-950 text-amber-400 flex items-center justify-center">
              <Download className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200">3. RAM Concept Export</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Generates RAM Concept CAD DXF layer drawings, automated Bentley COM macro scripts, and normalized structural JSON.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
};
