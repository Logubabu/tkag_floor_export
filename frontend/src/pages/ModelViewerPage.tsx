import React, { useEffect, useState } from 'react';
import { Header } from '../components/Header';
import { FloorTree } from '../components/FloorTree';
import { PropertyPanel } from '../components/PropertyPanel';
import { StructuralViewer } from '../viewer/StructuralViewer';
import { ExtractionModal } from '../components/ExtractionModal';
import { ValidationCard } from '../components/ValidationCard';
import { ExportModal } from '../components/ExportModal';
import { UploadModal } from '../components/UploadModal';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import { Story, ExtractionMode } from '../types';

interface ModelViewerPageProps {
  onNavigateHome: () => void;
}

export const ModelViewerPage: React.FC<ModelViewerPageProps> = () => {
  const {
    activeProjectId,
    setStories,
    setSelectedStory,
    setFloorModel,
    setValidationResult,
    setIsExtracting,
  } = useStore();

  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isExtractionOpen, setIsExtractionOpen] = useState(false);
  const [isValidationOpen, setIsValidationOpen] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);

  // Load project stories on mount
  useEffect(() => {
    async function loadData() {
      try {
        const fetchedStories = await api.getStories(activeProjectId);
        setStories(fetchedStories);
        if (fetchedStories.length > 0) {
          const firstStory = fetchedStories[0];
          setSelectedStory(firstStory);
          await runFloorExtraction(firstStory, 'Mode B — Slab + Supporting Elements');
        }
      } catch (err) {
        console.error('Failed to load initial project stories:', err);
      }
    }
    loadData();
  }, [activeProjectId]);

  const runFloorExtraction = async (story: Story, mode: ExtractionMode) => {
    setIsExtracting(true);
    try {
      const res = await api.extractFloor(activeProjectId, story.name, mode);
      const floorModelData = await api.getFloorModel(activeProjectId, res.floor_id);
      setFloorModel(floorModelData);

      // Run automatic validation
      const valRes = await api.validateFloor(activeProjectId, res.floor_id);
      setValidationResult(valRes);
    } catch (err: any) {
      console.error('Extraction error:', err);
    } finally {
      setIsExtracting(false);
    }
  };

  const handleSelectFloor = async (story: Story) => {
    setSelectedStory(story);
    const { extractionMode } = useStore.getState();
    await runFloorExtraction(story, extractionMode);
  };

  const handleConfirmExtraction = async (mode: ExtractionMode) => {
    setIsExtractionOpen(false);
    const { selectedStory } = useStore.getState();
    if (selectedStory) {
      await runFloorExtraction(selectedStory, mode);
    }
  };

  const handleUploadSuccess = async () => {
    try {
      const fetchedStories = await api.getStories(activeProjectId);
      setStories(fetchedStories);
      if (fetchedStories.length > 0) {
        const firstStory = fetchedStories[0];
        setSelectedStory(firstStory);
        await runFloorExtraction(firstStory, 'Mode B — Slab + Supporting Elements');
      }
    } catch (err) {
      console.error('Error refreshing stories after upload:', err);
    }
  };

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-100 flex flex-col overflow-hidden select-none">
      {/* Navigation Header */}
      <Header
        onOpenUploadModal={() => setIsUploadOpen(true)}
        onOpenExtractionModal={() => setIsExtractionOpen(true)}
        onOpenValidationModal={() => setIsValidationOpen(true)}
        onOpenExportModal={() => setIsExportOpen(true)}
      />

      {/* Main Engineering Workbench */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Floor Hierarchy & Layer Controls */}
        <FloorTree onSelectFloor={handleSelectFloor} />

        {/* Center Viewport: Interactive 3D Three.js Model */}
        <div className="flex-1 relative h-full">
          <StructuralViewer />
        </div>

        {/* Right Sidebar: Property Inspector */}
        <PropertyPanel />
      </div>

      {/* Configuration & Upload Modals */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />

      <ExtractionModal
        isOpen={isExtractionOpen}
        onClose={() => setIsExtractionOpen(false)}
        onConfirm={handleConfirmExtraction}
      />

      <ValidationCard
        isOpen={isValidationOpen}
        onClose={() => setIsValidationOpen(false)}
      />

      <ExportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
      />
    </div>
  );
};
