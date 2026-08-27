import React, { useRef, useState } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, Grid, Line, Html } from '@react-three/drei';
import { ChevronUp, ChevronDown, Layers, Box } from 'lucide-react';
import * as THREE from 'three';
import { useStore } from '../store/useStore';
import { Slab, Frame, Wall, Node, AreaLoad, PointLoad, LineLoad, Story } from '../types';

interface StructuralViewerProps {
  onSelectFloor?: (story: Story) => void;
}

// Camera controller helper to position camera dynamically based on model bounds
function CameraPresetController({ cameraView, bounds }: { cameraView: string; bounds: { centerX: number; centerY: number; centerZ: number; size: number } }) {
  const { camera, controls } = useThree();

  React.useEffect(() => {
    const { centerX, centerY, centerZ, size } = bounds;
    const dist = Math.max(size * 1.2, 15);
    const targetY = centerZ || 0;

    if (controls) {
      (controls as any).target.set(centerX, targetY, centerY);
    }

    if (cameraView === 'top' || cameraView === 'wireframe') {
      camera.position.set(centerX, targetY + dist * 1.6, centerY + 0.001);
    } else if (cameraView === 'front') {
      camera.position.set(centerX, targetY + dist * 0.4, centerY + dist * 1.3);
    } else if (cameraView === 'side') {
      camera.position.set(centerX + dist * 1.3, targetY + dist * 0.4, centerY);
    } else if (cameraView === 'iso') {
      camera.position.set(centerX + dist * 0.9, targetY + dist * 0.9, centerY + dist * 0.9);
    }
    camera.lookAt(centerX, targetY, centerY);
    if (controls) {
      (controls as any).update();
    }
  }, [cameraView, bounds, camera, controls]);

  return null;
}

// Helper function to resolve extracted or default color
function resolveColor(extractedColor: string | undefined, defaultColor: string): string {
  if (!extractedColor) return defaultColor;
  const c = extractedColor.trim();
  if (c.startsWith('#') || c.startsWith('rgb')) return c;
  // If hex without #
  if (/^[0-9A-Fa-f]{6}$/.test(c)) return `#${c}`;
  return defaultColor;
}

// Slab Mesh Renderer
function SlabMesh({ slab, isSelected, isWireframe, onClick }: { slab: Slab; isSelected: boolean; isWireframe: boolean; onClick: () => void }) {
  if (!slab || !slab.polygon || slab.polygon.length < 3) return null;

  const validPolygon = React.useMemo(() => {
    return slab.polygon.filter((p) => p && !isNaN(p.x) && !isNaN(p.y));
  }, [slab.polygon]);

  if (validPolygon.length < 3) return null;

  const shape = React.useMemo(() => {
    const s = new THREE.Shape();
    s.moveTo(validPolygon[0].x, validPolygon[0].y);
    for (let i = 1; i < validPolygon.length; i++) {
      s.lineTo(validPolygon[i].x, validPolygon[i].y);
    }
    s.closePath();
    return s;
  }, [validPolygon]);

  const depth = Math.max(slab.thickness || 0.2, 0.05);

  const geometry = React.useMemo(() => {
    try {
      return new THREE.ExtrudeGeometry(shape, {
        depth: depth,
        bevelEnabled: false,
      });
    } catch (e) {
      return new THREE.ShapeGeometry(shape);
    }
  }, [shape, depth]);

  const points3d = React.useMemo(() => {
    const pts = validPolygon.map((p) => new THREE.Vector3(p.x, p.y, -0.005));
    if (pts.length > 0) {
      pts.push(new THREE.Vector3(validPolygon[0].x, validPolygon[0].y, -0.005));
    }
    return pts;
  }, [validPolygon]);

  const meshColor = isSelected
    ? '#06b6d4'
    : isWireframe
    ? '#0f172a'
    : resolveColor(slab.color, '#1e293b');

  return (
    <group rotation={[Math.PI / 2, 0, 0]} onClick={(e) => { e.stopPropagation(); onClick(); }}>
      <mesh geometry={geometry}>
        <meshStandardMaterial
          color={meshColor}
          transparent
          opacity={isWireframe ? 0.25 : 0.85}
          wireframe={isWireframe}
          roughness={0.3}
          metalness={0.2}
          side={THREE.DoubleSide}
        />
      </mesh>
      {points3d.length >= 2 && (
        <Line points={points3d} color={isSelected ? '#22d3ee' : '#38bdf8'} lineWidth={isSelected ? 3.5 : 2} />
      )}
    </group>
  );
}

// Opening Renderer
function OpeningMesh({ opening }: { opening: Slab }) {
  if (!opening || !opening.polygon || opening.polygon.length < 2) return null;
  const validPts = opening.polygon.filter((p) => p && !isNaN(p.x) && !isNaN(p.y));
  if (validPts.length < 2) return null;

  const points3d = React.useMemo(() => {
    const pts = validPts.map((p) => new THREE.Vector3(p.x, 0.02, p.y));
    if (pts.length > 0 && (pts[0].x !== pts[pts.length - 1].x || pts[0].z !== pts[pts.length - 1].z)) {
      pts.push(new THREE.Vector3(validPts[0].x, 0.02, validPts[0].y));
    }
    return pts;
  }, [validPts]);

  return (
    <group onClick={(e) => e.stopPropagation()}>
      <Line points={points3d} color="#ef4444" lineWidth={2.5} dashed dashScale={2} />
    </group>
  );
}

// Beam Renderer
function BeamMesh({ beam, isSelected, onClick }: { beam: Frame; isSelected: boolean; onClick: () => void }) {
  if (!beam || !beam.start_point || !beam.end_point) return null;
  if (isNaN(beam.start_point.x) || isNaN(beam.end_point.x)) return null;

  const start = new THREE.Vector3(beam.start_point.x, 0.03, beam.start_point.y);
  const end = new THREE.Vector3(beam.end_point.x, 0.03, beam.end_point.y);

  if (start.distanceTo(end) < 0.001) return null;

  const beamColor = isSelected ? '#f59e0b' : resolveColor(beam.color, '#3b82f6');

  return (
    <group onClick={(e) => { e.stopPropagation(); onClick(); }}>
      <Line points={[start, end]} color={beamColor} lineWidth={4} />
    </group>
  );
}

// Column Renderer
function ColumnMesh({ column, isAbove, isSelected, isWireframe, onClick }: { column: Frame; isAbove: boolean; isSelected: boolean; isWireframe: boolean; onClick: () => void }) {
  if (!column || !column.start_point) return null;
  if (isNaN(column.start_point.x) || isNaN(column.start_point.y)) return null;

  const basePoint = new THREE.Vector3(column.start_point.x, 0, column.start_point.y);
  const height = isAbove ? 2.5 : -2.5;

  const colColor = isSelected
    ? '#f59e0b'
    : resolveColor(column.color, isAbove ? '#a855f7' : '#8b5cf6');

  return (
    <group position={[basePoint.x, height / 2, basePoint.z]} onClick={(e) => { e.stopPropagation(); onClick(); }}>
      <mesh>
        <boxGeometry args={[0.4, Math.abs(height), 0.4]} />
        <meshStandardMaterial
          color={colColor}
          wireframe={isWireframe}
          transparent={isWireframe}
          opacity={isWireframe ? 0.35 : 1}
          roughness={0.4}
        />
      </mesh>
    </group>
  );
}

// Wall Renderer
function WallMesh({ wall, isAbove, isSelected, isWireframe, onClick }: { wall: Wall; isAbove: boolean; isSelected: boolean; isWireframe: boolean; onClick: () => void }) {
  if (!wall || !wall.polygon || wall.polygon.length < 2) return null;
  const p1 = wall.polygon[0];
  const p2 = wall.polygon[1];
  if (!p1 || !p2 || isNaN(p1.x) || isNaN(p2.x)) return null;

  const midX = (p1.x + p2.x) / 2;
  const midY = (p1.y + p2.y) / 2;
  const len = Math.hypot(p2.x - p1.x, p2.y - p1.y);
  if (len < 0.001) return null;

  const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x);
  const height = isAbove ? 2.5 : -2.5;
  const thick = Math.max(wall.thickness || 0.3, 0.05);

  const wallColor = isSelected
    ? '#f59e0b'
    : resolveColor(wall.color, isAbove ? '#10b981' : '#059669');

  return (
    <group
      position={[midX, height / 2, midY]}
      rotation={[0, -angle, 0]}
      onClick={(e) => { e.stopPropagation(); onClick(); }}
    >
      <mesh>
        <boxGeometry args={[len, Math.abs(height), thick]} />
        <meshStandardMaterial
          color={wallColor}
          wireframe={isWireframe}
          transparent
          opacity={isWireframe ? 0.3 : 0.8}
        />
      </mesh>
    </group>
  );
}

// Node Marker Renderer
function NodeMarker({ node, isSelected, onClick }: { node: Node; isSelected: boolean; onClick: () => void }) {
  if (!node || isNaN(node.x) || isNaN(node.y)) return null;
  const position = new THREE.Vector3(node.x, 0.05, node.y);

  return (
    <group position={position} onClick={(e) => { e.stopPropagation(); onClick(); }}>
      <mesh>
        <sphereGeometry args={[0.2, 16, 16]} />
        <meshStandardMaterial color={isSelected ? '#f59e0b' : '#ec4899'} emissive={isSelected ? '#f59e0b' : '#be185d'} emissiveIntensity={0.5} />
      </mesh>
    </group>
  );
}

// Load Indicator Renderer
function LoadIndicator({ load }: { load: PointLoad }) {
  if (!load || isNaN(load.fz)) return null;
  return null;
}

export const StructuralViewer: React.FC<StructuralViewerProps> = ({ onSelectFloor }) => {
  const { floorModel, fullBuildingModel, stories, selectedStoryIds, selectedStory, setSelectedStory, setViewMode, viewMode, selectedElement, setSelectedElement, layerVisibility } = useStore();
  const [cameraPreset, setCameraPreset] = useState<'iso' | 'top' | 'front' | 'side' | 'wireframe'>('iso');

  // Sorted stories by elevation descending (top story to bottom story)
  const sortedStories = React.useMemo(() => {
    return [...(stories || [])].sort((a, b) => b.elevation - a.elevation);
  }, [stories]);

  const currentStoryIndex = React.useMemo(() => {
    if (!selectedStory) return -1;
    return sortedStories.findIndex((s) => s.id === selectedStory.id);
  }, [sortedStories, selectedStory]);

  const handleStepFloor = (direction: 'up' | 'down') => {
    if (sortedStories.length === 0) return;
    let nextIdx = 0;
    if (currentStoryIndex === -1) {
      nextIdx = direction === 'up' ? 0 : sortedStories.length - 1;
    } else if (direction === 'up') {
      nextIdx = Math.max(0, currentStoryIndex - 1);
    } else {
      nextIdx = Math.min(sortedStories.length - 1, currentStoryIndex + 1);
    }
    const targetStory = sortedStories[nextIdx];
    setSelectedStory(targetStory);
    setViewMode('floor');
    if (onSelectFloor) {
      onSelectFloor(targetStory);
    }
  };

  // Story elevation lookup map for full building model rendering
  const storyElevations = React.useMemo(() => {
    const map: Record<string, number> = {};
    const sourceStories = stories && stories.length > 0 ? stories : fullBuildingModel?.stories || [];

    sourceStories.forEach((st: any) => {
      if (st && st.name !== undefined && st.name !== null) {
        const raw = String(st.name).trim().toLowerCase();
        const norm = raw.replace(/[\s_-]+/g, '');
        map[raw] = st.elevation;
        map[norm] = st.elevation;
      }
    });
    return map;
  }, [stories, fullBuildingModel]);

  const getElevationForStory = React.useCallback(
    (storyName: string | undefined | null, explicitElev?: number): number => {
      if (storyName) {
        const raw = String(storyName).trim().toLowerCase();
        const norm = raw.replace(/[\s_-]+/g, '');
        if (storyElevations[raw] !== undefined) return storyElevations[raw];
        if (storyElevations[norm] !== undefined) return storyElevations[norm];

        // Match numbers e.g. "STORY1" -> "story 1"
        const digits = raw.match(/\d+/);
        if (digits) {
          const numStr = digits[0];
          for (const [k, v] of Object.entries(storyElevations)) {
            const kDigits = k.match(/\d+/);
            if (kDigits && kDigits[0] === numStr) {
              return v;
            }
          }
        }
      }
      if (typeof explicitElev === 'number') {
        return explicitElev;
      }
      return 0.0;
    },
    [storyElevations]
  );

  // Set of selected story names for 3D viewport filtering (null if all or none selected)
  const activeStoryFilterSet = React.useMemo(() => {
    if (!stories || stories.length === 0) return null;
    if (selectedStoryIds.length === 0 || selectedStoryIds.length === stories.length) {
      return null; // Display all floors data when none or all selected
    }
    const set = new Set<string>();
    stories.forEach((st) => {
      if (selectedStoryIds.includes(st.id)) {
        const clean = st.name.trim().toLowerCase();
        set.add(clean);
        set.add(clean.replace(/\s+/g, ''));
        set.add(clean.replace(/[\s_-]+/g, ''));
      }
    });
    return set;
  }, [stories, selectedStoryIds]);

  const isElementVisible = React.useCallback((storyName: string | undefined | null): boolean => {
    if (!activeStoryFilterSet) return true; // Show all floors when none or all selected
    if (!storyName) return true;
    const clean = storyName.trim().toLowerCase();
    const cleanNoSpace = clean.replace(/\s+/g, '');
    const cleanAlpha = clean.replace(/[\s_-]+/g, '');
    return activeStoryFilterSet.has(clean) || activeStoryFilterSet.has(cleanNoSpace) || activeStoryFilterSet.has(cleanAlpha);
  }, [activeStoryFilterSet]);

  // Compute model bounding box center and size dynamically
  const bounds = React.useMemo(() => {
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity, minZ = Infinity, maxZ = -Infinity;

    const includePoint = (x: number, y: number, z: number = 0) => {
      if (typeof x === 'number' && !isNaN(x) && typeof y === 'number' && !isNaN(y)) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
        if (z < minZ) minZ = z;
        if (z > maxZ) maxZ = z;
      }
    };

    if (viewMode === 'full' && fullBuildingModel) {
      (fullBuildingModel.slabs || [])
        .filter((s: any) => isElementVisible(s.story))
        .forEach((s: any) => {
          const elev = getElevationForStory(s.story, s.elevation);
          s.polygon.forEach((p: any) => includePoint(p.x, p.y, elev));
        });
      (fullBuildingModel.frames || [])
        .filter((f: any) => isElementVisible(f.story))
        .forEach((f: any) => {
          const storyElev = getElevationForStory(f.story);
          const z1 = f.start_point ? (f.start_point.z > 0 ? f.start_point.z : storyElev) : storyElev;
          const z2 = f.end_point ? (f.end_point.z > 0 ? f.end_point.z : storyElev) : storyElev;
          if (f.start_point) includePoint(f.start_point.x, f.start_point.y, z1);
          if (f.end_point) includePoint(f.end_point.x, f.end_point.y, z2);
        });
      (fullBuildingModel.walls || [])
        .filter((w: any) => isElementVisible(w.story))
        .forEach((w: any) => {
          const storyElev = getElevationForStory(w.story);
          const z = w.bottom_z > 0 ? w.bottom_z : storyElev;
          w.polygon.forEach((p: any) => includePoint(p.x, p.y, z));
        });
    } else if (viewMode === 'floor') {
      let foundPoints = false;
      if (floorModel && floorModel.slabs && floorModel.slabs.length > 0) {
        floorModel.slabs.forEach((s) => s.polygon.forEach((p) => { includePoint(p.x, p.y, 0); foundPoints = true; }));
        floorModel.openings.forEach((o) => o.polygon.forEach((p) => { includePoint(p.x, p.y, 0); foundPoints = true; }));
        floorModel.beams.forEach((b) => {
          if (b.start_point) { includePoint(b.start_point.x, b.start_point.y, 0); foundPoints = true; }
          if (b.end_point) { includePoint(b.end_point.x, b.end_point.y, 0); foundPoints = true; }
        });
        floorModel.columns_below.concat(floorModel.columns_above).forEach((c) => {
          if (c.start_point) { includePoint(c.start_point.x, c.start_point.y, 0); foundPoints = true; }
        });
        floorModel.walls_below.concat(floorModel.walls_above).forEach((w) => {
          w.polygon.forEach((p) => { includePoint(p.x, p.y, 0); foundPoints = true; });
        });
      }

      if (!foundPoints && fullBuildingModel) {
        const activeStoryName = selectedStory ? selectedStory.name.trim().toLowerCase() : '';
        const matchStory = (stName: string | undefined) => {
          if (!stName || !activeStoryName) return true;
          return stName.trim().toLowerCase() === activeStoryName;
        };

        (fullBuildingModel.slabs || [])
          .filter((s: any) => matchStory(s.story))
          .forEach((s: any) => s.polygon.forEach((p: any) => includePoint(p.x, p.y, 0)));
        (fullBuildingModel.frames || [])
          .filter((f: any) => matchStory(f.story))
          .forEach((f: any) => {
            if (f.start_point) includePoint(f.start_point.x, f.start_point.y, 0);
            if (f.end_point) includePoint(f.end_point.x, f.end_point.y, 0);
          });
        (fullBuildingModel.walls || [])
          .filter((w: any) => matchStory(w.story))
          .forEach((w: any) => w.polygon.forEach((p: any) => includePoint(p.x, p.y, 0)));
      }
    }

    if (minX === Infinity || isNaN(minX)) {
      minX = 0; maxX = 20; minY = 0; maxY = 20; minZ = 0; maxZ = 15;
    }

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const centerZ = (minZ + maxZ) / 2;
    const size = Math.max(maxX - minX, maxY - minY, maxZ - minZ, 10);
    return { minX, maxX, minY, maxY, minZ, maxZ, centerX, centerY, centerZ, size };
  }, [viewMode, fullBuildingModel, floorModel, selectedStory, activeStoryFilterSet, getElevationForStory]);

  const isWireframeMode = cameraPreset === 'wireframe';

  const sceneProps = {
    viewMode,
    fullBuildingModel,
    floorModel,
    selectedStory,
    layerVisibility,
    selectedElement,
    setSelectedElement,
    isWireframeMode,
    isElementVisible,
    storyElevations,
    getElevationForStory,
    bounds,
  };

  return (
    <div className="relative w-full h-full bg-slate-950 overflow-hidden select-none">
      {/* Top Right: Layer-by-Layer Floor Navigator Bar */}
      {sortedStories.length > 0 && (
        <div className="absolute top-4 right-4 z-20 flex items-center gap-2 bg-slate-900/95 backdrop-blur-md p-2 rounded-xl border border-slate-800 shadow-2xl text-xs font-medium">
          <div className="flex items-center gap-1">
            <button
              onClick={() => handleStepFloor('up')}
              disabled={currentStoryIndex <= 0}
              className="p-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 text-slate-300 disabled:opacity-30 disabled:hover:bg-slate-950 transition border border-slate-800 flex items-center gap-1"
              title="Move Up One Floor Layer"
            >
              <ChevronUp className="w-4 h-4 text-cyan-400" />
            </button>
            <button
              onClick={() => handleStepFloor('down')}
              disabled={currentStoryIndex >= sortedStories.length - 1}
              className="p-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 text-slate-300 disabled:opacity-30 disabled:hover:bg-slate-950 transition border border-slate-800 flex items-center gap-1"
              title="Move Down One Floor Layer"
            >
              <ChevronDown className="w-4 h-4 text-cyan-400" />
            </button>
          </div>

          <div className="h-5 w-px bg-slate-800" />

          <select
            value={viewMode === 'full' || !selectedStory ? 'all' : selectedStory.id}
            onChange={(e) => {
              const val = e.target.value;
              if (val === 'all') {
                setViewMode('full');
                setSelectedStory(null);
              } else {
                const match = stories.find((s) => s.id === val);
                if (match) {
                  setSelectedStory(match);
                  setViewMode('floor');
                  if (onSelectFloor) onSelectFloor(match);
                }
              }
            }}
            className="bg-slate-950 border border-slate-800 text-cyan-300 rounded-lg px-2.5 py-1 text-xs font-semibold focus:outline-none focus:border-cyan-500 cursor-pointer max-w-[200px] truncate"
          >
            <option value="all">🏢 All Floors (Full 3D Building)</option>
            {sortedStories.map((st) => (
              <option key={st.id} value={st.id}>
                🥞 {st.name} ({st.elevation}m)
              </option>
            ))}
          </select>
        </div>
      )}
      {/* View Mode & Camera Toolbar */}
      <div className="absolute top-4 left-4 z-20 flex items-center gap-3 bg-slate-900/95 backdrop-blur-md p-2 rounded-xl border border-slate-800 shadow-2xl text-xs font-medium">
        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
          <button
            onClick={() => setCameraPreset('iso')}
            className={`px-3 py-1.5 rounded-md font-semibold transition ${cameraPreset === 'iso' ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-md shadow-cyan-950' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'}`}
          >
            1. 3D Perspective
          </button>
          <button
            onClick={() => setCameraPreset('top')}
            className={`px-3 py-1.5 rounded-md font-semibold transition ${cameraPreset === 'top' ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-md shadow-cyan-950' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'}`}
          >
            2. 2D Floor Plan
          </button>
          <button
            onClick={() => setCameraPreset('wireframe')}
            className={`px-3 py-1.5 rounded-md font-semibold transition ${cameraPreset === 'wireframe' ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-md shadow-cyan-950' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'}`}
          >
            3. CAD DXF Wireframe
          </button>
        </div>

        <div className="h-5 w-px bg-slate-800" />

        <div className="flex items-center gap-1">
          <button
            onClick={() => setCameraPreset('front')}
            className={`px-2.5 py-1 rounded-md transition ${cameraPreset === 'front' ? 'bg-slate-800 text-cyan-300' : 'text-slate-400 hover:text-slate-200'}`}
          >
            Front
          </button>
          <button
            onClick={() => setCameraPreset('side')}
            className={`px-2.5 py-1 rounded-md transition ${cameraPreset === 'side' ? 'bg-slate-800 text-cyan-300' : 'text-slate-400 hover:text-slate-200'}`}
          >
            Side
          </button>
        </div>
      </div>

      {/* Main Three.js Canvas */}
      <Canvas
        camera={{ position: [bounds.centerX + bounds.size * 0.9, bounds.size * 0.9, bounds.centerY + bounds.size * 0.9], fov: 45 }}
        onPointerMissed={() => setSelectedElement(null)}
      >
        <ambientLight intensity={0.7} />
        <directionalLight position={[bounds.centerX + 20, 40, bounds.centerY + 20]} intensity={1.2} castShadow />
        <directionalLight position={[bounds.centerX - 20, 20, bounds.centerY - 20]} intensity={0.4} />

        <CameraPresetController cameraView={cameraPreset} bounds={bounds} />
        <OrbitControls
          makeDefault
          enableDamping
          dampingFactor={0.1}
        />

        {/* 1. Render Entire Multi-Floor Building Structure */}
        {viewMode === 'full' && fullBuildingModel && (
          <group>
            {/* Multi-story Slabs */}
            {layerVisibility.slabs &&
              (fullBuildingModel.slabs || [])
                .filter((slab: any) => !slab.is_opening && isElementVisible(slab.story))
                .map((slab: any) => {
                const elev = getElevationForStory(slab.story, slab.elevation);
                return (
                  <group key={slab.id} position={[0, elev, 0]}>
                    <SlabMesh
                      slab={slab}
                      isSelected={selectedElement?.id === slab.id}
                      isWireframe={isWireframeMode}
                      onClick={() =>
                        setSelectedElement({
                          id: slab.id,
                          type: 'Slab',
                          details: {
                            story: slab.story,
                            property: slab.property_name,
                            thickness: slab.thickness,
                            elevation: elev,
                          },
                        })
                      }
                    />
                  </group>
                );
              })}

            {/* Multi-story Slab Openings */}
            {layerVisibility.slabs &&
              (fullBuildingModel.slabs || [])
                .filter((op: any) => op.is_opening && isElementVisible(op.story))
                .map((op: any) => {
                const elev = getElevationForStory(op.story, op.elevation);
                return (
                  <group key={op.id} position={[0, elev, 0]}>
                    <OpeningMesh opening={op} />
                  </group>
                );
              })}

            {/* Multi-story Frame Elements (Beams & Columns) */}
            {(fullBuildingModel.frames || [])
              .filter((fr: any) => isElementVisible(fr.story))
              .map((fr: any) => {
              const storyElev = getElevationForStory(fr.story);
              if (fr.type === 'Column' && layerVisibility.columns) {
                const p1 = fr.start_point;
                const p2 = fr.end_point;
                if (!p1 || !p2) return null;
                const midX = (p1.x + p2.x) / 2;
                const midY = (p1.y + p2.y) / 2;
                const z1 = typeof p1.z === 'number' && !isNaN(p1.z) ? p1.z : storyElev;
                const z2 = typeof p2.z === 'number' && !isNaN(p2.z) ? p2.z : storyElev;
                const minZ = Math.min(z1, z2);
                const maxZ = Math.max(z1, z2);
                let height = Math.abs(maxZ - minZ);
                if (height < 0.01) height = 3.5;

                let midZ = (minZ + maxZ) / 2;
                if (Math.abs(maxZ - minZ) < 0.01) {
                  midZ = storyElev - height / 2;
                }
                const colColor = selectedElement?.id === fr.id ? '#f59e0b' : resolveColor(fr.color, '#8b5cf6');

                return (
                  <group key={fr.id} position={[midX, midZ, midY]} onClick={(e) => { e.stopPropagation(); setSelectedElement({ id: fr.id, type: 'Column', details: { section: fr.section, story: fr.story } }); }}>
                    <mesh>
                      <boxGeometry args={[0.4, height, 0.4]} />
                      <meshStandardMaterial
                        color={colColor}
                        wireframe={isWireframeMode}
                        transparent={isWireframeMode}
                        opacity={isWireframeMode ? 0.35 : 1}
                      />
                    </mesh>
                  </group>
                );
              } else if (fr.type === 'Beam' && layerVisibility.beams) {
                const p1 = fr.start_point;
                const p2 = fr.end_point;
                if (!p1 || !p2) return null;
                const startZ = typeof p1.z === 'number' && !isNaN(p1.z) ? p1.z : storyElev;
                const endZ = typeof p2.z === 'number' && !isNaN(p2.z) ? p2.z : storyElev;
                const start = new THREE.Vector3(p1.x, startZ, p1.y);
                const end = new THREE.Vector3(p2.x, endZ, p2.y);
                const beamColor = selectedElement?.id === fr.id ? '#f59e0b' : resolveColor(fr.color, '#3b82f6');

                return (
                  <group key={fr.id} onClick={(e) => { e.stopPropagation(); setSelectedElement({ id: fr.id, type: 'Beam', details: { section: fr.section, story: fr.story } }); }}>
                    <Line points={[start, end]} color={beamColor} lineWidth={4} />
                  </group>
                );
              }
              return null;
            })}

            {/* Multi-story Core Walls */}
            {layerVisibility.walls &&
              (fullBuildingModel.walls || [])
                .filter((w: any) => isElementVisible(w.story))
                .map((w: any) => {
                if (!w.polygon || w.polygon.length < 2) return null;
                const storyElev = getElevationForStory(w.story);
                const p1 = w.polygon[0];
                const p2 = w.polygon[1];
                const midX = (p1.x + p2.x) / 2;
                const midY = (p1.y + p2.y) / 2;
                const len = Math.hypot(p2.x - p1.x, p2.y - p1.y);
                if (len < 0.001) return null;
                const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x);
                const z1 = typeof w.top_z === 'number' && !isNaN(w.top_z) ? w.top_z : storyElev;
                const z2 = typeof w.bottom_z === 'number' && !isNaN(w.bottom_z) ? w.bottom_z : storyElev - 3.5;
                const minZ = Math.min(z1, z2);
                const maxZ = Math.max(z1, z2);
                let height = Math.abs(maxZ - minZ);
                if (height < 0.01) height = 3.5;

                let midZ = (minZ + maxZ) / 2;
                if (Math.abs(maxZ - minZ) < 0.01) {
                  midZ = storyElev - height / 2;
                }
                const thick = Math.max(w.thickness || 0.3, 0.05);
                const wallColor = selectedElement?.id === w.id ? '#f59e0b' : resolveColor(w.color, '#059669');

                return (
                  <group
                    key={w.id}
                    position={[midX, midZ, midY]}
                    rotation={[0, -angle, 0]}
                    onClick={(e) => { e.stopPropagation(); setSelectedElement({ id: w.id, type: 'Wall', details: { property: w.property_name, story: w.story } }); }}
                  >
                    <mesh>
                      <boxGeometry args={[len, height, thick]} />
                      <meshStandardMaterial
                        color={wallColor}
                        wireframe={isWireframeMode}
                        transparent
                        opacity={isWireframeMode ? 0.3 : 0.8}
                      />
                    </mesh>
                  </group>
                );
              })}
          </group>
        )}

        {/* 2. Render Single Isolated Floor Model */}
        {viewMode === 'floor' && (
          <group>
            {floorModel && floorModel.slabs && floorModel.slabs.length > 0 ? (
              <>
                {/* Slabs */}
                {layerVisibility.slabs &&
                  floorModel.slabs.map((slab) => (
                    <SlabMesh
                      key={slab.id}
                      slab={slab}
                      isSelected={selectedElement?.id === slab.id}
                      isWireframe={isWireframeMode}
                      onClick={() =>
                        setSelectedElement({
                          id: slab.id,
                          type: 'Slab',
                          details: {
                            story: slab.story,
                            property: slab.property_name,
                            thickness: `${slab.thickness * 1000} mm`,
                            vertices: slab.polygon.length,
                            elevation: `${slab.elevation} m`,
                          },
                        })
                      }
                    />
                  ))}

                {/* Openings */}
                {layerVisibility.slabs &&
                  floorModel.openings.map((op) => <OpeningMesh key={op.id} opening={op} />)}

                {/* Beams */}
                {layerVisibility.beams &&
                  floorModel.beams.map((bm) => (
                    <BeamMesh
                      key={bm.id}
                      beam={bm}
                      isSelected={selectedElement?.id === bm.id}
                      onClick={() =>
                        setSelectedElement({
                          id: bm.id,
                          type: 'Beam',
                          details: {
                            section: bm.section,
                            story: bm.story,
                            start_node: bm.start_node,
                            end_node: bm.end_node,
                          },
                        })
                      }
                    />
                  ))}

                {/* Columns Below */}
                {layerVisibility.columns &&
                  floorModel.columns_below.map((col) => (
                    <ColumnMesh
                      key={col.id}
                      column={col}
                      isAbove={false}
                      isSelected={selectedElement?.id === col.id}
                      isWireframe={isWireframeMode}
                      onClick={() =>
                        setSelectedElement({
                          id: col.id,
                          type: 'Column',
                          details: {
                            section: col.section,
                            story: col.story,
                            location: `X: ${col.start_point.x.toFixed(2)}, Y: ${col.start_point.y.toFixed(2)}`,
                            position: 'Supporting Below',
                          },
                        })
                      }
                    />
                  ))}

                {/* Columns Above */}
                {layerVisibility.columns &&
                  floorModel.columns_above.map((col) => (
                    <ColumnMesh
                      key={col.id}
                      column={col}
                      isAbove={true}
                      isSelected={selectedElement?.id === col.id}
                      isWireframe={isWireframeMode}
                      onClick={() =>
                        setSelectedElement({
                          id: col.id,
                          type: 'Column',
                          details: {
                            section: col.section,
                            story: col.story,
                            location: `X: ${col.start_point.x.toFixed(2)}, Y: ${col.start_point.y.toFixed(2)}`,
                            position: 'Reaction Above',
                          },
                        })
                      }
                    />
                  ))}

                {/* Walls Below */}
                {layerVisibility.walls &&
                  floorModel.walls_below.map((w) => (
                    <WallMesh
                      key={w.id}
                      wall={w}
                      isAbove={false}
                      isSelected={selectedElement?.id === w.id}
                      isWireframe={isWireframeMode}
                      onClick={() =>
                        setSelectedElement({
                          id: w.id,
                          type: 'Wall',
                          details: {
                            property: w.property_name,
                            thickness: `${w.thickness * 1000} mm`,
                            story: w.story,
                            position: 'Supporting Below',
                          },
                        })
                      }
                    />
                  ))}

                {/* Walls Above */}
                {layerVisibility.walls &&
                  floorModel.walls_above.map((w) => (
                    <WallMesh
                      key={w.id}
                      wall={w}
                      isAbove={true}
                      isSelected={selectedElement?.id === w.id}
                      isWireframe={isWireframeMode}
                      onClick={() =>
                        setSelectedElement({
                          id: w.id,
                          type: 'Wall',
                          details: {
                            property: w.property_name,
                            thickness: `${w.thickness * 1000} mm`,
                            story: w.story,
                            position: 'Reaction Above',
                          },
                        })
                      }
                    />
                  ))}
              </>
            ) : (
              /* Fallback to rendering selected story from fullBuildingModel */
              fullBuildingModel && (
                <>
                  {layerVisibility.slabs &&
                    (fullBuildingModel.slabs || [])
                      .filter((s: any) => !selectedStory || (s.story && s.story.trim().toLowerCase() === selectedStory.name.trim().toLowerCase()))
                      .map((slab: any) => (
                        <group key={slab.id} position={[0, 0, 0]}>
                          <SlabMesh
                            slab={slab}
                            isSelected={selectedElement?.id === slab.id}
                            isWireframe={isWireframeMode}
                            onClick={() => setSelectedElement({ id: slab.id, type: 'Slab', details: { story: slab.story, property: slab.property_name, thickness: slab.thickness } })}
                          />
                        </group>
                      ))}

                  {(fullBuildingModel.frames || [])
                    .filter((fr: any) => !selectedStory || (fr.story && fr.story.trim().toLowerCase() === selectedStory.name.trim().toLowerCase()))
                    .map((fr: any) => {
                      if (fr.type === 'Column' && layerVisibility.columns) {
                        const p1 = fr.start_point;
                        const p2 = fr.end_point;
                        if (!p1 || !p2) return null;
                        const midX = (p1.x + p2.x) / 2;
                        const midY = (p1.y + p2.y) / 2;
                        const colColor = selectedElement?.id === fr.id ? '#f59e0b' : resolveColor(fr.color, '#8b5cf6');
                        return (
                          <group key={fr.id} position={[midX, 0, midY]} onClick={(e) => { e.stopPropagation(); setSelectedElement({ id: fr.id, type: 'Column', details: { section: fr.section, story: fr.story } }); }}>
                            <mesh>
                              <boxGeometry args={[0.4, 3.5, 0.4]} />
                              <meshStandardMaterial color={colColor} wireframe={isWireframeMode} transparent={isWireframeMode} opacity={isWireframeMode ? 0.35 : 1} />
                            </mesh>
                          </group>
                        );
                      } else if (fr.type === 'Beam' && layerVisibility.beams) {
                        const p1 = fr.start_point;
                        const p2 = fr.end_point;
                        if (!p1 || !p2) return null;
                        const start = new THREE.Vector3(p1.x, 0.03, p1.y);
                        const end = new THREE.Vector3(p2.x, 0.03, p2.y);
                        const beamColor = selectedElement?.id === fr.id ? '#f59e0b' : resolveColor(fr.color, '#3b82f6');
                        return (
                          <group key={fr.id} onClick={(e) => { e.stopPropagation(); setSelectedElement({ id: fr.id, type: 'Beam', details: { section: fr.section, story: fr.story } }); }}>
                            <Line points={[start, end]} color={beamColor} lineWidth={4} />
                          </group>
                        );
                      }
                      return null;
                    })}

                  {layerVisibility.walls &&
                    (fullBuildingModel.walls || [])
                      .filter((w: any) => !selectedStory || (w.story && w.story.trim().toLowerCase() === selectedStory.name.trim().toLowerCase()))
                      .map((w: any) => {
                        if (!w.polygon || w.polygon.length < 2) return null;
                        const p1 = w.polygon[0];
                        const p2 = w.polygon[1];
                        const midX = (p1.x + p2.x) / 2;
                        const midY = (p1.y + p2.y) / 2;
                        const len = Math.hypot(p2.x - p1.x, p2.y - p1.y);
                        if (len < 0.001) return null;
                        const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x);
                        const wallColor = selectedElement?.id === w.id ? '#f59e0b' : resolveColor(w.color, '#059669');
                        return (
                          <group key={w.id} position={[midX, 0, midY]} rotation={[0, -angle, 0]} onClick={(e) => { e.stopPropagation(); setSelectedElement({ id: w.id, type: 'Wall', details: { property: w.property_name, story: w.story } }); }}>
                            <mesh>
                              <boxGeometry args={[len, 3.5, Math.max(w.thickness || 0.3, 0.05)]} />
                              <meshStandardMaterial color={wallColor} wireframe={isWireframeMode} transparent opacity={isWireframeMode ? 0.3 : 0.8} />
                            </mesh>
                          </group>
                        );
                      })}
                </>
              )
            )}
            {/* Nodes */}
            {layerVisibility.nodes &&
              floorModel?.nodes &&
              floorModel.nodes.map((node) => (
                <NodeMarker
                  key={node.id}
                  node={node}
                  isSelected={selectedElement?.id === node.id}
                  onClick={() =>
                    setSelectedElement({
                      id: node.id,
                      type: 'Node',
                      details: {
                        id: node.id,
                        x: `${node.x.toFixed(2)} m`,
                        y: `${node.y.toFixed(2)} m`,
                        z: `${node.z.toFixed(2)} m`,
                        restraints: node.restraints ? node.restraints.join(',') : 'None',
                      },
                    })
                  }
                />
              ))}
          </group>
        )}
      </Canvas>
    </div>
  );
};

