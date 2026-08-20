import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import { useStore } from '../store/useStore';

interface DropZoneProps {
  onUploadSuccess: (stories: any[]) => void;
}

export const DropZone: React.FC<DropZoneProps> = ({ onUploadSuccess }) => {
  const { activeProjectId, setStories, setSelectedStory, setJobStatus } = useStore();
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
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
      await processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      await processFile(e.target.files[0]);
    }
  };

  const processFile = async (file: File) => {
    setUploading(true);
    setUploadError(null);

    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['e2k', 's2k', 'json', 'edb'].includes(ext || '')) {
      setUploadError('Invalid file type. Please upload an ETABS .e2k / .s2k text export or structural JSON file.');
      setUploading(false);
      return;
    }

    try {
      const res = await api.uploadEtabsModel(activeProjectId, file);
      
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
            const fetchedStories = await api.getStories(activeProjectId);
            setStories(fetchedStories);
            if (fetchedStories.length > 0) {
              setSelectedStory(fetchedStories[0]);
            }
            onUploadSuccess(fetchedStories);
          } else if (job.status === 'FAILED' || attempts > 30) {
            clearInterval(pollInterval);
            setUploading(false);
            setUploadError(job.error || 'Model parsing job timed out.');
          }
        } catch (err) {
          clearInterval(pollInterval);
          setUploading(false);
        }
      }, 500);

    } catch (err: any) {
      setUploadError(err.message || 'File upload failed.');
      setUploading(false);
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto">
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
          accept=".e2k,.s2k,.json,.edb"
          onChange={handleFileChange}
          className="hidden"
        />

        <div className="w-14 h-14 rounded-2xl bg-cyan-950/50 border border-cyan-800/40 flex items-center justify-center mb-4 shadow-lg shadow-cyan-950/40 text-cyan-400">
          <UploadCloud className="w-7 h-7" />
        </div>

        <h3 className="text-sm font-semibold text-slate-100 mb-1">
          Upload ETABS Model Export File
        </h3>
        <p className="text-xs text-slate-400 mb-4 max-w-xs">
          Drag & drop your ETABS <code className="text-cyan-300 font-mono bg-slate-950 px-1 py-0.5 rounded">.e2k</code> text export or click to browse files.
        </p>

        <div className="flex items-center gap-2 text-[11px] text-slate-500 font-mono">
          <span>Supported: .E2K</span>
          <span>•</span>
          <span>.S2K</span>
          <span>•</span>
          <span>.EDB</span>
          <span>•</span>
          <span>JSON</span>
        </div>
      </div>

      {uploading && (
        <div className="mt-4 p-4 bg-slate-900 border border-slate-800 rounded-xl flex items-center gap-3 text-xs">
          <div className="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin shrink-0" />
          <div>
            <p className="font-semibold text-slate-200">Parsing ETABS Building Model...</p>
            <p className="text-[11px] text-slate-400 font-mono">Extracting stories, slabs, columns, and walls...</p>
          </div>
        </div>
      )}

      {uploadError && (
        <div className="mt-4 p-4 bg-rose-950/40 border border-rose-900/60 rounded-xl flex items-center gap-3 text-xs text-rose-200">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <p>{uploadError}</p>
        </div>
      )}
    </div>
  );
};
