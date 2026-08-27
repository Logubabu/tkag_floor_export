import { ExtractionMode, FloorModel, Story, ValidationResult } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

export const api = {
  async getStories(projectId: string): Promise<Story[]> {
    if (!projectId) return [];
    const res = await fetch(`${API_BASE}/projects/${projectId}/stories`);
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Failed to fetch project stories.');
    }
    const data = await res.json();
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.stories)) return data.stories;
    return [];
  },

  async getBuildingModel(projectId: string) {
    if (!projectId) return null;
    const res = await fetch(`${API_BASE}/projects/${projectId}/building-model`);
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Failed to fetch complete building model.');
    }
    return res.json();
  },

  async uploadEtabsModel(projectId: string, file: File, companionFile?: File, inTool: boolean = true): Promise<{ job_id: string }> {
    const formData = new FormData();
    formData.append('file', file);
    if (companionFile) {
      formData.append('companion_file', companionFile);
    }
    const res = await fetch(`${API_BASE}/projects/${projectId}/upload?in_tool=${inTool}`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Failed to upload ETABS model file.');
    }
    return res.json();
  },

  async getJobStatus(jobId: string) {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`);
    if (!res.ok) throw new Error('Failed to fetch job status.');
    return res.json();
  },

  async extractFloor(projectId: string, storyName: string, mode: ExtractionMode) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/extract-floor`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ story_name: storyName, mode }),
    });
    if (!res.ok) throw new Error('Failed to extract floor model.');
    return res.json();
  },

  async extractBatchFloors(projectId: string, storyNames: string[], mode: ExtractionMode) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/extract-floors`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ story_names: storyNames, mode }),
    });
    if (!res.ok) throw new Error('Failed to extract selected floors.');
    return res.json();
  },

  async getFloorModel(projectId: string, floorId: string): Promise<FloorModel> {
    const res = await fetch(`${API_BASE}/projects/${projectId}/floors/${floorId}/model`);
    if (!res.ok) throw new Error('Failed to fetch floor model data.');
    return res.json();
  },

  async validateFloor(projectId: string, floorId: string): Promise<ValidationResult> {
    const res = await fetch(`${API_BASE}/projects/${projectId}/floors/${floorId}/validate`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to validate floor data.');
    return res.json();
  },

  async connectEtabsApi(projectId: string = '') {
    const res = await fetch(`${API_BASE}/etabs/connect?project_id=${projectId}`, { method: 'POST' });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Failed to connect to live ETABS instance via COM API.');
    }
    return res.json();
  },

  async exportLiveRamConcept(projectId: string, floorId: string) {
    const res = await fetch(`${API_BASE}/ram-concept/export-live?project_id=${projectId}&floor_id=${floorId}`, { method: 'POST' });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Failed to push floor model to live RAM Concept via COM API.');
    }
    return res.json();
  },

  async downloadRamPackage(
    projectId: string,
    floorIds: string[],
    options: { include_dxf: boolean; include_cpt: boolean; include_json?: boolean; include_py?: boolean } = {
      include_dxf: true,
      include_cpt: true,
      include_json: false,
      include_py: false,
    }
  ) {
    const pickerWindow = window as unknown as {
      showSaveFilePicker?: (options?: {
        suggestedName?: string;
        types?: { description: string; accept: Record<string, string[]> }[];
      }) => Promise<{ createWritable: () => Promise<{ write: (data: Blob) => Promise<void>; close: () => Promise<void> }> }>;
    };
    const filename = `ETABS_RAMConcept_Export_${projectId}.zip`;
    let fileHandle = null;
    if (pickerWindow.showSaveFilePicker) {
      try {
        fileHandle = await pickerWindow.showSaveFilePicker({
          suggestedName: filename,
          types: [{ description: 'ZIP archive', accept: { 'application/zip': ['.zip'] } }],
        });
      } catch (err: any) {
        if (err.name === 'AbortError') {
          return;
        }
      }
    }

    const res = await fetch(`${API_BASE}/projects/${projectId}/download-package`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        floor_ids: floorIds,
        include_dxf: options.include_dxf,
        include_cpt: options.include_cpt,
        include_json: options.include_json ?? false,
        include_py: options.include_py ?? false,
      }),
    });
    if (!res.ok) throw new Error('Failed to generate RAM Concept export package.');

    const blob = await res.blob();
    if (fileHandle) {
      const writable = await fileHandle.createWritable();
      await writable.write(blob);
      await writable.close();
      return;
    }

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },

  async resetBackendState() {
    const res = await fetch(`${API_BASE}/reset`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to reset backend state.');
    return res.json();
  },

  async previewFloorExport(projectId: string, floorId: string) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/preview-export/${floorId}`);
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Failed to fetch export preview.');
    }
    return res.json();
  },
};

