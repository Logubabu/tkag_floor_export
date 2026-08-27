import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import { useStore } from '../store/useStore';

interface DropZoneProps {
  onUploadSuccess: (stories: any[]) => void;
}

export const DropZone: React.FC<DropZoneProps> = ({ onUploadSuccess }) => {
  const { setStories, setSelectedStory, setJobStatus, resetProjectState, createNewProjectId, inTool, setInTool } = useStore();
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [etabsStatusMsg, setEtabsStatusMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await processFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      await processFiles(Array.from(e.target.files));
    }
  };

  const processFiles = async (files: File[]) => {
    // Fresh state reset before processing
    await api.resetBackendState().catch(() => {});
    const currentProjectId = createNewProjectId();
    resetProjectState();
    setUploading(true);
    setUploadError(null);

    let primaryFile = files[0];
    let companionFile: File | undefined = undefined;

    if (files.length > 1) {
      const edb = files.find(f => f.name.toLowerCase().endsWith('.edb'));
      const textComp = files.find(f => {
        const n = f.name.toLowerCase();
        return n.endsWith('.$et') || n.endsWith('.e2k') || n.endsWith('.s2k') || n.endsWith('.d2k');
      });
      if (edb) {
        primaryFile = edb;
        companionFile = textComp;
      }
    }

    const getStem = (name: string) => name.replace(/\.[^/.]+$/, "").toLowerCase();

    // Store companion text files in sessionStorage when uploaded
    const textFile = files.find(f => {
      const n = f.name.toLowerCase();
      return n.endsWith('.$et') || n.endsWith('.e2k') || n.endsWith('.s2k') || n.endsWith('.d2k');
    });

    if (textFile) {
      try {
        const textContent = await textFile.text();
        const stem = getStem(textFile.name);
        sessionStorage.setItem(`companion_text_${stem}`, textContent);
        sessionStorage.setItem('last_companion_text', textContent);
      } catch (err) {
        console.error('Error saving companion text to sessionStorage:', err);
      }
    }

    // If EDB file uploaded and companionFile not supplied in drop, check sessionStorage
    if (primaryFile.name.toLowerCase().endsWith('.edb') && !companionFile) {
      const stem = getStem(primaryFile.name);
      const storedText = sessionStorage.getItem(`companion_text_${stem}`) || sessionStorage.getItem('last_companion_text');
      if (storedText) {
        companionFile = new File([storedText], `${stem}.$et`, { type: 'text/plain' });
      }
    }

    // If Live ETABS Mode is selected (inTool === false), check ETABS API connection first
    if (!inTool) {
      try {
        const conn = await api.connectEtabsApi(currentProjectId);
        if (!conn.success) {
          throw new Error(`Live ETABS check failed: ${conn.message}`);
        }
        setEtabsStatusMsg(`Connected to live ETABS instance (${conn.stories_count || 0} stories found).`);
      } catch (err: any) {
        setUploadError(
          `Live ETABS Mode error: ETABS installation or running instance not detected. (${err.message}). ` +
          `Tip: Switch to "In-Tool Processing Mode" to process models without ETABS installation.`
        );
        setUploading(false);
        return;
      }
    }

    try {
      const res = await api.uploadEtabsModel(currentProjectId, primaryFile, companionFile, inTool);
      
      // Poll background job status until completed
      let attempts = 0;
      const pollInterval = setInterval(async () => {
        attempts++;
        try {
          const job = await api.getJobStatus(res.job_id);
          setJobStatus(job);
          
          if (job.status === 'COMPLETED') {
            clearInterval(pollInterval);
            setUploading(false);
            const fetchedStories = await api.getStories(currentProjectId);
            setStories(fetchedStories);
            if (fetchedStories.length > 0) {
              setSelectedStory(fetchedStories[0]);
            }
            onUploadSuccess(fetchedStories);
          } else if (job.status === 'FAILED' || attempts > 40) {
            clearInterval(pollInterval);
            setUploading(false);
            resetProjectState();
            setUploadError(job.error || 'Model parsing job failed.');
          }
        } catch (err) {
          clearInterval(pollInterval);
          setUploading(false);
          resetProjectState();
        }
      }, 500);

    } catch (err: any) {
      resetProjectState();
      setUploadError(err.message || 'File upload failed.');
      setUploading(false);
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto space-y-4">
      {/* Execution Mode Switcher */}
      <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2">
        <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
          <span>Processing Mode</span>
          <span className="text-cyan-400 font-mono text-[10px]">
            {inTool ? 'ETABS Installation Not Needed' : 'Live ETABS COM API Active'}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2 text-xs">
          <button
            type="button"
            onClick={() => setInTool(true)}
            className={`p-2.5 rounded-lg border text-left transition flex flex-col justify-between ${
              inTool
                ? 'bg-cyan-950/60 border-cyan-500/80 text-cyan-200 ring-1 ring-cyan-500/50'
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            <span className="font-semibold text-slate-100 flex items-center justify-between">
              In-Tool Processing
              <span className="text-[10px] bg-cyan-900/60 text-cyan-300 px-1.5 py-0.5 rounded font-mono">
                No ETABS
              </span>
            </span>
            <span className="text-[11px] text-slate-400 mt-1">
              Parses .EDB, .$ET, .D2K inside tool code. ETABS installation not required.
            </span>
          </button>

          <button
            type="button"
            onClick={() => setInTool(false)}
            className={`p-2.5 rounded-lg border text-left transition flex flex-col justify-between ${
              !inTool
                ? 'bg-purple-950/60 border-purple-500/80 text-purple-200 ring-1 ring-purple-500/50'
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            <span className="font-semibold text-slate-100 flex items-center justify-between">
              Live ETABS Mode
              <span className="text-[10px] bg-purple-900/60 text-purple-300 px-1.5 py-0.5 rounded font-mono">
                ETABS OAPI
              </span>
            </span>
            <span className="text-[11px] text-slate-400 mt-1">
              Checks ETABS installation & active session to extract data via Windows API.
            </span>
          </button>
        </div>
      </div>

      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`p-8 border-2 border-dashed rounded-2xl cursor-pointer transition text-center flex flex-col items-center justify-center ${
          isDragging
            ? 'border-cyan-500 bg-cyan-950/20'
            : 'border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".edb,.$et,.et,.d2k,.e2k,.s2k,.$ed,.ed,.json"
          onChange={handleFileChange}
          className="hidden"
        />

        <div className="w-14 h-14 rounded-2xl bg-cyan-950/50 border border-cyan-800/40 flex items-center justify-center mb-4 shadow-lg shadow-cyan-950/40 text-cyan-400">
          <UploadCloud className="w-7 h-7" />
        </div>

        <h3 className="text-sm font-semibold text-slate-100 mb-1">
          Upload Structural Model File
        </h3>
        <p className="text-xs text-slate-400 mb-4 max-w-xs">
          Drag & drop your <code className="text-cyan-300 font-mono bg-slate-950 px-1 py-0.5 rounded">.edb</code>, <code className="text-cyan-300 font-mono bg-slate-950 px-1 py-0.5 rounded">.$et</code>, or <code className="text-cyan-300 font-mono bg-slate-950 px-1 py-0.5 rounded">.d2k</code> model file.
        </p>

        <div className="flex flex-wrap justify-center items-center gap-1.5 text-[11px] text-slate-400 font-mono">
          <span className="bg-slate-800 px-2 py-0.5 rounded border border-slate-700 text-cyan-300">.EDB</span>
          <span className="bg-slate-800 px-2 py-0.5 rounded border border-slate-700 text-cyan-300">.$ET</span>
          <span className="bg-slate-800 px-2 py-0.5 rounded border border-slate-700 text-cyan-300">.D2K</span>
          <span className="bg-slate-800 px-2 py-0.5 rounded border border-slate-700 text-slate-300">.E2K</span>
          <span className="bg-slate-800 px-2 py-0.5 rounded border border-slate-700 text-slate-300">.S2K</span>
        </div>
      </div>

      {uploading && (
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl flex items-center gap-3 text-xs">
          <div className="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin shrink-0" />
          <div>
            <p className="font-semibold text-slate-200">
              {inTool ? 'In-Tool Structural Model Extraction...' : 'Extracting Data via Live ETABS OAPI...'}
            </p>
            <p className="text-[11px] text-slate-400 font-mono">Extracting floor geometry, columns, beams & loads...</p>
          </div>
        </div>
      )}

      {etabsStatusMsg && (
        <div className="p-3 bg-emerald-950/40 border border-emerald-800/60 rounded-xl flex items-center gap-2 text-xs text-emerald-300">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <p>{etabsStatusMsg}</p>
        </div>
      )}

      {uploadError && (
        <div className="p-4 bg-rose-950/40 border border-rose-900/60 rounded-xl flex items-center gap-3 text-xs text-rose-200">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <p>{uploadError}</p>
        </div>
      )}
    </div>
  );
};
