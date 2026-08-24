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
}

export const useStore = create<AppState>((set) => ({
  activeProjectId: 'sample_proj',
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
    nodes: false,
    loads: false,
  },
  isExtracting: false,
  jobStatus: null,

  setProjectId: (id) => set({ activeProjectId: id }),
  setStories: (stories) =>
    set({
      stories,
      selectedStoryIds: [],
    }),
  setSelectedStory: (story) => set({ selectedStory: story }),
  toggleStorySelection: (storyId) =>
    set((state) => ({
      selectedStoryIds: state.selectedStoryIds.includes(storyId)
        ? state.selectedStoryIds.filter((id) => id !== storyId)
        : [...state.selectedStoryIds, storyId],
    })),
  selectAllStories: () => set((state) => ({ selectedStoryIds: state.stories.map((s) => s.id) })),
  deselectAllStories: () => set({ selectedStoryIds: [] }),
  setExtractionMode: (mode) => set({ extractionMode: mode }),
  setActiveUnits: (units) => set({ activeUnits: units }),
  setFloorModel: (model) => set({ floorModel: model, selectedElement: null }),
  setFullBuildingModel: (model) => set({ fullBuildingModel: model }),
  setViewMode: (mode) => set({ viewMode: mode }),
  setSelectedElement: (element) => set({ selectedElement: element }),
  setValidationResult: (res) => set({ validationResult: res }),
  toggleLayerVisibility: (layer) =>
    set((state) => ({
      layerVisibility: {
        ...state.layerVisibility,
        [layer]: !state.layerVisibility[layer],
      },
    })),
  setIsExtracting: (val) => set({ isExtracting: val }),
  setJobStatus: (status) => set({ jobStatus: status }),
}));
