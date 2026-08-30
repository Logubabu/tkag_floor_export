import pytest
import os
import tempfile
from app.models.intermediate import (
    StructuralModel, Story, Node, Slab, Wall, Column, Beam, Opening, Support, Material, Section, AreaLoad, Units
)
from app.models.units import UnitsSystem, convert_length, convert_force
from app.floor_extractor.floor_filter import FloorFilter
from app.validation.validator import ModelValidator
from app.conversion.converter import ModelConverter
from app.ram_concept.exporter import RAMConceptExporter
from app.ram_concept.verification import ExportVerifier
from app.reports.report_generator import ReportGenerator

@pytest.fixture
def golden_structural_model():
    """Creates a deterministic 3-story structural model for end-to-end integration tests."""
    model = StructuralModel(project_name="GoldenBuildingTest")
    model.units = Units(force="KN", length="M", temperature="C")
    
    # 1. Stories
    model.stories = [
        Story(name="Roof", elevation=9.0, height=3.0),
        Story(name="Floor 2", elevation=6.0, height=3.0),
        Story(name="Floor 1", elevation=3.0, height=3.0),
    ]
    
    # 2. Materials
    model.materials["C30"] = Material(name="C30", type="Concrete", fc=30.0, E=30000.0)
    
    # 3. Sections
    model.sections["C400x400"] = Section(name="C400x400", type="Column", b=0.4, h=0.4, material="C30")
    model.sections["B300x600"] = Section(name="B300x600", type="Beam", b=0.3, h=0.6, material="C30")
    model.sections["W250"] = Section(name="W250", type="Wall", thickness=0.25, material="C30")
    model.sections["S200"] = Section(name="S200", type="Slab", thickness=0.20, material="C30")
    
    # Nodes for Floor 2 (Z=6.0)
    nodes_f2 = {
        "N1": Node(id="N1", x=0.0, y=0.0, z=6.0),
        "N2": Node(id="N2", x=10.0, y=0.0, z=6.0),
        "N3": Node(id="N3", x=10.0, y=10.0, z=6.0),
        "N4": Node(id="N4", x=0.0, y=10.0, z=6.0),
        "N5": Node(id="N5", x=5.0, y=0.0, z=6.0),
        "N6": Node(id="N6", x=5.0, y=10.0, z=6.0),
    }
    # Nodes for Floor 1 (Z=3.0)
    nodes_f1 = {
        "N101": Node(id="N101", x=0.0, y=0.0, z=3.0),
        "N102": Node(id="N102", x=10.0, y=0.0, z=3.0),
        "N103": Node(id="N103", x=10.0, y=10.0, z=3.0),
        "N104": Node(id="N104", x=0.0, y=10.0, z=3.0),
        "N105": Node(id="N105", x=5.0, y=0.0, z=3.0),
        "N106": Node(id="N106", x=5.0, y=10.0, z=3.0),
    }
    model.nodes.update(nodes_f2)
    model.nodes.update(nodes_f1)
    
    # 4. Slabs (6 slabs total)
    model.slabs = [
        # Floor 2 slabs
        Slab(id="S201", story="Floor 2", points=[(0.0,0.0), (5.0,0.0), (5.0,10.0), (0.0,10.0)], section="S200", thickness=0.20, material="C30"),
        Slab(id="S202", story="Floor 2", points=[(5.0,0.0), (10.0,0.0), (10.0,10.0), (5.0,10.0)], section="S200", thickness=0.20, material="C30"),
        # Floor 1 slabs
        Slab(id="S101", story="Floor 1", points=[(0.0,0.0), (5.0,0.0), (5.0,10.0), (0.0,10.0)], section="S200", thickness=0.20, material="C30"),
        Slab(id="S102", story="Floor 1", points=[(5.0,0.0), (10.0,0.0), (10.0,10.0), (5.0,10.0)], section="S200", thickness=0.20, material="C30"),
        # Roof slabs
        Slab(id="SR01", story="Roof", points=[(0.0,0.0), (5.0,0.0), (5.0,10.0), (0.0,10.0)], section="S200", thickness=0.20, material="C30"),
        Slab(id="SR02", story="Roof", points=[(5.0,0.0), (10.0,0.0), (10.0,10.0), (5.0,10.0)], section="S200", thickness=0.20, material="C30"),
    ]
    
    # 5. Walls (3 walls)
    model.walls = [
        Wall(id="W1", story="Floor 2", p1=(0.0,0.0), p2=(0.0,10.0), thickness=0.25, height=3.0, section="W250", material="C30"),
        Wall(id="W2", story="Floor 1", p1=(0.0,0.0), p2=(0.0,10.0), thickness=0.25, height=3.0, section="W250", material="C30"),
        Wall(id="W3", story="Roof", p1=(0.0,0.0), p2=(0.0,10.0), thickness=0.25, height=3.0, section="W250", material="C30"),
    ]
    
    # 6. Columns (8 columns)
    model.columns = [
        # Floor 2 columns
        Column(id="C1", story="Floor 2", x=10.0, y=0.0, height=3.0, section="C400x400", material="C30"),
        Column(id="C2", story="Floor 2", x=10.0, y=10.0, height=3.0, section="C400x400", material="C30"),
        Column(id="C3", story="Floor 2", x=5.0, y=0.0, height=3.0, section="C400x400", material="C30"),
        Column(id="C4", story="Floor 2", x=5.0, y=10.0, height=3.0, section="C400x400", material="C30"),
        # Floor 1 columns
        Column(id="C101", story="Floor 1", x=10.0, y=0.0, height=3.0, section="C400x400", material="C30"),
        Column(id="C102", story="Floor 1", x=10.0, y=10.0, height=3.0, section="C400x400", material="C30"),
        Column(id="C103", story="Floor 1", x=5.0, y=0.0, height=3.0, section="C400x400", material="C30"),
        Column(id="C104", story="Floor 1", x=5.0, y=10.0, height=3.0, section="C400x400", material="C30"),
    ]
    
    # 7. Beams (12 beams)
    model.beams = [
        # Floor 2 beams (4)
        Beam(id="B1", story="Floor 2", p1=(0.0,0.0), p2=(5.0,0.0), section="B300x600", material="C30"),
        Beam(id="B2", story="Floor 2", p1=(5.0,0.0), p2=(10.0,0.0), section="B300x600", material="C30"),
        Beam(id="B3", story="Floor 2", p1=(0.0,10.0), p2=(5.0,10.0), section="B300x600", material="C30"),
        Beam(id="B4", story="Floor 2", p1=(5.0,10.0), p2=(10.0,10.0), section="B300x600", material="C30"),
        # Floor 1 beams (4)
        Beam(id="B101", story="Floor 1", p1=(0.0,0.0), p2=(5.0,0.0), section="B300x600", material="C30"),
        Beam(id="B102", story="Floor 1", p1=(5.0,0.0), p2=(10.0,0.0), section="B300x600", material="C30"),
        Beam(id="B103", story="Floor 1", p1=(0.0,10.0), p2=(5.0,10.0), section="B300x600", material="C30"),
        Beam(id="B104", story="Floor 1", p1=(5.0,10.0), p2=(10.0,10.0), section="B300x600", material="C30"),
        # Roof beams (4)
        Beam(id="BR01", story="Roof", p1=(0.0,0.0), p2=(5.0,0.0), section="B300x600", material="C30"),
        Beam(id="BR02", story="Roof", p1=(5.0,0.0), p2=(10.0,0.0), section="B300x600", material="C30"),
        Beam(id="BR03", story="Roof", p1=(0.0,10.0), p2=(5.0,10.0), section="B300x600", material="C30"),
        Beam(id="BR04", story="Roof", p1=(5.0,10.0), p2=(10.0,10.0), section="B300x600", material="C30"),
    ]
    
    # 8. Openings (2)
    model.openings = [
        Opening(id="OP1", story="Floor 2", points=[(2.0,2.0), (4.0,2.0), (4.0,4.0), (2.0,4.0)]),
        Opening(id="OP2", story="Floor 1", points=[(2.0,2.0), (4.0,2.0), (4.0,4.0), (2.0,4.0)]),
    ]
    
    # 9. Supports (6)
    model.supports = [
        Support(id="SUP1", node_id="N101", ux=True, uy=True, uz=True, rx=True, ry=True, rz=True),
        Support(id="SUP2", node_id="N102", ux=True, uy=True, uz=True, rx=True, ry=True, rz=True),
        Support(id="SUP3", node_id="N103", ux=True, uy=True, uz=True, rx=True, ry=True, rz=True),
        Support(id="SUP4", node_id="N104", ux=True, uy=True, uz=True, rx=True, ry=True, rz=True),
        Support(id="SUP5", node_id="N105", ux=True, uy=True, uz=True, rx=True, ry=True, rz=True),
        Support(id="SUP6", node_id="N106", ux=True, uy=True, uz=True, rx=True, ry=True, rz=True),
    ]
    
    # 10. Area Loads
    model.area_loads = [
        AreaLoad(id="L1", story="Floor 2", pattern="DEAD", value=1.5, points=[(0.0,0.0),(10.0,0.0),(10.0,10.0),(0.0,10.0)]),
        AreaLoad(id="L2", story="Floor 2", pattern="LIVE", value=2.5, points=[(0.0,0.0),(10.0,0.0),(10.0,10.0),(0.0,10.0)]),
    ]
    
    return model

def test_golden_model_counts(golden_structural_model):
    assert len(golden_structural_model.stories) == 3
    assert len(golden_structural_model.slabs) == 6
    assert len(golden_structural_model.walls) == 3
    assert len(golden_structural_model.columns) == 8
    assert len(golden_structural_model.beams) == 12
    assert len(golden_structural_model.openings) == 2
    assert len(golden_structural_model.supports) == 6

def test_golden_model_floor_filtering(golden_structural_model):
    filter_engine = FloorFilter(golden_structural_model)
    filtered = filter_engine.filter_stories(["Floor 2"])
    
    assert len(filtered.stories) == 1
    assert len(filtered.slabs) == 2
    assert len(filtered.walls) == 1
    assert len(filtered.columns) == 4
    assert len(filtered.beams) == 4
    assert len(filtered.openings) == 1

def test_golden_model_validation(golden_structural_model):
    validator = ModelValidator()
    results = validator.validate(golden_structural_model)
    
    # Expect 0 errors
    errors = [r for r in results if r.level == "ERROR"]
    assert len(errors) == 0

def test_golden_model_ram_concept_export(golden_structural_model):
    filter_engine = FloorFilter(golden_structural_model)
    filtered = filter_engine.filter_stories(["Floor 2"])
    
    converter = ModelConverter()
    converted = converter.convert(filtered)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        cpt_path = os.path.join(tmp_dir, "Golden_Floor2.cpt")
        dxf_path = os.path.join(tmp_dir, "Golden_Floor2.dxf")
        cpf_path = os.path.join(tmp_dir, "Golden_Floor2.cpf")
        
        exporter = RAMConceptExporter()
        export_res = exporter.export_model(converted, cpt_path, dxf_path=dxf_path, cpf_path=cpf_path)
        
        assert os.path.exists(cpt_path)
        assert os.path.exists(dxf_path)
        assert os.path.exists(cpf_path)
        assert os.path.getsize(cpt_path) > 0
        assert os.path.getsize(dxf_path) > 0
        assert os.path.getsize(cpf_path) > 0

def test_golden_model_export_verification(golden_structural_model):
    filter_engine = FloorFilter(golden_structural_model)
    filtered = filter_engine.filter_stories(["Floor 2"])
    
    converter = ModelConverter()
    converted = converter.convert(filtered)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        cpt_path = os.path.join(tmp_dir, "Golden_Floor2.cpt")
        dxf_path = os.path.join(tmp_dir, "Golden_Floor2.dxf")
        
        exporter = RAMConceptExporter()
        exporter.export_model(converted, cpt_path, dxf_path=dxf_path)
        
        verifier = ExportVerifier()
        v_result = verifier.verify_export(converted, cpt_path, dxf_path=dxf_path)
        assert v_result["status"] == "VERIFIED"
        assert v_result["checks"]["cpt_exists"] is True
        assert v_result["checks"]["cpt_non_empty"] is True
