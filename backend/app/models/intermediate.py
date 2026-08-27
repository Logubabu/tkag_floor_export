from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class UnitSystem(BaseModel):
    length: str = "m"       # m, mm, in, ft
    force: str = "kN"       # kN, N, kip, lb
    temperature: str = "C" # C, F


class Point3D(BaseModel):
    x: float
    y: float
    z: float


class Point2D(BaseModel):
    x: float
    y: float


class Node(BaseModel):
    id: str
    x: float
    y: float
    z: float
    story: Optional[str] = None
    restraints: List[bool] = Field(default_factory=lambda: [False, False, False, False, False, False]) # Ux, Uy, Uz, Rx, Ry, Rz


class Story(BaseModel):
    id: str
    name: str
    elevation: float
    height: float
    is_master: bool = False
    similar_to: Optional[str] = None


class Material(BaseModel):
    id: str
    name: str
    type: str = "Concrete"  # Concrete, Steel, Masonry
    elasticity_modulus: float = 30000000.0  # kPa / N/m^2
    fc: float = 30000.0                   # Concrete strength (kPa)
    poisson: float = 0.2


class FrameSection(BaseModel):
    id: str
    name: str
    material: str = "Concrete"
    shape: str = "Rectangular" # Rectangular, Circular, I-Section
    depth: float = 0.5        # m
    width: float = 0.3        # m
    color: Optional[str] = None


class ShellProperty(BaseModel):
    id: str
    name: str
    material: str = "Concrete"
    type: str = "Slab"        # Slab, Wall, Deck
    thickness: float = 0.2    # m
    color: Optional[str] = None


class FrameType(str, Enum):
    BEAM = "Beam"
    COLUMN = "Column"
    BRACE = "Brace"


class Frame(BaseModel):
    id: str
    type: FrameType
    start_node: str
    end_node: str
    start_point: Point3D
    end_point: Point3D
    section: str
    story: str
    material: Optional[str] = None
    color: Optional[str] = None
    angle: float = 0.0
    offset_1: Point3D = Field(default_factory=lambda: Point3D(x=0.0, y=0.0, z=0.0))
    offset_2: Point3D = Field(default_factory=lambda: Point3D(x=0.0, y=0.0, z=0.0))
    cardinal_point: int = 10


class Slab(BaseModel):
    id: str
    story: str
    polygon: List[Point2D]
    thickness: float = 0.2
    property_name: str = "SLAB"
    is_opening: bool = False
    material: Optional[str] = None
    elevation: float = 0.0
    color: Optional[str] = None


class Wall(BaseModel):
    id: str
    story: str
    polygon: List[Point2D]
    thickness: float = 0.25
    property_name: str = "WALL"
    material: Optional[str] = None
    top_z: float = 0.0
    bottom_z: float = 0.0
    color: Optional[str] = None


class AreaLoad(BaseModel):
    id: str
    area_id: str
    story: str
    pattern: str
    magnitude: float  # kN/m^2
    direction: str = "Gravity"


class PointLoad(BaseModel):
    id: str
    node_id: str
    story: str
    pattern: str
    fz: float = 0.0   # kN
    mx: float = 0.0   # kN-m
    my: float = 0.0   # kN-m


class LineLoad(BaseModel):
    id: str
    frame_id: str
    story: str
    pattern: str
    magnitude: float  # kN/m


class LoadPattern(BaseModel):
    name: str
    type: str = "Dead"
    self_weight_multiplier: float = 0.0


class BuildingModel(BaseModel):
    project_name: str = "ETABS Building Model"
    units: UnitSystem = Field(default_factory=UnitSystem)
    stories: List[Story] = Field(default_factory=list)
    materials: Dict[str, Material] = Field(default_factory=dict)
    frame_sections: Dict[str, FrameSection] = Field(default_factory=dict)
    shell_properties: Dict[str, ShellProperty] = Field(default_factory=dict)
    nodes: Dict[str, Node] = Field(default_factory=dict)
    frames: List[Frame] = Field(default_factory=list)
    slabs: List[Slab] = Field(default_factory=list)
    walls: List[Wall] = Field(default_factory=list)
    area_loads: List[AreaLoad] = Field(default_factory=list)
    point_loads: List[PointLoad] = Field(default_factory=list)
    line_loads: List[LineLoad] = Field(default_factory=list)
    load_patterns: List[LoadPattern] = Field(default_factory=list)


class ExtractionMode(str, Enum):
    SLAB_ONLY = "Mode A — Slab Only"
    SLAB_AND_SUPPORTS = "Mode B — Slab + Supporting Elements"
    COMPLETE_FLOOR = "Mode C — Complete Floor Model"


class FloorModel(BaseModel):
    story: Story
    mode: ExtractionMode = ExtractionMode.SLAB_AND_SUPPORTS
    units: UnitSystem = Field(default_factory=UnitSystem)
    slabs: List[Slab] = Field(default_factory=list)
    openings: List[Slab] = Field(default_factory=list)
    beams: List[Frame] = Field(default_factory=list)
    columns_above: List[Frame] = Field(default_factory=list)
    columns_below: List[Frame] = Field(default_factory=list)
    walls_above: List[Wall] = Field(default_factory=list)
    walls_below: List[Wall] = Field(default_factory=list)
    nodes: List[Node] = Field(default_factory=list)
    area_loads: List[AreaLoad] = Field(default_factory=list)
    point_loads: List[PointLoad] = Field(default_factory=list)
    line_loads: List[LineLoad] = Field(default_factory=list)


class AlertLevel(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class ValidationAlert(BaseModel):
    level: AlertLevel
    element_type: str
    element_id: str
    message: str
    action_tip: str


class ValidationResult(BaseModel):
    is_valid: bool
    summary: Dict[str, int]
    alerts: List[ValidationAlert] = Field(default_factory=list)
