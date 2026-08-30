from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from pydantic import BaseModel, Field


class UnitSystem(BaseModel):
    length: str = "m"       # m, mm, in, ft
    force: str = "kN"       # kN, N, kip, lb
    temperature: str = "C" # C, F

Units = UnitSystem


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


class Support(BaseModel):
    id: str
    node_id: str
    ux: bool = True
    uy: bool = True
    uz: bool = True
    rx: bool = True
    ry: bool = True
    rz: bool = True


class Story(BaseModel):
    id: str = ""
    name: str
    elevation: float
    height: float
    is_master: bool = False
    similar_to: Optional[str] = None

    def __init__(self, **data):
        if "id" not in data or not data["id"]:
            data["id"] = data.get("name", "")
        super().__init__(**data)


class Material(BaseModel):
    id: str = ""
    name: str
    type: str = "Concrete"  # Concrete, Steel, Masonry
    elasticity_modulus: float = 30000000.0  # kPa / N/m^2
    fc: float = 30000.0                   # Concrete strength (kPa)
    poisson: float = 0.2

    def __init__(self, **data):
        if "id" not in data or not data["id"]:
            data["id"] = data.get("name", "")
        super().__init__(**data)


class FrameSection(BaseModel):
    id: str = ""
    name: str
    material: str = "Concrete"
    shape: str = "Rectangular" # Rectangular, Circular, I-Section
    depth: float = 0.5        # m
    width: float = 0.3        # m
    b: float = 0.3
    h: float = 0.5
    thickness: float = 0.2
    type: str = "Column"
    color: Optional[str] = None

    def __init__(self, **data):
        if "id" not in data or not data["id"]:
            data["id"] = data.get("name", "")
        if "b" in data and "width" not in data:
            data["width"] = data["b"]
        if "h" in data and "depth" not in data:
            data["depth"] = data["h"]
        super().__init__(**data)

Section = FrameSection


class ShellProperty(BaseModel):
    id: str = ""
    name: str
    material: str = "Concrete"
    type: str = "Slab"        # Slab, Wall, Deck
    thickness: float = 0.2    # m
    color: Optional[str] = None

    def __init__(self, **data):
        if "id" not in data or not data["id"]:
            data["id"] = data.get("name", "")
        super().__init__(**data)


class FrameType(str, Enum):
    BEAM = "Beam"
    COLUMN = "Column"
    BRACE = "Brace"


class Frame(BaseModel):
    id: str
    type: FrameType = FrameType.BEAM
    start_node: str = ""
    end_node: str = ""
    start_point: Optional[Point3D] = None
    end_point: Optional[Point3D] = None
    section: str = ""
    story: str = ""
    story_below: Optional[str] = None
    p1: Optional[Tuple[float, float]] = None
    p2: Optional[Tuple[float, float]] = None
    x: float = 0.0
    y: float = 0.0
    height: float = 3.0
    material: Optional[str] = None
    color: Optional[str] = None
    angle: float = 0.0
    cardinal_point: int = 10

Beam = Frame
Column = Frame


class Slab(BaseModel):
    id: str
    story: str
    polygon: List[Point2D] = Field(default_factory=list)
    points: List[Tuple[float, float]] = Field(default_factory=list)
    thickness: float = 0.2
    property_name: str = "SLAB"
    section: str = "SLAB"
    is_opening: bool = False
    material: Optional[str] = None
    elevation: float = 0.0
    color: Optional[str] = None

    def __init__(self, **data):
        if "points" in data and not data.get("polygon"):
            data["polygon"] = [Point2D(x=p[0], y=p[1]) for p in data["points"]]
        elif "polygon" in data and not data.get("points"):
            data["points"] = [(p.x, p.y) for p in data["polygon"]]
        super().__init__(**data)


class Opening(BaseModel):
    id: str
    story: str
    points: List[Tuple[float, float]] = Field(default_factory=list)
    polygon: List[Point2D] = Field(default_factory=list)

    def __init__(self, **data):
        if "points" in data and not data.get("polygon"):
            data["polygon"] = [Point2D(x=p[0], y=p[1]) for p in data["points"]]
        elif "polygon" in data and not data.get("points"):
            data["points"] = [(p.x, p.y) for p in data["polygon"]]
        super().__init__(**data)


class Wall(BaseModel):
    id: str
    story: str
    story_below: Optional[str] = None
    polygon: List[Point2D] = Field(default_factory=list)
    p1: Optional[Tuple[float, float]] = None
    p2: Optional[Tuple[float, float]] = None
    thickness: float = 0.25
    height: float = 3.0
    section: str = "WALL"
    property_name: str = "WALL"
    material: Optional[str] = None
    top_z: float = 0.0
    bottom_z: float = 0.0
    color: Optional[str] = None

    @property
    def start_point(self) -> Point3D:
        if self.p1:
            return Point3D(x=self.p1[0], y=self.p1[1], z=self.bottom_z)
        elif self.polygon and len(self.polygon) > 0:
            return Point3D(x=self.polygon[0].x, y=self.polygon[0].y, z=self.bottom_z)
        return Point3D(x=0.0, y=0.0, z=self.bottom_z)

    @property
    def end_point(self) -> Point3D:
        if self.p2:
            return Point3D(x=self.p2[0], y=self.p2[1], z=self.top_z)
        elif self.polygon and len(self.polygon) > 1:
            return Point3D(x=self.polygon[1].x, y=self.polygon[1].y, z=self.top_z)
        return Point3D(x=0.0, y=0.0, z=self.top_z)


class AreaLoad(BaseModel):
    id: str
    area_id: str = ""
    story: str = ""
    pattern: str = "DEAD"
    magnitude: float = 0.0 # kN/m^2
    value: float = 0.0
    points: List[Tuple[float, float]] = Field(default_factory=list)
    direction: str = "Gravity"

    def __init__(self, **data):
        if "value" in data and ("magnitude" not in data or data["magnitude"] == 0.0):
            data["magnitude"] = data["value"]
        elif "magnitude" in data and ("value" not in data or data["value"] == 0.0):
            data["value"] = data["magnitude"]
        super().__init__(**data)


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
    sections: Dict[str, FrameSection] = Field(default_factory=dict)
    frame_sections: Dict[str, FrameSection] = Field(default_factory=dict)
    shell_properties: Dict[str, ShellProperty] = Field(default_factory=dict)
    nodes: Dict[str, Node] = Field(default_factory=dict)
    frames: List[Frame] = Field(default_factory=list)
    columns: List[Column] = Field(default_factory=list)
    beams: List[Beam] = Field(default_factory=list)
    slabs: List[Slab] = Field(default_factory=list)
    walls: List[Wall] = Field(default_factory=list)
    openings: List[Opening] = Field(default_factory=list)
    supports: List[Support] = Field(default_factory=list)
    area_loads: List[AreaLoad] = Field(default_factory=list)
    point_loads: List[PointLoad] = Field(default_factory=list)
    line_loads: List[LineLoad] = Field(default_factory=list)
    load_patterns: List[LoadPattern] = Field(default_factory=list)

StructuralModel = BuildingModel


class ExtractionMode(str, Enum):
    SLAB_ONLY = "Mode A — Slab Only"
    SLAB_AND_SUPPORTS = "Mode B — Slab + Supporting Elements"
    COMPLETE_FLOOR = "Mode C — Complete Floor Model"


class FloorModel(BaseModel):
    story: Story
    mode: ExtractionMode = ExtractionMode.SLAB_AND_SUPPORTS
    units: UnitSystem = Field(default_factory=UnitSystem)
    slabs: List[Slab] = Field(default_factory=list)
    openings: List[Opening] = Field(default_factory=list)
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
