import { create } from 'zustand';
import { Story, FloorModel, ExtractionMode, ValidationResult, SelectedElement } from '../types';

interface AppState {
  activeProjectId: string;
  stories: Story[];
  selectedStory: Story | null;
  selectedStoryIds: string[];
  extractionMode: ExtractionMode;
  activeUnits: { length: string; force: string };
  floorModel: FloorModel | null;
  fullBuildingModel: any | null;
  viewMode: 'full' | 'floor';
  selectedElement: SelectedElement | null;
  validationResult: ValidationResult | null;
  layerVisibility: {
    slabs: boolean;
    beams: boolean;
    columns: boolean;
    walls: boolean;
    nodes: boolean;
    loads: boolean;
  };
  isExtracting: boolean;
  jobStatus: { progress: number; status: string; stage: string } | null;
  inTool: boolean;

  setProjectId: (id: string) => void;
  setStories: (stories: Story[]) => void;
  setSelectedStory: (story: Story | null) => void;
  toggleStorySelection: (storyId: string) => void;
  selectAllStories: () => void;
  deselectAllStories: () => void;
  setExtractionMode: (mode: ExtractionMode) => void;
  setActiveUnits: (units: { length: string; force: string }) => void;
  setFloorModel: (model: FloorModel | null) => void;
  setFullBuildingModel: (model: any | null) => void;
  setViewMode: (mode: 'full' | 'floor') => void;
  setSelectedElement: (element: SelectedElement | null) => void;
  setValidationResult: (res: ValidationResult | null) => void;
  toggleLayerVisibility: (layer: keyof AppState['layerVisibility']) => void;
  setIsExtracting: (val: boolean) => void;
  setJobStatus: (status: any) => void;
  setInTool: (val: boolean) => void;
  resetProjectState: () => void;
  createNewProjectId: () => string;
}

const getStoredProjectId = (): string => {
  // Always start fresh on browser load/refresh as per user requirement
  try {
    sessionStorage.removeItem('active_project_id');
  } catch {}
  return '';
};

export const useStore = create<AppState>((set) => ({
  activeProjectId: '',
  stories: [],
  selectedStory: null,
  selectedStoryIds: [],
  extractionMode: 'Mode B — Slab + Supporting Elements',
  activeUnits: { length: 'm', force: 'kN' },
  floorModel: null,
  fullBuildingModel: null,
  viewMode: 'full',
  selectedElement: null,
  validationResult: null,
  layerVisibility: {
    slabs: true,
    beams: true,
    columns: true,
    walls: true,
    nodes: true,
    loads: true,
  },
  isExtracting: false,
  jobStatus: null,
  inTool: true,

  setProjectId: (id) => {
    try {
      sessionStorage.setItem('active_project_id', id);
    } catch {}
    set({ activeProjectId: id });
  },
  createNewProjectId: () => {
    const newId = `proj_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    try {
      sessionStorage.setItem('active_project_id', newId);
    } catch {}
    set({ activeProjectId: newId });
    return newId;
  },
  setStories: (stories) =>
    set({
      stories: Array.isArray(stories) ? stories : [],
      selectedStoryIds: [],
    }),
  setSelectedStory: (story) => set({ selectedStory: story }),
  toggleStorySelection: (storyId) =>
    set((state) => ({
      selectedStoryIds: (Array.isArray(state.selectedStoryIds) ? state.selectedStoryIds : []).includes(storyId)
        ? (Array.isArray(state.selectedStoryIds) ? state.selectedStoryIds : []).filter((id) => id !== storyId)
        : [...(Array.isArray(state.selectedStoryIds) ? state.selectedStoryIds : []), storyId],
    })),
  selectAllStories: () =>
    set((state) => ({
      selectedStoryIds: Array.isArray(state.stories) ? state.stories.map((s) => s.id) : [],
    })),
  deselectAllStories: () => set({ selectedStoryIds: [] }),
  setExtractionMode: (mode) => set({ extractionMode: mode }),
  setActiveUnits: (units) => set({ activeUnits: units }),
  setFloorModel: (model) => {
    if (!model) {
      set({ floorModel: null, selectedElement: null });
      return;
    }
    const safeModel: FloorModel = {
      ...model,
      slabs: Array.isArray(model.slabs) ? model.slabs : [],
      openings: Array.isArray(model.openings) ? model.openings : [],
      beams: Array.isArray(model.beams) ? model.beams : [],
      columns_below: Array.isArray(model.columns_below) ? model.columns_below : [],
      columns_above: Array.isArray(model.columns_above) ? model.columns_above : [],
      walls_below: Array.isArray(model.walls_below) ? model.walls_below : [],
      walls_above: Array.isArray(model.walls_above) ? model.walls_above : [],
      nodes: Array.isArray(model.nodes) ? model.nodes : [],
      area_loads: Array.isArray(model.area_loads) ? model.area_loads : [],
      point_loads: Array.isArray(model.point_loads) ? model.point_loads : [],
      line_loads: Array.isArray(model.line_loads) ? model.line_loads : [],
    };
    set({ floorModel: safeModel, selectedElement: null });
  },
  setFullBuildingModel: (model) => set({ fullBuildingModel: model }),
  setViewMode: (mode) => set({ viewMode: mode }),
  setSelectedElement: (element) => set({ selectedElement: element }),
  setValidationResult: (res) => {
    if (!res) {
      set({ validationResult: null });
      return;
    }
    set({
      validationResult: {
        ...res,
        alerts: Array.isArray(res.alerts) ? res.alerts : [],
      },
    });
  },
  toggleLayerVisibility: (layer) =>
    set((state) => ({
      layerVisibility: {
        ...state.layerVisibility,
        [layer]: !state.layerVisibility[layer],
      },
    })),
  setIsExtracting: (val) => set({ isExtracting: val }),
  setJobStatus: (status) => set({ jobStatus: status }),
  setInTool: (val) => set({ inTool: val }),
  resetProjectState: () =>
    set({
      stories: [],
      selectedStory: null,
      selectedStoryIds: [],
      floorModel: null,
      fullBuildingModel: null,
      selectedElement: null,
      validationResult: null,
      jobStatus: null,
    }),
}));
