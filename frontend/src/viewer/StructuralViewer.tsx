import React, { useRef, useState } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, Grid, Line, Html } from '@react-three/drei';
import * as THREE from 'three';
import { useStore } from '../store/useStore';
import { Slab, Frame, Wall, Node, AreaLoad, PointLoad, LineLoad } from '../types';

// Camera controller helper to position camera dynamically based on model bounds
function CameraPresetController({ cameraView, bounds }: { cameraView: string; bounds: { centerX: number; centerY: number; size: number } }) {
  const { camera, controls } = useThree();

  React.useEffect(() => {
    const { centerX, centerY, size } = bounds;
    const dist = Math.max(size * 1.2, 15);

    if (controls) {
      (controls as any).target.set(centerX, 0, centerY);
    }

    if (cameraView === 'top' || cameraView === 'wireframe') {
      camera.position.set(centerX, dist * 1.6, centerY + 0.001);
    } else if (cameraView === 'front') {
      camera.position.set(centerX, dist * 0.4, centerY + dist * 1.3);
    } else if (cameraView === 'side') {
      camera.position.set(centerX + dist * 1.3, dist * 0.4, centerY);
    } else if (cameraView === 'iso') {
      camera.position.set(centerX + dist * 0.9, dist * 0.9, centerY + dist * 0.9);
    }
    camera.lookAt(centerX, 0, centerY);
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

export const StructuralViewer: React.FC = () => {
  const { floorModel, fullBuildingModel, selectedStory, viewMode, selectedElement, setSelectedElement, layerVisibility } = useStore();
  const [cameraPreset, setCameraPreset] = useState<'iso' | 'top' | 'front' | 'side' | 'wireframe'>('iso');

  // Story elevation lookup map for full building model rendering
  const storyElevations = React.useMemo(() => {
    const map: Record<string, number> = {};
    if (fullBuildingModel && fullBuildingModel.stories) {
      fullBuildingModel.stories.forEach((st: any) => {
        if (st && st.name) {
          map[st.name.trim().toLowerCase()] = st.elevation;
        }
      });
    }
    return map;
  }, [fullBuildingModel]);

  // Active target story filter name
  const activeStoryFilter = selectedStory?.name ? selectedStory.name.toLowerCase() : null;

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
      (fullBuildingModel.slabs || []).forEach((s: any) => s.polygon.forEach((p: any) => includePoint(p.x, p.y, s.elevation)));
      (fullBuildingModel.frames || []).forEach((f: any) => {
        if (f.start_point) includePoint(f.start_point.x, f.start_point.y, f.start_point.z);
        if (f.end_point) includePoint(f.end_point.x, f.end_point.y, f.end_point.z);
      });
      (fullBuildingModel.walls || []).forEach((w: any) => w.polygon.forEach((p: any) => includePoint(p.x, p.y, w.bottom_z)));
    } else if (floorModel) {
      floorModel.slabs.forEach((s) => s.polygon.forEach((p) => includePoint(p.x, p.y, 0)));
      floorModel.openings.forEach((o) => o.polygon.forEach((p) => includePoint(p.x, p.y, 0)));
      floorModel.beams.forEach((b) => {
        if (b.start_point) includePoint(b.start_point.x, b.start_point.y, 0);
        if (b.end_point) includePoint(b.end_point.x, b.end_point.y, 0);
      });
      floorModel.columns_below.concat(floorModel.columns_above).forEach((c) => {
        if (c.start_point) includePoint(c.start_point.x, c.start_point.y, 0);
      });
      floorModel.walls_below.concat(floorModel.walls_above).forEach((w) => {
        w.polygon.forEach((p) => includePoint(p.x, p.y, 0));
      });
    }

    if (minX === Infinity || isNaN(minX)) {
      minX = 0; maxX = 20; minY = 0; maxY = 20; minZ = 0; maxZ = 15;
    }

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const centerZ = (minZ + maxZ) / 2;
    const size = Math.max(maxX - minX, maxY - minY, maxZ - minZ, 10);
    return { minX, maxX, minY, maxY, minZ, maxZ, centerX, centerY, centerZ, size };
  }, [viewMode, fullBuildingModel, floorModel, activeStoryFilter]);

  const isWireframeMode = cameraPreset === 'wireframe';

  return (
    <div className="relative w-full h-full bg-slate-950 overflow-hidden select-none">
      {/* View Mode & Camera Toolbar */}
      <div className="absolute top-4 left-4 z-10 flex items-center gap-3 bg-slate-900/95 backdrop-blur-md p-2 rounded-xl border border-slate-800 shadow-2xl text-xs font-medium">
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
          target={[bounds.centerX, viewMode === 'full' ? bounds.centerZ : 0, bounds.centerY]}
        />

        {/* 1. Render Entire Multi-Floor Building Structure */}
        {viewMode === 'full' && fullBuildingModel && (
          <group>
            {/* Multi-story Slabs */}
            {layerVisibility.slabs &&
              (fullBuildingModel.slabs || [])
                .map((slab: any) => {
                const elev = storyElevations[slab.story ? slab.story.trim().toLowerCase() : ''] ?? slab.elevation ?? 0.0;
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

            {/* Multi-story Frame Elements (Beams & Columns) */}
            {(fullBuildingModel.frames || [])
              .map((fr: any) => {
              if (fr.type === 'Column' && layerVisibility.columns) {
                const p1 = fr.start_point;
                const p2 = fr.end_point;
                if (!p1 || !p2) return null;
                const midX = (p1.x + p2.x) / 2;
                const midY = (p1.y + p2.y) / 2;
                const minZ = Math.min(p1.z, p2.z);
                const maxZ = Math.max(p1.z, p2.z);
                const height = Math.abs(maxZ - minZ) || 3.5;
                const midZ = minZ + height / 2;
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
                const start = new THREE.Vector3(p1.x, p1.z, p1.y);
                const end = new THREE.Vector3(p2.x, p2.z, p2.y);
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
                .map((w: any) => {
                if (!w.polygon || w.polygon.length < 2) return null;
                const p1 = w.polygon[0];
                const p2 = w.polygon[1];
                const midX = (p1.x + p2.x) / 2;
                const midY = (p1.y + p2.y) / 2;
                const len = Math.hypot(p2.x - p1.x, p2.y - p1.y);
                if (len < 0.001) return null;
                const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x);
                const minZ = Math.min(w.top_z, w.bottom_z);
                const maxZ = Math.max(w.top_z, w.bottom_z);
                const height = Math.abs(maxZ - minZ) || 3.5;
                const midZ = minZ + height / 2;
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
        {viewMode === 'floor' && floorModel && (
          <group>
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

            {/* Nodes */}
            {layerVisibility.nodes &&
              floorModel.nodes &&
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

