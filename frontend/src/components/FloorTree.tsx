import React from 'react';
import { Layers, ChevronRight, Crown, Box, Eye, EyeOff, CheckSquare, Square, Download } from 'lucide-react';
import { useStore } from '../store/useStore';
import { Story } from '../types';
import { formatLength } from '../utils/unitConverter';

interface FloorTreeProps {
  onSelectFloor: (story: Story) => void;
  onExportFloor?: (story: Story) => void;
}

export const FloorTree: React.FC<FloorTreeProps> = ({ onSelectFloor, onExportFloor }) => {
  const {
    stories,
    selectedStory,
    selectedStoryIds,
    toggleStorySelection,
    selectAllStories,
    deselectAllStories,
    layerVisibility,
    toggleLayerVisibility,
    viewMode,
    setViewMode,
    activeUnits,
  } = useStore();

  const allSelected = stories.length > 0 && selectedStoryIds.length === stories.length;

  return (
    <aside className="w-72 bg-slate-900 border-r border-slate-800 flex flex-col h-full z-10 shrink-0">
      {/* View Mode Toggle: Entire 3D Building vs Single Floor */}
      <div className="p-3 border-b border-slate-800 bg-slate-950/60">
        <div className="flex bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs font-medium">
          <button
            onClick={() => setViewMode('full')}
            className={`flex-1 py-1.5 rounded-md font-semibold text-center transition ${
              viewMode === 'full'
                ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-md shadow-cyan-950'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Entire 3D Building
          </button>
          <button
            onClick={() => setViewMode('floor')}
            className={`flex-1 py-1.5 rounded-md font-semibold text-center transition ${
              viewMode === 'floor'
                ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-md shadow-cyan-950'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Single Floor
          </button>
        </div>
      </div>

      {/* Sidebar Section 1: Story Tree & Multi-Select Controls */}
      <div className="p-4 border-b border-slate-800 space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span>Floor Selection</span>
          </h2>
          <span className="text-[11px] text-slate-400 font-mono bg-slate-800 px-2 py-0.5 rounded">
            {selectedStoryIds.length}/{stories.length} Selected
          </span>
        </div>

        {/* Multi-select Select All / Clear Controls */}
        <div className="flex items-center justify-between text-[11px] pt-1">
          <button
            onClick={allSelected ? deselectAllStories : selectAllStories}
            className="text-cyan-400 hover:text-cyan-300 font-medium transition"
          >
            {allSelected ? 'Deselect All' : 'Select All Floors'}
          </button>
          <span className="text-slate-500">•</span>
          <span className="text-slate-400 font-mono text-[10px]">Batch Extraction Ready</span>
        </div>
      </div>

      {/* Story List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        {stories.length === 0 ? (
          <div className="p-4 text-center text-xs text-slate-400 space-y-2 my-auto">
            <Layers className="w-8 h-8 text-slate-600 mx-auto opacity-50" />
            <p className="font-semibold text-slate-300">No Floors Loaded</p>
            <p className="text-[11px] text-slate-400 font-mono">Upload an .EDB, .$ET, or .D2K model file to extract stories.</p>
          </div>
        ) : (
          <>
            {/* All Floors (Full 3D Building View) Option */}
            <div
              onClick={() => {
                useStore.getState().setViewMode('full');
                useStore.getState().setSelectedStory(null);
              }}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold cursor-pointer transition border mb-2 ${
                viewMode === 'full' && !selectedStory
                  ? 'bg-gradient-to-r from-cyan-900 to-blue-900 text-white border-cyan-400 shadow-lg shadow-cyan-950/60 ring-2 ring-cyan-500/40'
                  : 'bg-slate-950/60 text-slate-300 border-slate-800 hover:border-cyan-700/60'
              }`}
            >
              <div className="flex items-center gap-2">
                <Box className="w-4 h-4 text-cyan-400" />
                <span>All Floors (Full 3D View)</span>
              </div>
              <span className="text-[10px] bg-slate-800 text-cyan-300 px-2 py-0.5 rounded font-mono">
                {stories.length} Floors
              </span>
            </div>

            {stories.map((story) => {
              const is3DActive = viewMode === 'floor' && selectedStory?.id === story.id;
              const isChecked = selectedStoryIds.includes(story.id);

              return (
                <div
                  key={story.id}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition group border ${
                    is3DActive
                      ? 'bg-gradient-to-r from-cyan-900 to-blue-900 text-white border-cyan-400 shadow-lg shadow-cyan-950/60 ring-2 ring-cyan-500/40 font-bold'
                      : 'bg-slate-950/40 text-slate-400 border-slate-850 hover:border-slate-750'
                  }`}
                >
                  {/* Checkbox for floor extraction selection */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleStorySelection(story.id);
                    }}
                    className="p-1 text-slate-400 hover:text-cyan-400 transition mr-1"
                    title="Toggle floor for batch extraction"
                  >
                    {isChecked ? (
                      <CheckSquare className="w-4 h-4 text-cyan-400" />
                    ) : (
                      <Square className="w-4 h-4 text-slate-600" />
                    )}
                  </button>

                  {/* Story Name & Single Floor View Trigger */}
                  <div
                    onClick={() => {
                      useStore.getState().setViewMode('floor');
                      onSelectFloor(story);
                    }}
                    className="flex-1 flex items-center justify-between cursor-pointer"
                  >
                <div className="flex items-center gap-2">
                  <span className={`font-semibold ${isChecked ? 'text-slate-200' : 'text-slate-500'}`}>
                    {story.name}
                  </span>
                  {story.is_master && (
                    <span title="Master Story">
                      <Crown className="w-3.5 h-3.5 text-amber-400 inline" />
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-mono text-slate-400">
                    {formatLength(story.elevation, activeUnits.length)}
                  </span>
                  {onExportFloor && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!selectedStoryIds.includes(story.id)) {
                          toggleStorySelection(story.id);
                        }
                        onExportFloor(story);
                      }}
                      className="p-1 rounded text-slate-400 hover:text-cyan-300 hover:bg-slate-800/80 transition"
                      title={`Export ${story.name} (DXF / CPT / PY)`}
                    >
                      <Download className="w-3.5 h-3.5" />
                    </button>
                  )}
                  <ChevronRight
                    className={`w-3.5 h-3.5 transition-transform ${
                      is3DActive ? 'rotate-90 text-cyan-400' : 'text-slate-600 group-hover:text-slate-400'
                    }`}
                  />
                </div>
                  </div>
                </div>
              );
            })}
          </>
        )}
      </div>

      {/* Sidebar Section 2: Active Floor Layer Toggles */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/40">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          3D Layer Filters
        </h3>
        <div className="grid grid-cols-2 gap-2 text-xs">
          {(['slabs', 'beams', 'columns', 'walls', 'nodes', 'loads'] as const).map((layer) => {
            const isVisible = layerVisibility[layer];
            return (
              <button
                key={layer}
                onClick={() => toggleLayerVisibility(layer)}
                className={`flex items-center justify-between px-2.5 py-1.5 rounded-md border text-[11px] capitalize transition ${
                  isVisible
                    ? 'bg-slate-800 border-slate-700 text-slate-200'
                    : 'bg-slate-950/80 border-slate-900 text-slate-400 opacity-60'
                }`}
              >
                <span>{layer}</span>
                {isVisible ? <Eye className="w-3.5 h-3.5 text-cyan-400" /> : <EyeOff className="w-3.5 h-3.5 text-slate-600" />}
              </button>
            );
          })}
        </div>
      </div>
    </aside>
  );
};
