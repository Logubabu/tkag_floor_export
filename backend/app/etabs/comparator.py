import math
from typing import Dict, Any, List, Optional
from app.models.intermediate import BuildingModel, Story, Slab, Frame, Wall

class ModelComparator:
    """
    Automated $ET vs EDB model comparator.
    Computes precise metric comparisons between two parsed BuildingModels (e.g. $ET vs EDB).
    """
    def compare(self, model_et: BuildingModel, model_edb: BuildingModel) -> Dict[str, Any]:
        story_diff = self._compare_stories(model_et.stories, model_edb.stories)
        node_count_et = len(model_et.nodes)
        node_count_edb = len(model_edb.nodes)
        
        slab_count_et = len([s for s in model_et.slabs if not s.is_opening])
        slab_count_edb = len([s for s in model_edb.slabs if not s.is_opening])
        opening_count_et = len([s for s in model_et.slabs if s.is_opening])
        opening_count_edb = len([s for s in model_edb.slabs if s.is_opening])
        
        beam_count_et = len([f for f in model_et.frames if f.type == "Beam"])
        beam_count_edb = len([f for f in model_edb.frames if f.type == "Beam"])
        col_count_et = len([f for f in model_edb.frames if f.type == "Column"])
        col_count_edb = len([f for f in model_edb.frames if f.type == "Column"])
        
        wall_count_et = len(model_et.walls)
        wall_count_edb = len(model_edb.walls)
        
        bbox_et = self._compute_bounding_box(model_et)
        bbox_edb = self._compute_bounding_box(model_edb)

        summary_rows = [
            {"category": "Stories", "et_count": len(model_et.stories), "edb_count": len(model_edb.stories), "difference": len(model_edb.stories) - len(model_et.stories)},
            {"category": "Nodes", "et_count": node_count_et, "edb_count": node_count_edb, "difference": node_count_edb - node_count_et},
            {"category": "Slabs", "et_count": slab_count_et, "edb_count": slab_count_edb, "difference": slab_count_edb - slab_count_et},
            {"category": "Openings", "et_count": opening_count_et, "edb_count": opening_count_edb, "difference": opening_count_edb - opening_count_et},
            {"category": "Beams", "et_count": beam_count_et, "edb_count": beam_count_edb, "difference": beam_count_edb - beam_count_et},
            {"category": "Columns", "et_count": col_count_et, "edb_count": col_count_edb, "difference": col_count_edb - col_count_et},
            {"category": "Walls", "et_count": wall_count_et, "edb_count": wall_count_edb, "difference": wall_count_edb - wall_count_et},
        ]
        
        is_match = (
            len(model_et.stories) == len(model_edb.stories) and
            node_count_et == node_count_edb and
            slab_count_et == slab_count_edb and
            beam_count_et == beam_count_edb and
            col_count_et == col_count_edb and
            wall_count_et == wall_count_edb
        )

        return {
            "is_match": is_match,
            "summary": summary_rows,
            "story_diff": story_diff,
            "bounding_box": {
                "et": bbox_et,
                "edb": bbox_edb,
                "match": bbox_et == bbox_edb
            }
        }

    def _compare_stories(self, stories_et: List[Story], stories_edb: List[Story]) -> List[Dict[str, Any]]:
        et_map = {s.name.lower(): s for s in stories_et}
        edb_map = {s.name.lower(): s for s in stories_edb}
        diff = []
        all_names = sorted(list(set(et_map.keys()).union(set(edb_map.keys()))))
        for name in all_names:
            s_et = et_map.get(name)
            s_edb = edb_map.get(name)
            diff.append({
                "story_name": s_et.name if s_et else s_edb.name,
                "et_elevation": s_et.elevation if s_et else None,
                "edb_elevation": s_edb.elevation if s_edb else None,
                "match": (s_et and s_edb and abs(s_et.elevation - s_edb.elevation) < 1e-3)
            })
        return diff

    def _compute_bounding_box(self, model: BuildingModel) -> Dict[str, float]:
        if not model.nodes:
            return {"min_x": 0.0, "max_x": 0.0, "min_y": 0.0, "max_y": 0.0, "min_z": 0.0, "max_z": 0.0}
        xs = [n.x for n in model.nodes.values()]
        ys = [n.y for n in model.nodes.values()]
        zs = [n.z for n in model.nodes.values()]
        return {
            "min_x": round(min(xs), 3),
            "max_x": round(max(xs), 3),
            "min_y": round(min(ys), 3),
            "max_y": round(max(ys), 3),
            "min_z": round(min(zs), 3),
            "max_z": round(max(zs), 3),
        }
