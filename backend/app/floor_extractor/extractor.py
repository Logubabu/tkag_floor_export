from typing import List, Optional
from app.models.intermediate import (
    BuildingModel, FloorModel, Story, Slab, Frame, Wall, Node, AreaLoad,
    PointLoad, LineLoad, ExtractionMode, FrameType, Point3D
)


class FloorExtractor:
    """
    Structural Floor Extraction Engine.
    Isolates single floor models from full building models while preserving
    structural relationships (supporting columns/walls above & below).
    """
    @staticmethod
    def extract_floor(
        model: BuildingModel,
        story_name: str,
        mode: ExtractionMode = ExtractionMode.SLAB_AND_SUPPORTS
    ) -> FloorModel:
        # 1. Locate story
        target_story: Optional[Story] = None
        for st in model.stories:
            if st.name.lower() == story_name.lower():
                target_story = st
                break

        if not target_story:
            # Fallback mock story if not found directly
            target_story = Story(id=f"story_{story_name}", name=story_name, elevation=0.0, height=3.0)

        story_elev = target_story.elevation
        elev_tol = 0.1  # meters

        # 2. Extract Slabs & Openings for story
        slabs: List[Slab] = []
        openings: List[Slab] = []
        for sl in model.slabs:
            if sl.story.lower() == story_name.lower() or abs(sl.elevation - story_elev) < elev_tol:
                if sl.is_opening:
                    openings.append(sl)
                else:
                    slabs.append(sl)

        # 3. Extract Beams (Frame elements lying on story floor level)
        beams: List[Frame] = []
        for fr in model.frames:
            if fr.type == FrameType.BEAM:
                if fr.story.lower() == story_name.lower() or (abs(fr.start_point.z - story_elev) < elev_tol and abs(fr.end_point.z - story_elev) < elev_tol):
                    beams.append(fr)

        # 4. Mode A — Slab Only return
        if mode == ExtractionMode.SLAB_ONLY:
            return FloorModel(
                story=target_story,
                mode=mode,
                units=model.units,
                slabs=slabs,
                openings=openings,
                area_loads=[al for al in model.area_loads if al.story.lower() == story_name.lower()]
            )

        # 5. Extract Columns Above and Below
        columns_above: List[Frame] = []
        columns_below: List[Frame] = []
        for fr in model.frames:
            if fr.type == FrameType.COLUMN:
                min_z = min(fr.start_point.z, fr.end_point.z)
                max_z = max(fr.start_point.z, fr.end_point.z)
                
                # Column extending below story down to lower floor
                if abs(max_z - story_elev) < elev_tol:
                    columns_below.append(fr)
                # Column extending above story up to upper floor
                elif abs(min_z - story_elev) < elev_tol:
                    columns_above.append(fr)
                elif fr.story.lower() == story_name.lower():
                    columns_below.append(fr)

        # 6. Extract Walls Above and Below
        walls_above: List[Wall] = []
        walls_below: List[Wall] = []
        for w in model.walls:
            min_z = min(w.top_z, w.bottom_z)
            max_z = max(w.top_z, w.bottom_z)
            
            if abs(max_z - story_elev) < elev_tol:
                walls_below.append(w)
            elif abs(min_z - story_elev) < elev_tol:
                walls_above.append(w)
            elif w.story.lower() == story_name.lower():
                walls_below.append(w)

        # 7. Extract Nodes on floor level
        floor_nodes: List[Node] = []
        for nd in model.nodes.values():
            if abs(nd.z - story_elev) < elev_tol or (nd.story and nd.story.lower() == story_name.lower()):
                floor_nodes.append(nd)

        # 8. Filter Loads for story
        area_loads = [al for al in model.area_loads if al.story.lower() == story_name.lower()]
        point_loads = [pl for pl in model.point_loads if pl.story.lower() == story_name.lower()]
        line_loads = [ll for ll in model.line_loads if ll.story.lower() == story_name.lower()]

        return FloorModel(
            story=target_story,
            mode=mode,
            units=model.units,
            slabs=slabs,
            openings=openings,
            beams=beams,
            columns_above=columns_above,
            columns_below=columns_below,
            walls_above=walls_above,
            walls_below=walls_below,
            nodes=floor_nodes,
            area_loads=area_loads,
            point_loads=point_loads,
            line_loads=line_loads
        )
