export interface Point2D {
  x: number;
  y: number;
}

export interface Point3D {
  x: number;
  y: number;
  z: number;
}

export interface Story {
  id: string;
  name: string;
  elevation: number;
  height: number;
  is_master: boolean;
  similar_to?: string;
}

export interface Node {
  id: string;
  x: number;
  y: number;
  z: number;
  story?: string;
  restraints: boolean[];
}

export interface Frame {
  id: string;
  type: 'Beam' | 'Column' | 'Brace';
  start_node: string;
  end_node: string;
  start_point: Point3D;
  end_point: Point3D;
  section: string;
  story: string;
  material?: string;
}

export interface Slab {
  id: string;
  story: string;
  polygon: Point2D[];
  thickness: number;
  property_name: string;
  is_opening: boolean;
  material?: string;
  elevation: number;
}

export interface Wall {
  id: string;
  story: string;
  polygon: Point2D[];
  thickness: number;
  property_name: string;
  material?: string;
  top_z: number;
  bottom_z: number;
}

export interface AreaLoad {
  id: string;
  area_id: string;
  story: string;
  pattern: string;
  magnitude: number;
  direction: string;
}

export interface PointLoad {
  id: string;
  node_id: string;
  story: string;
  pattern: string;
  fz: number;
  mx: number;
  my: number;
}

export interface LineLoad {
  id: string;
  frame_id: string;
  story: string;
  pattern: string;
  magnitude: number;
}

export type ExtractionMode =
  | 'Mode A — Slab Only'
  | 'Mode B — Slab + Supporting Elements'
  | 'Mode C — Complete Floor Model';

export interface FloorModel {
  story: Story;
  mode: ExtractionMode;
  units: {
    length: string;
    force: string;
    temperature: string;
  };
  slabs: Slab[];
  openings: Slab[];
  beams: Frame[];
  columns_above: Frame[];
  columns_below: Frame[];
  walls_above: Wall[];
  walls_below: Wall[];
  nodes: Node[];
  area_loads: AreaLoad[];
  point_loads: PointLoad[];
  line_loads: LineLoad[];
}

export interface ValidationAlert {
  level: 'ERROR' | 'WARNING' | 'INFO';
  element_type: string;
  element_id: string;
  message: string;
  action_tip: string;
}

export interface ValidationResult {
  is_valid: boolean;
  summary: {
    slabs: number;
    openings: number;
    beams: number;
    columns: number;
    walls: number;
    errors: number;
    warnings: number;
  };
  alerts: ValidationAlert[];
}

export interface SelectedElement {
  id: string;
  type: 'Slab' | 'Opening' | 'Beam' | 'Column' | 'Wall' | 'Node';
  details: Record<string, any>;
}
