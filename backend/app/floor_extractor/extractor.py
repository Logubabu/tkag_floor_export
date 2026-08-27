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
        elev_tol = 0.5  # meters
        s_name_clean = story_name.strip().lower().replace(" ", "").replace("_", "").replace("-", "")

        # Helper for matching story string tokens
        def is_story_match(val: Optional[str]) -> bool:
            if not val:
                return False
            clean_val = val.strip().lower().replace(" ", "").replace("_", "").replace("-", "")
            return clean_val == s_name_clean or s_name_clean in clean_val or clean_val in s_name_clean

        # 2. Extract Slabs & Openings for story
        slabs: List[Slab] = []
        openings: List[Slab] = []
        for sl in model.slabs:
            if is_story_match(sl.story) or abs(sl.elevation - story_elev) < elev_tol or (sl.story and sl.story.lower() == story_name.lower()):
                if sl.is_opening:
                    openings.append(sl)
                else:
                    slabs.append(sl)

        # Fallback if no slabs matched story name/elevation directly
        if not slabs and model.slabs:
            target_idx = next((i for i, st in enumerate(model.stories) if is_story_match(st.name)), 0)
            if target_idx < len(model.slabs):
                slabs.append(model.slabs[target_idx])
            else:
                slabs.append(model.slabs[0])

        # 3. Extract Beams (Frame elements lying on story floor level)
        beams: List[Frame] = []
        for fr in model.frames:
            if fr.type == FrameType.BEAM:
                if is_story_match(fr.story) or (abs(fr.start_point.z - story_elev) < elev_tol and abs(fr.end_point.z - story_elev) < elev_tol):
                    beams.append(fr)

        if not beams and model.frames:
            beams = [fr for fr in model.frames if fr.type == FrameType.BEAM]

        # 4. Mode A — Slab Only return
        if mode == ExtractionMode.SLAB_ONLY:
            return FloorModel(
                story=target_story,
                mode=mode,
                units=model.units,
                slabs=slabs,
                openings=openings,
                area_loads=[al for al in model.area_loads if is_story_match(al.story)]
            )

        # 5. Extract Columns Above and Below
        columns_above: List[Frame] = []
        columns_below: List[Frame] = []

        for fr in model.frames:
            if fr.type == FrameType.COLUMN:
                min_z = min(fr.start_point.z, fr.end_point.z)
                max_z = max(fr.start_point.z, fr.end_point.z)

                if abs(max_z - story_elev) < 0.8 or is_story_match(fr.story):
                    columns_below.append(fr)
                elif abs(min_z - story_elev) < 0.8:
                    columns_above.append(fr)
                elif min_z < story_elev < max_z:
                    columns_below.append(fr)

        if not columns_below and not columns_above and model.frames:
            columns_below = [fr for fr in model.frames if fr.type == FrameType.COLUMN]

        # 6. Extract Walls Above and Below
        walls_above: List[Wall] = []
        walls_below: List[Wall] = []
        for w in model.walls:
            min_z = min(w.top_z, w.bottom_z)
            max_z = max(w.top_z, w.bottom_z)

            if abs(max_z - story_elev) < 0.8 or is_story_match(w.story):
                walls_below.append(w)
            elif abs(min_z - story_elev) < 0.8:
                walls_above.append(w)
            elif min_z < story_elev < max_z:
                walls_below.append(w)

        if not walls_below and not walls_above and model.walls:
            walls_below = list(model.walls)

        # 7. Extract Nodes on floor level
        floor_nodes: List[Node] = []
        for nd in model.nodes.values():
            if abs(nd.z - story_elev) < 0.8 or is_story_match(nd.story):
                floor_nodes.append(nd)

        if not floor_nodes and model.nodes:
            floor_nodes = list(model.nodes.values())

        # 8. Filter Loads for story
        area_loads = [al for al in model.area_loads if is_story_match(al.story)]
        point_loads = [pl for pl in model.point_loads if is_story_match(pl.story)]
        line_loads = [ll for ll in model.line_loads if is_story_match(ll.story)]

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
