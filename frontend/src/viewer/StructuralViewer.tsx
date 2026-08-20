import React, { useRef, useState } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, Grid, Line, Html } from '@react-three/drei';
import * as THREE from 'three';
import { useStore } from '../store/useStore';
import { Slab, Frame, Wall, Node } from '../types';

// Camera controller helper to position camera dynamically based on model bounds
function CameraPresetController({ cameraView, bounds }: { cameraView: string; bounds: { centerX: number; centerY: number; size: number } }) {
  const { camera } = useThree();

  React.useEffect(() => {
    const { centerX, centerY, size } = bounds;
    const dist = Math.max(size * 1.2, 15);

    if (cameraView === 'top') {
      camera.position.set(centerX, dist * 1.5, centerY + 0.001);
      camera.lookAt(centerX, 0, centerY);
    } else if (cameraView === 'front') {
      camera.position.set(centerX, dist * 0.4, centerY + dist * 1.2);
      camera.lookAt(centerX, 0, centerY);
    } else if (cameraView === 'side') {
      camera.position.set(centerX + dist * 1.2, dist * 0.4, centerY);
      camera.lookAt(centerX, 0, centerY);
    } else if (cameraView === 'iso') {
      camera.position.set(centerX + dist * 0.9, dist * 0.9, centerY + dist * 0.9);
      camera.lookAt(centerX, 0, centerY);
    }
  }, [cameraView, bounds, camera]);

  return null;
}

// Slab Mesh Renderer
function SlabMesh({ slab, isSelected, onClick }: { slab: Slab; isSelected: boolean; onClick: () => void }) {
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
    const pts = validPolygon.map((p) => new THREE.Vector3(p.x, p.y, depth));
    if (pts.length > 0) {
      pts.push(new THREE.Vector3(validPolygon[0].x, validPolygon[0].y, depth));
    }
    return pts;
  }, [validPolygon, depth]);

  return (
    <group rotation={[-Math.PI / 2, 0, 0]} onClick={(e) => { e.stopPropagation(); onClick(); }}>
      <mesh geometry={geometry}>
        <meshStandardMaterial
          color={isSelected ? '#06b6d4' : '#1e293b'}
          transparent
          opacity={0.85}
          roughness={0.3}
          metalness={0.2}
          side={THREE.DoubleSide}
        />
      </mesh>
      {points3d.length >= 2 && (
        <Line points={points3d} color={isSelected ? '#22d3ee' : '#38bdf8'} lineWidth={2.5} />
      )}
    </group>
  );
}

// Opening Renderer
function OpeningMesh({ opening }: { opening: Slab }) {
  if (!opening || !opening.polygon || opening.polygon.length < 2) return null;
  const validPts = opening.polygon.filter((p) => p && !isNaN(p.x) && !isNaN(p.y));
  if (validPts.length < 2) return null;

  const points3d = validPts.map((p) => new THREE.Vector3(p.x, 0.02, p.y));

  return (
    <group onClick={(e) => e.stopPropagation()}>
      <Line points={points3d} color="#ef4444" lineWidth={2} dashed dashScale={2} />
    </group>
  );
}

// Beam Renderer
function BeamMesh({ beam, isSelected, onClick }: { beam: Frame; isSelected: boolean; onClick: () => void }) {
  if (!beam || !beam.start_point || !beam.end_point) return null;
  if (isNaN(beam.start_point.x) || isNaN(beam.end_point.x)) return null;

  const start = new THREE.Vector3(beam.start_point.x, 0, beam.start_point.y);
  const end = new THREE.Vector3(beam.end_point.x, 0, beam.end_point.y);

  if (start.distanceTo(end) < 0.001) return null;

  return (
    <group onClick={(e) => { e.stopPropagation(); onClick(); }}>
      <Line points={[start, end]} color={isSelected ? '#f59e0b' : '#3b82f6'} lineWidth={4} />
    </group>
  );
}

// Column Renderer
function ColumnMesh({ column, isAbove, isSelected, onClick }: { column: Frame; isAbove: boolean; isSelected: boolean; onClick: () => void }) {
  if (!column || !column.start_point) return null;
  if (isNaN(column.start_point.x) || isNaN(column.start_point.y)) return null;

  const basePoint = new THREE.Vector3(column.start_point.x, 0, column.start_point.y);
  const height = isAbove ? 2.5 : -2.5;

  return (
    <group position={[basePoint.x, height / 2, basePoint.z]} onClick={(e) => { e.stopPropagation(); onClick(); }}>
      <mesh>
        <boxGeometry args={[0.4, Math.abs(height), 0.4]} />
        <meshStandardMaterial
          color={isSelected ? '#f59e0b' : isAbove ? '#a855f7' : '#8b5cf6'}
          roughness={0.4}
        />
      </mesh>
    </group>
  );
}

// Wall Renderer
function WallMesh({ wall, isAbove, isSelected, onClick }: { wall: Wall; isAbove: boolean; isSelected: boolean; onClick: () => void }) {
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

  return (
    <group
      position={[midX, height / 2, midY]}
      rotation={[0, -angle, 0]}
      onClick={(e) => { e.stopPropagation(); onClick(); }}
    >
      <mesh>
        <boxGeometry args={[len, Math.abs(height), thick]} />
        <meshStandardMaterial
          color={isSelected ? '#f59e0b' : isAbove ? '#10b981' : '#059669'}
          transparent
          opacity={0.8}
        />
      </mesh>
    </group>
  );
}

export const StructuralViewer: React.FC = () => {
  const { floorModel, selectedElement, setSelectedElement, layerVisibility } = useStore();
  const [cameraPreset, setCameraPreset] = useState<'iso' | 'top' | 'front' | 'side'>('iso');

  // Compute model bounding box center and size dynamically
  const bounds = React.useMemo(() => {
    if (!floorModel) return { minX: 0, maxX: 20, minY: 0, maxY: 20, centerX: 10, centerY: 10, size: 20 };
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

    floorModel.slabs.forEach((s) =>
      s.polygon.forEach((p) => {
        if (p.x < minX) minX = p.x;
        if (p.x > maxX) maxX = p.x;
        if (p.y < minY) minY = p.y;
        if (p.y > maxY) maxY = p.y;
      })
    );

    floorModel.beams.forEach((b) => {
      [b.start_point, b.end_point].forEach((p) => {
        if (p.x < minX) minX = p.x;
        if (p.x > maxX) maxX = p.x;
        if (p.y < minY) minY = p.y;
        if (p.y > maxY) maxY = p.y;
      });
    });

    if (minX === Infinity || isNaN(minX)) {
      minX = 0; maxX = 20; minY = 0; maxY = 20;
    }

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const size = Math.max(maxX - minX, maxY - minY, 10);
    return { minX, maxX, minY, maxY, centerX, centerY, size };
  }, [floorModel]);

  return (
    <div className="relative w-full h-full bg-slate-950 overflow-hidden select-none">
      {/* 3D Viewport Controls Toolbar */}
      <div className="absolute top-4 left-4 z-10 flex gap-2 bg-slate-900/90 backdrop-blur-md p-1.5 rounded-xl border border-slate-800 shadow-xl text-xs font-medium">
        <button
          onClick={() => setCameraPreset('iso')}
          className={`px-3 py-1.5 rounded-lg transition ${cameraPreset === 'iso' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'}`}
        >
          Perspective
        </button>
        <button
          onClick={() => setCameraPreset('top')}
          className={`px-3 py-1.5 rounded-lg transition ${cameraPreset === 'top' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'}`}
        >
          Top View
        </button>
        <button
          onClick={() => setCameraPreset('front')}
          className={`px-3 py-1.5 rounded-lg transition ${cameraPreset === 'front' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'}`}
        >
          Front
        </button>
        <button
          onClick={() => setCameraPreset('side')}
          className={`px-3 py-1.5 rounded-lg transition ${cameraPreset === 'side' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'}`}
        >
          Side
        </button>
      </div>

      {/* Main Three.js R3F Canvas */}
      <Canvas
        camera={{ position: [bounds.centerX + bounds.size * 0.9, bounds.size * 0.9, bounds.centerY + bounds.size * 0.9], fov: 45 }}
        onPointerMissed={() => setSelectedElement(null)}
      >
        <ambientLight intensity={0.7} />
        <directionalLight position={[bounds.centerX + 20, 40, bounds.centerY + 20]} intensity={1.2} castShadow />
        <directionalLight position={[bounds.centerX - 20, 20, bounds.centerY - 20]} intensity={0.4} />

        <Grid
          position={[bounds.centerX, -0.01, bounds.centerY]}
          infiniteGrid
          cellSize={1}
          cellThickness={0.5}
          cellColor="#334155"
          sectionSize={5}
          sectionThickness={1}
          sectionColor="#475569"
          fadeDistance={Math.max(bounds.size * 3, 100)}
        />

        <CameraPresetController cameraView={cameraPreset} bounds={bounds} />
        <OrbitControls
          makeDefault
          enableDamping
          dampingFactor={0.1}
          maxPolarAngle={Math.PI / 2 + 0.1}
          target={[bounds.centerX, 0, bounds.centerY]}
        />

        {floorModel && (
          <group>
            {/* Slabs */}
            {layerVisibility.slabs &&
              floorModel.slabs.map((slab) => (
                <SlabMesh
                  key={slab.id}
                  slab={slab}
                  isSelected={selectedElement?.id === slab.id}
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
          </group>
        )}
      </Canvas>
    </div>
  );
};
