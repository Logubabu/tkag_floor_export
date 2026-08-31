from typing import Dict, List, Any, Tuple, Optional
import math
from app.models.intermediate import BuildingModel, Story, Node, Frame, Slab, Wall, FrameType, Point2D, Point3D

LATERAL_PATTERNS = {'EX+', 'EX-', 'EY+', 'EY-', 'WX', 'WY'}
GRAVITY_PATTERNS = {'OW', 'SIDL', 'LN', 'H'}


class TributaryLoadPathEngine:
    """
    Tributary Load Path Engine for ETABS Models.
    Marches vertical self-weight (slabs, beams, columns, walls) and uniform area loads (SIDL/LN/H)
    down story by story from roof to foundation level.
    Computes cumulative column & wall base reactions (Fz).
    """
    @staticmethod
    def is_gravity_combo(combo_cases: List[Tuple[str, float]]) -> bool:
        return all(case_name in GRAVITY_PATTERNS or case_name == 'T' for case_name, _ in combo_cases)

    @staticmethod
    def in_polygon(x: float, y: float, polygon: List[Tuple[float, float]]) -> bool:
        inside = False
        j = len(polygon) - 1
        for i in range(len(polygon)):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    @staticmethod
    def seg_dist(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
        dx = x2 - x1
        dy = y2 - y1
        length_sq = dx * dx + dy * dy
        if length_sq == 0.0:
            return math.hypot(px - x1, py - y1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
        return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

    @classmethod
    def nearest_support(cls, supports: List[Dict[str, Any]], x: float, y: float) -> int:
        best_idx = -1
        best_dist = float('inf')
        for i, sup in enumerate(supports):
            if sup['t'] == 'col':
                dist = math.hypot(x - sup['x'], y - sup['y'])
            else:
                dist = cls.seg_dist(x, y, sup['x1'], sup['y1'], sup['x2'], sup['y2'])
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        return best_idx

    @classmethod
    def compute_tributary_reactions(cls, model: BuildingModel, target_story_idx: int, grid_res: float = 0.4) -> Dict[str, Any]:
        """
        Marches load path from top story down to target_story_idx.
        Returns accumulated reactions for columns and walls at target_story_idx.
        """
        density = 2.5e-5  # N/mm3 (standard concrete weight 25 kN/m3)
        applied: Dict[str, float] = {}
        unassigned = 0.0
        carried: List[Dict[str, Any]] = []
        final_supports: List[Dict[str, Any]] = []

        # Iterate top-down from story 0 to target_story_idx
        for s_idx in range(min(target_story_idx + 1, len(model.stories))):
            story = model.stories[s_idx]
            story_name = story.name
            st_height = story.height * 1000.0 if story.height < 100.0 else story.height  # mm

            # 1. Build supports for story
            supports: List[Dict[str, Any]] = []
            panel_map: Dict[str, int] = {}
            panel_len: Dict[str, float] = {}
            panel_h: Dict[str, float] = {}

            # Columns
            cols_on_story = [fr for fr in model.frames if fr.type == FrameType.COLUMN and fr.story.lower() == story_name.lower()]
            for c in cols_on_story:
                cx, cy = c.start_point.x * 1000.0, c.start_point.y * 1000.0
                supports.append({
                    't': 'col', 'n': c.id, 'sec': c.section, 'x': cx, 'y': cy,
                    'a': 250000.0, 'h': st_height, 'P': {}
                })

            # Walls
            walls_on_story = [w for w in model.walls if w.story.lower() == story_name.lower()]
            seen_walls: Dict[str, int] = {}
            for w in walls_on_story:
                if hasattr(w, 'polygon') and len(w.polygon) >= 2:
                    x1, y1 = w.polygon[0].x * 1000.0, w.polygon[0].y * 1000.0
                    x2, y2 = w.polygon[1].x * 1000.0, w.polygon[1].y * 1000.0
                else:
                    x1, y1 = w.start_point.x * 1000.0, w.start_point.y * 1000.0
                    x2, y2 = w.end_point.x * 1000.0, w.end_point.y * 1000.0

                w_len = math.hypot(x2 - x1, y2 - y1)
                if w_len < 1.0:
                    continue
                panel_len[w.id] = w_len
                panel_h[w.id] = st_height

                k = f"{round(x1/50)}|{round(y1/50)}|{round(x2/50)}|{round(y2/50)}"
                if k in seen_walls:
                    panel_map[w.id] = seen_walls[k]
                    continue
                seen_walls[k] = len(supports)
                panel_map[w.id] = len(supports)
                supports.append({
                    't': 'wall', 'n': w.id, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                    'x': (x1 + x2) / 2.0, 'y': (y1 + y2) / 2.0, 'th': w.thickness * 1000.0 if w.thickness < 10 else w.thickness,
                    'len': w_len, 'h': st_height, 'P': {}
                })

            if not supports:
                continue

            # 2. Self weight of vertical elements
            for sup in supports:
                if sup['t'] == 'col':
                    w_self = sup['a'] * sup['h'] * density
                else:
                    w_self = sup['th'] * sup['len'] * sup['h'] * density
                sup['P']['OW'] = sup['P'].get('OW', 0.0) + w_self
                applied['OW'] = applied.get('OW', 0.0) + w_self

            # 3. Floor area loads sampling
            story_slabs = [sl for sl in model.slabs if sl.story.lower() == story_name.lower()]
            real_slabs = [sl for sl in story_slabs if not sl.is_opening]

            if real_slabs:
                minx, maxx = float('inf'), float('-inf')
                miny, maxy = float('inf'), float('-inf')
                for sl in real_slabs:
                    for pt in sl.polygon:
                        px, py = pt.x * 1000.0, pt.y * 1000.0
                        if px < minx: minx = px
                        if px > maxx: maxx = px
                        if py < miny: miny = py
                        if py > maxy: maxy = py

                res_mm = grid_res * 1000.0
                cell_area = res_mm * res_mm
                x_curr = minx + res_mm / 2.0
                while x_curr < maxx:
                    y_curr = miny + res_mm / 2.0
                    while y_curr < maxy:
                        hit_slab = None
                        for sl in real_slabs:
                            poly_pts = [(pt.x * 1000.0, pt.y * 1000.0) for pt in sl.polygon]
                            if cls.in_polygon(x_curr, y_curr, poly_pts):
                                hit_slab = sl
                                break
                        if hit_slab:
                            sup_idx = cls.nearest_support(supports, x_curr, y_curr)
                            ow_val = (hit_slab.thickness * 1000.0 if hit_slab.thickness < 10 else hit_slab.thickness) * density * cell_area
                            applied['OW'] = applied.get('OW', 0.0) + ow_val
                            if sup_idx >= 0:
                                supports[sup_idx]['P']['OW'] = supports[sup_idx]['P'].get('OW', 0.0) + ow_val
                            else:
                                unassigned += ow_val

                        y_curr += res_mm
                    x_curr += res_mm

            # 4. Beam self weight
            story_beams = [fr for fr in model.frames if fr.type == FrameType.BEAM and fr.story.lower() == story_name.lower()]
            for bm in story_beams:
                bx1, by1 = bm.start_point.x * 1000.0, bm.start_point.y * 1000.0
                bx2, by2 = bm.end_point.x * 1000.0, bm.end_point.y * 1000.0
                b_len = math.hypot(bx2 - bx1, by2 - by1)
                b_weight = (300.0 * 600.0) * b_len * density
                applied['OW'] = applied.get('OW', 0.0) + b_weight
                sup_idx = cls.nearest_support(supports, (bx1 + bx2) / 2.0, (by1 + by2) / 2.0)
                if sup_idx >= 0:
                    supports[sup_idx]['P']['OW'] = supports[sup_idx]['P'].get('OW', 0.0) + b_weight
                else:
                    unassigned += b_weight

            # 5. March down carried reactions from story above
            for c_item in carried:
                sup_idx = cls.nearest_support(supports, c_item['x'], c_item['y'])
                if sup_idx >= 0:
                    for pat, val in c_item['P'].items():
                        supports[sup_idx]['P'][pat] = supports[sup_idx]['P'].get(pat, 0.0) + val
                else:
                    unassigned += c_item['P'].get('OW', 0.0)

            carried = [{'x': sup['x'], 'y': sup['y'], 'P': dict(sup['P'])} for sup in supports]
            final_supports = supports

        return {
            'supports': final_supports,
            'applied': applied,
            'unassigned': unassigned
        }
