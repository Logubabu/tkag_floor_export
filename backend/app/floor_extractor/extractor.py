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
            if st.name.lower().strip() == story_name.lower().strip():
                target_story = st
                break

        if not target_story:
            target_story = Story(id=f"story_{story_name}", name=story_name, elevation=0.0, height=3.0)

        story_elev = target_story.elevation
        story_height = target_story.height if target_story.height > 0 else 3.5
        elev_tol = 0.35  # meters tolerance for story floor level

        s_name_clean = story_name.strip().lower().replace(" ", "").replace("_", "").replace("-", "")

        # Strict exact story match helper
        def is_story_match(val: Optional[str]) -> bool:
            if not val:
                return False
            clean_val = val.strip().lower().replace(" ", "").replace("_", "").replace("-", "")
            return clean_val == s_name_clean

        # 2. Extract Slabs & Openings for story
        slabs: List[Slab] = []
        openings: List[Slab] = []
        for sl in model.slabs:
            if is_story_match(sl.story) or abs(sl.elevation - story_elev) < elev_tol:
                if sl.is_opening:
                    openings.append(sl)
                else:
                    slabs.append(sl)

        # 3. Extract Beams (Frame elements lying on story floor level)
        beams: List[Frame] = []
        for fr in model.frames:
            if fr.type == FrameType.BEAM:
                if is_story_match(fr.story) or (abs(fr.start_point.z - story_elev) < elev_tol and abs(fr.end_point.z - story_elev) < elev_tol):
                    beams.append(fr)

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

        # 5. Extract Columns Above and Below with exact elevation bounds
        columns_above: List[Frame] = []
        columns_below: List[Frame] = []

        for fr in model.frames:
            if fr.type == FrameType.COLUMN:
                min_z = min(fr.start_point.z, fr.end_point.z)
                max_z = max(fr.start_point.z, fr.end_point.z)

                # Column Below: top node connects to floor elevation (story_elev)
                if abs(max_z - story_elev) < elev_tol:
                    columns_below.append(fr)
                # Column Above: bottom node connects to floor elevation (story_elev)
                elif abs(min_z - story_elev) < elev_tol:
                    columns_above.append(fr)
                # Column Spanning across floor elevation
                elif min_z + 0.1 < story_elev < max_z - 0.1:
                    columns_below.append(fr)
                elif is_story_match(fr.story):
                    columns_below.append(fr)

        # 6. Extract Walls Above and Below with exact elevation bounds
        walls_above: List[Wall] = []
        walls_below: List[Wall] = []
        for w in model.walls:
            min_z = min(w.top_z, w.bottom_z)
            max_z = max(w.top_z, w.bottom_z)

            if abs(max_z - story_elev) < elev_tol:
                walls_below.append(w)
            elif abs(min_z - story_elev) < elev_tol:
                walls_above.append(w)
            elif min_z + 0.1 < story_elev < max_z - 0.1:
                walls_below.append(w)
            elif is_story_match(w.story):
                walls_below.append(w)

        # 7. Extract Nodes on story floor level
        floor_nodes: List[Node] = []
        for nd in model.nodes.values():
            if abs(nd.z - story_elev) < elev_tol or is_story_match(nd.story):
                floor_nodes.append(nd)

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
