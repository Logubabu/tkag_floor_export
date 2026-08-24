import React, { useState, useEffect, useRef } from 'react';
import { X, FileText, Code, Download, FileCode, Layers, CheckCircle2, Copy, Check, Eye, Maximize2 } from 'lucide-react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import { StructuralViewer } from '../viewer/StructuralViewer';

interface ExportedFilesViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ExportedFileData {
  dxf_filename: string;
  dxf_content: string;
  cpt_filename: string;
  cpt_content: string;
  automation_filename: string;
  automation_content: string;
  json_filename: string;
  json_content: string;
}

export const ExportedFilesViewerModal: React.FC<ExportedFilesViewerModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { activeProjectId, selectedStory, floorModel } = useStore();
  const [activeFileType, setActiveFileType] = useState<'dxf' | 'cpt' | 'py' | 'json'>('dxf');
  const [viewDisplayMode, setViewDisplayMode] = useState<'visual' | 'code'>('visual');
  const [filesData, setFilesData] = useState<ExportedFileData | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (isOpen && selectedStory) {
      fetchExportedFiles();
    }
  }, [isOpen, selectedStory]);

  const fetchExportedFiles = async () => {
    if (!selectedStory) return;
    setLoading(true);
    try {
      // 1. Extract floor
      const res = await api.extractFloor(activeProjectId, selectedStory.name, 'Mode B — Slab + Supporting Elements');
      // 2. Fetch extracted floor details & generated formats
      const modelData = await api.getFloorModel(activeProjectId, res.floor_id);

      // Construct file contents directly for immediate preview
      const cleanStory = selectedStory.name.replace(/[^a-zA-Z0-9_-]/g, '');

      // Generate DXF content preview
      const dxf_filename = `${cleanStory}_RAMConcept_Exchange.dxf`;
      const dxf_content = `0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nSECTION\n2\nTABLES\n0\nTABLE\n2\nLAYER\n70\n10\n0\nLAYER\n2\nSLAB_OUTLINE\n70\n0\n62\n1\n6\nCONTINUOUS\n0\nLAYER\n2\nOPENINGS\n70\n0\n62\n2\n6\nCONTINUOUS\n0\nLAYER\n2\nBEAMS\n70\n0\n62\n3\n6\nCONTINUOUS\n0\nLAYER\n2\nCOLUMNS_BELOW\n70\n0\n62\n4\n6\nCONTINUOUS\n0\nLAYER\n2\nCOLUMNS_ABOVE\n70\n0\n62\n5\n6\nCONTINUOUS\n0\nLAYER\n2\nWALLS_BELOW\n70\n0\n62\n6\n6\nCONTINUOUS\n0\nENDTAB\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n` +
        modelData.slabs.map((s, idx) => `0\nPOLYLINE\n8\nSLAB_OUTLINE\n66\n1\n70\n1\n` + s.polygon.map(p => `0\nVERTEX\n8\nSLAB_OUTLINE\n10\n${p.x.toFixed(4)}\n20\n${p.y.toFixed(4)}\n30\n0.0\n`).join('') + `0\nSEQEND\n`).join('') +
        modelData.beams.map(b => `0\nLINE\n8\nBEAMS\n10\n${b.start_point.x.toFixed(4)}\n20\n${b.start_point.y.toFixed(4)}\n30\n0.0\n11\n${b.end_point.x.toFixed(4)}\n21\n${b.end_point.y.toFixed(4)}\n31\n0.0\n`).join('') +
        `0\nENDSEC\n0\nEOF\n`;

      // Generate CPT content preview
      const cpt_filename = `${cleanStory}_RAMConcept_Model.cpt`;
      const cpt_content = `// BENTLEY RAM CONCEPT STRUCTURAL MODEL EXCHANGER (.CPT)
// Story Name: ${selectedStory.name}
// Story Elevation: ${selectedStory.elevation} m
BEGIN_MODEL
  FORMAT = RAM_CONCEPT_V8
  STORY = "${selectedStory.name}"
  ELEVATION = ${selectedStory.elevation}

  BEGIN_MATERIALS
    MATERIAL NAME="Concrete_C30" E=30000000 POISSON=0.2 FC=30000 DENSITY=24.0
  END_MATERIALS

  BEGIN_SLABS
${modelData.slabs.map(s => `    SLAB ID="${s.id}" THICKNESS=${s.thickness} PROPERTY="${s.property_name}"\n` + s.polygon.map(p => `      VERTEX X=${p.x.toFixed(4)} Y=${p.y.toFixed(4)}`).join('\n') + `\n    END_SLAB`).join('\n')}
  END_SLABS

  BEGIN_COLUMNS
${modelData.columns_below.map(c => `    COLUMN_BELOW ID="${c.id}" SECTION="${c.section}" X=${c.start_point.x.toFixed(4)} Y=${c.start_point.y.toFixed(4)}`).join('\n')}
${modelData.columns_above.map(c => `    COLUMN_ABOVE ID="${c.id}" SECTION="${c.section}" X=${c.start_point.x.toFixed(4)} Y=${c.start_point.y.toFixed(4)}`).join('\n')}
  END_COLUMNS
END_MODEL`;

      // Generate Python COM Automation script
      const automation_filename = `${cleanStory}_RAMConcept_Automation.py`;
      const automation_content = `# RAM Concept COM Automation Macro Script
# Generated automatically by ETABS to RAM Concept Exporter for ${selectedStory.name}
import sys
import win32com.client

dxf_file = r"C:\\Exports\\${dxf_filename}"

print("Connecting to Bentley RAM Concept Application...")
try:
    app = win32com.client.GetActiveObject("RAMConcept.Application")
    print("Connected to active RAM Concept instance.")
except Exception:
    app = win32com.client.Dispatch("RAMConcept.Application")
    print("Launched new RAM Concept instance.")

doc = app.NewDocument()
doc.ImportDXF(dxf_file)
print("Floor model geometry imported into RAM Concept successfully.")`;

      // Generate JSON Intermediate schema
      const json_filename = `${cleanStory}_IntermediateModel.json`;
      const json_content = JSON.stringify(modelData, null, 2);

      setFilesData({
        dxf_filename,
        dxf_content,
        cpt_filename,
        cpt_content,
        automation_filename,
        automation_content,
        json_filename,
        json_content,
      });
    } catch (err: any) {
      console.error('Error fetching exported file previews:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const getActiveContent = () => {
    if (!filesData) return '';
    switch (activeFileType) {
      case 'dxf':
        return filesData.dxf_content;
      case 'cpt':
        return filesData.cpt_content;
      case 'py':
        return filesData.automation_content;
      case 'json':
        return filesData.json_content;
    }
  };

  const getActiveFilename = () => {
    if (!filesData) return '';
    switch (activeFileType) {
      case 'dxf':
        return filesData.dxf_filename;
      case 'cpt':
        return filesData.cpt_filename;
      case 'py':
        return filesData.automation_filename;
      case 'json':
        return filesData.json_filename;
    }
  };

  const handleCopyContent = () => {
    const content = getActiveContent();
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadSingleFile = () => {
    const content = getActiveContent();
    const filename = getActiveFilename();
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-6 select-none animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-6xl h-[88vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center shadow-md">
              <FileCode className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-slate-100">Exported Files Viewer</h2>
                <span className="px-2 py-0.5 text-[10px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-800 rounded-md">
                  {selectedStory?.name || 'Floor File'} Code & Schema
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">
                Inspect raw output files: <span className="text-cyan-400 font-bold">.DXF • .CPT • .PY • .JSON</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyContent}
              disabled={loading || !filesData}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition border border-slate-700"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
              <span>{copied ? 'Copied!' : 'Copy File Content'}</span>
            </button>

            <button
              onClick={handleDownloadSingleFile}
              disabled={loading || !filesData}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg transition shadow-md"
            >
              <Download className="w-4 h-4" />
              <span>Download File</span>
            </button>

            <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* File Format Selector Tabs & Visual/Code Mode Toggle */}
        <div className="px-6 py-2.5 border-b border-slate-800 bg-slate-950 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-medium">
            <button
              onClick={() => setActiveFileType('dxf')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg border transition ${
                activeFileType === 'dxf'
                  ? 'bg-cyan-950/80 border-cyan-700 text-cyan-300 font-semibold shadow-inner'
                  : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <FileText className="w-4 h-4 text-cyan-400" />
              <span>AutoCAD Exchange (.DXF)</span>
            </button>

            <button
              onClick={() => setActiveFileType('cpt')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg border transition ${
                activeFileType === 'cpt'
                  ? 'bg-cyan-950/80 border-cyan-700 text-cyan-300 font-semibold shadow-inner'
                  : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-4 h-4 text-purple-400" />
              <span>RAM Concept Model (.CPT)</span>
            </button>

            <button
              onClick={() => setActiveFileType('py')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg border transition ${
                activeFileType === 'py'
                  ? 'bg-cyan-950/80 border-cyan-700 text-cyan-300 font-semibold shadow-inner'
                  : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <Code className="w-4 h-4 text-amber-400" />
              <span>Python Automation Script (.PY)</span>
            </button>

            <button
              onClick={() => setActiveFileType('json')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg border transition ${
                activeFileType === 'json'
                  ? 'bg-cyan-950/80 border-cyan-700 text-cyan-300 font-semibold shadow-inner'
                  : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <FileCode className="w-4 h-4 text-emerald-400" />
              <span>ISM Structural Schema (.JSON)</span>
            </button>
          </div>

          {/* Visual Drawing vs Raw Code Text Toggle */}
          <div className="flex items-center gap-3">
            <div className="flex bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs font-medium">
              <button
                onClick={() => setViewDisplayMode('visual')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition ${
                  viewDisplayMode === 'visual'
                    ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white font-semibold shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Visual Drawing</span>
              </button>

              <button
                onClick={() => setViewDisplayMode('code')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition ${
                  viewDisplayMode === 'code'
                    ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white font-semibold shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Code className="w-3.5 h-3.5" />
                <span>Raw Code Text</span>
              </button>
            </div>

            <span className="text-[11px] font-mono text-slate-400 bg-slate-900 px-3 py-1 rounded-md border border-slate-800 hidden md:inline-block">
              File: <span className="text-cyan-300 font-bold">{getActiveFilename()}</span>
            </span>
          </div>
        </div>

        {/* Main Viewport Content */}
        <div className="flex-1 p-4 bg-slate-950 overflow-hidden relative">
          {loading ? (
            <div className="h-full flex items-center justify-center text-slate-400 text-xs gap-3">
              <div className="w-5 h-5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
              <span>Generating exported file drawings...</span>
            </div>
          ) : viewDisplayMode === 'visual' ? (
            <div className="h-full w-full relative rounded-xl overflow-hidden border border-slate-800 bg-slate-950">
              <StructuralViewer />
              {/* Overlay Visual Legend Badge */}
              <div className="absolute bottom-4 left-4 z-10 bg-slate-900/90 backdrop-blur-md px-4 py-2 rounded-xl border border-slate-800 text-xs font-mono text-cyan-300 shadow-xl flex items-center gap-3">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
                <span>Extracted Floor Plan Drawing ({selectedStory?.name})</span>
              </div>
            </div>
          ) : (
            <pre className="h-full bg-slate-900/90 p-5 rounded-xl border border-slate-800 text-xs font-mono text-cyan-300/90 leading-relaxed overflow-x-auto select-text">
              {getActiveContent()}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
};
