"""
Floor Filter Engine.
Filters normalized structural models by single or multiple story selection
with spatial elevation bounding rules for columns and walls spanning multiple levels.
"""
from typing import List, Set
from app.models.intermediate import StructuralModel, Story

class FloorFilter:
    """Filters structural elements by selected story names."""

    def __init__(self, model: StructuralModel):
        self.model = model

    def filter_stories(self, selected_story_names: List[str]) -> StructuralModel:
        """
        Extracts all structural elements associated with the selected stories.
        """
        if not selected_story_names:
            return StructuralModel(project_name=self.model.project_name, units=self.model.units)

        target_set: Set[str] = set(selected_story_names)
        
        # 1. Filter stories list
        selected_stories = [st for st in self.model.stories if st.name in target_set]
        
        # Calculate elevation bounds of selected stories
        elevations = [st.elevation for st in selected_stories]
        min_elev = min(elevations) - 0.1 if elevations else -1e9
        max_elev = max(elevations) + 0.1 if elevations else 1e9

        # Filter nodes within elevation range or associated story
        selected_nodes = {
            node_id: node
            for node_id, node in self.model.nodes.items()
            if min_elev <= node.z <= max_elev or (node.story and node.story in target_set)
        }

        # 2. Filter Slabs & Openings
        selected_slabs = []
        selected_openings = [op for op in self.model.openings if op.story in target_set]

        for s in self.model.slabs:
            if s.story in target_set:
                prop_upper = (s.property_name or "").upper()
                is_op = (
                    s.is_opening or
                    prop_upper in ["OPENING", "VOID", "OPEN", "NONE", "CUTOUT", "SHAFT", "HOLE"] or
                    any(k in prop_upper for k in ["OPEN", "VOID", "CUTOUT", "SHAFT", "HOLE"]) or
                    s.thickness == 0.0
                )
                if is_op:
                    from app.models.intermediate import Opening
                    if not any(o.id == s.id for o in selected_openings):
                        selected_openings.append(Opening(id=s.id, story=s.story, polygon=s.polygon, points=[(p.x, p.y) for p in s.polygon]))
                else:
                    selected_slabs.append(s)

        # 4. Filter Walls
        # Include walls whose story is in selection or story_below is in selection
        selected_walls = [
            w for w in self.model.walls
            if w.story in target_set or (w.story_below and w.story_below in target_set)
        ]

        # 5. Filter Columns
        selected_columns = [
            c for c in self.model.columns
            if c.story in target_set or (c.story_below and c.story_below in target_set)
        ]

        # 6. Filter Beams
        selected_beams = [b for b in self.model.beams if b.story in target_set]

        # 7. Filter Supports
        selected_supports = [
            sup for sup in self.model.supports
            if sup.node_id in selected_nodes or sup.id in target_set
        ]

        # 8. Filter Area Loads
        selected_loads = [ld for ld in self.model.area_loads if ld.story in target_set]

        filtered_model = StructuralModel(
            project_name=f"{self.model.project_name}_Filtered",
            units=self.model.units,
            stories=selected_stories,
            nodes=selected_nodes,
            slabs=selected_slabs,
            walls=selected_walls,
            columns=selected_columns,
            beams=selected_beams,
            openings=selected_openings,
            supports=selected_supports,
            materials=self.model.materials.copy(),
            sections=self.model.sections.copy(),
            area_loads=selected_loads,
        )
        return filtered_model
