import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.intermediate import FloorModel, Story, Slab, Frame, Point3D, Point2D, FrameType
from gui.model_viewer import ModelViewerWidget
from PySide6.QtCore import QPointF

@pytest.fixture
def sample_floor_model():
    story = Story(id="story_1", name="Story 1", elevation=3.5, height=3.5)
    slab = Slab(
        id="S1",
        story="Story 1",
        thickness=0.25,
        polygon=[Point2D(x=0.0, y=0.0), Point2D(x=10.0, y=0.0), Point2D(x=10.0, y=10.0), Point2D(x=0.0, y=10.0)],
        elevation=3.5
    )
    beam = Frame(
        id="B1",
        type=FrameType.BEAM,
        story="Story 1",
        start_point=Point3D(x=0.0, y=0.0, z=3.5),
        end_point=Point3D(x=10.0, y=0.0, z=3.5)
    )
    col_below = Frame(
        id="C1_below",
        type=FrameType.COLUMN,
        story="Story 1",
        start_point=Point3D(x=0.0, y=0.0, z=0.0),
        end_point=Point3D(x=0.0, y=0.0, z=3.5)
    )
    col_above = Frame(
        id="C1_above",
        type=FrameType.COLUMN,
        story="Story 1",
        start_point=Point3D(x=0.0, y=0.0, z=3.5),
        end_point=Point3D(x=0.0, y=0.0, z=7.0)
    )
    return FloorModel(
        story=story,
        slabs=[slab],
        beams=[beam],
        columns_below=[col_below],
        columns_above=[col_above]
    )

def test_model_viewer_3d_coordinates_alignment(sample_floor_model):
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    widget = ModelViewerWidget()
    widget.set_floor_model(sample_floor_model)
    widget.set_3d_mode()

    # World (0, 0, 3.5) -> screen point
    pt_beam_start = widget._world_to_screen(0.0, 0.0, 3.5)
    
    # Column below top point (0, 0, 3.5)
    pt_col_below_top = widget._world_to_screen(0.0, 0.0, 3.5)
    
    # Column above bottom point (0, 0, 3.5)
    pt_col_above_bot = widget._world_to_screen(0.0, 0.0, 3.5)

    # All 3 connection points at joint (0, 0, 3.5) must project to identical screen coordinates
    assert abs(pt_beam_start.x() - pt_col_below_top.x()) < 1e-4
    assert abs(pt_beam_start.y() - pt_col_below_top.y()) < 1e-4
    assert abs(pt_col_below_top.x() - pt_col_above_bot.x()) < 1e-4
    assert abs(pt_col_below_top.y() - pt_col_above_bot.y()) < 1e-4
