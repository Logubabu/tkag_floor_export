import React, { useEffect, useState } from 'react';
import { Header } from '../components/Header';
import { FloorTree } from '../components/FloorTree';
import { PropertyPanel } from '../components/PropertyPanel';
import { StructuralViewer } from '../viewer/StructuralViewer';
import { ExtractionModal } from '../components/ExtractionModal';
import { ValidationCard } from '../components/ValidationCard';
import { ExportModal } from '../components/ExportModal';
import { UploadModal } from '../components/UploadModal';
import { VisualComparisonModal } from '../components/VisualComparisonModal';
import { RAMConceptViewerModal } from '../components/RAMConceptViewerModal';
import { ExportedFilesViewerModal } from '../components/ExportedFilesViewerModal';
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
    setFullBuildingModel,
    setViewMode,
    setValidationResult,
    setIsExtracting,
  } = useStore();

  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isExtractionOpen, setIsExtractionOpen] = useState(false);
  const [isValidationOpen, setIsValidationOpen] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [isComparisonOpen, setIsComparisonOpen] = useState(false);
  const [isRamViewerOpen, setIsRamViewerOpen] = useState(false);
  const [isExportedFilesOpen, setIsExportedFilesOpen] = useState(false);

  const loadFullModelAndStories = async () => {
    if (!activeProjectId) {
      setStories([]);
      setSelectedStory(null);
      setFloorModel(null);
      setValidationResult(null);
      setFullBuildingModel(null);
      return;
    }

    try {
      const fetchedStories = await api.getStories(activeProjectId);
      if (Array.isArray(fetchedStories) && fetchedStories.length > 0) {
        setStories(fetchedStories);

        if (!useStore.getState().selectedStory) {
          setSelectedStory(fetchedStories[0]);
        }
      }

      try {
        const bModel = await api.getBuildingModel(activeProjectId);
        if (bModel) {
          setFullBuildingModel(bModel);
          setViewMode('full');
        }
      } catch (bmErr) {
        console.warn('Could not fetch full building model, using story-level extraction:', bmErr);
      }

      const currentSelected = useStore.getState().selectedStory || (fetchedStories.length > 0 ? fetchedStories[0] : null);
      if (currentSelected) {
        await runFloorExtraction(currentSelected, useStore.getState().extractionMode);
      }
    } catch (err) {
      console.error('Failed to load project stories:', err);
    }
  };

  // Load project stories & building model on mount only if activeProjectId is set
  useEffect(() => {
    loadFullModelAndStories();
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
    setViewMode('floor');
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
    await loadFullModelAndStories();
  };

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-100 flex flex-col overflow-hidden select-none">
      {/* Navigation Header */}
      <Header
        onOpenUploadModal={() => setIsUploadOpen(true)}
        onOpenExtractionModal={() => setIsExtractionOpen(true)}
        onOpenValidationModal={() => setIsValidationOpen(true)}
        onOpenExportModal={() => setIsExportOpen(true)}
        onOpenComparisonModal={() => setIsComparisonOpen(true)}
        onOpenRamViewerModal={() => setIsRamViewerOpen(true)}
        onOpenExportedFilesModal={() => setIsExportedFilesOpen(true)}
      />

      {/* Main Engineering Workbench */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Floor Hierarchy & Layer Controls */}
        <FloorTree
          onSelectFloor={handleSelectFloor}
          onExportFloor={() => setIsExportOpen(true)}
        />

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

      <VisualComparisonModal
        isOpen={isComparisonOpen}
        onClose={() => setIsComparisonOpen(false)}
        comparisonData={null}
      />

      <RAMConceptViewerModal
        isOpen={isRamViewerOpen}
        onClose={() => setIsRamViewerOpen(false)}
        onConfirmExport={() => setIsExportOpen(true)}
      />

      <ExportedFilesViewerModal
        isOpen={isExportedFilesOpen}
        onClose={() => setIsExportedFilesOpen(false)}
      />
    </div>
  );
};
