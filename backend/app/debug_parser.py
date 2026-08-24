import os
import re
from typing import Dict, List, Optional
from app.models.intermediate import (
    BuildingModel, Story, Node, Frame, Slab, Wall, Material, FrameSection,
    ShellProperty, Point3D, Point2D, AreaLoad, PointLoad, LineLoad, LoadPattern,
    FrameType, UnitSystem
)

class RobustE2KParser:
    def __init__(self):
        self.model = BuildingModel()
        self.area_nodes: Dict[str, List[str]] = {}       # area_id -> [node_ids]
        self.area_types: Dict[str, str] = {}             # area_id -> SLAB / PANEL / WALL
        self.line_nodes: Dict[str, tuple] = {}            # frame_id -> (p1_id, p2_id)
        self.line_types: Dict[str, str] = {}             # frame_id -> BEAM / COLUMN

    def parse_string(self, content: str) -> BuildingModel:
        lines = content.splitlines()
        current_section = None

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            cleaned_header = stripped.lstrip("$").strip()

            if cleaned_header.startswith("STORIES"):
                current_section = "STORIES"
                continue
            elif cleaned_header.startswith("POINT COORDINATES"):
                current_section = "POINT COORDINATES"
                continue
            elif cleaned_header.startswith("LINE CONNECTIVITIES"):
                current_section = "LINE CONNECTIVITIES"
                continue
            elif cleaned_header.startswith("LINE ASSIGNS"):
                current_section = "LINE ASSIGNS"
                continue
            elif cleaned_header.startswith("AREA CONNECTIVITIES"):
                current_section = "AREA CONNECTIVITIES"
                continue
            elif cleaned_header.startswith("AREA ASSIGNS"):
                current_section = "AREA ASSIGNS"
                continue
            elif cleaned_header.startswith("FRAME SECTIONS") or cleaned_header.startswith("CONCRETE SECTIONS"):
                current_section = "FRAME SECTIONS"
                continue
            elif cleaned_header.startswith("SLAB PROPERTIES") or cleaned_header.startswith("WALL PROPERTIES") or cleaned_header.startswith("SHELL PROPERTIES"):
                current_section = "SHELL PROPERTIES"
                continue
            elif cleaned_header.startswith("MATERIAL PROPERTIES"):
                current_section = "MATERIAL PROPERTIES"
                continue

            if stripped.startswith("$"):
                # Also check inline $ comments like "$ STORY"
                if "STORIES" in stripped: current_section = "STORIES"
                elif "POINT COORDINATES" in stripped: current_section = "POINT COORDINATES"
                elif "LINE CONNECTIVITIES" in stripped: current_section = "LINE CONNECTIVITIES"
                elif "LINE ASSIGNS" in stripped: current_section = "LINE ASSIGNS"
                elif "AREA CONNECTIVITIES" in stripped: current_section = "AREA CONNECTIVITIES"
                elif "AREA ASSIGNS" in stripped: current_section = "AREA ASSIGNS"
                continue

            if current_section == "STORIES":
                self._parse_story(stripped)
            elif current_section == "POINT COORDINATES":
                self._parse_point_coordinate(stripped)
            elif current_section == "LINE CONNECTIVITIES":
                self._parse_line_connectivity(stripped)
            elif current_section == "LINE ASSIGNS":
                self._parse_line_assign(stripped)
            elif current_section == "AREA CONNECTIVITIES":
                self._parse_area_connectivity(stripped)
            elif current_section == "AREA ASSIGNS":
                self._parse_area_assign(stripped)

        self._post_process()
        return self.model

    def _parse_story(self, line: str):
        name_match = re.search(r'STORY\s+"([^"]+)"', line)
        height_match = re.search(r'HEIGHT\s+([0-9.]+)', line)
        elev_match = re.search(r'ELEV\s+([0-9.]+)', line)

        if name_match:
            story_name = name_match.group(1)
            elevation = float(elev_match.group(1)) if elev_match else 0.0
            height = float(height_match.group(1)) if height_match else 3.5

            self.model.stories.append(Story(
                id=f"story_{story_name.lower().replace(' ', '_')}",
                name=story_name,
                elevation=elevation,
                height=height
            ))

    def _parse_point_coordinate(self, line: str):
        name_match = re.search(r'POINT\s+"([^"]+)"', line)
        if not name_match:
            return
        node_id = name_match.group(1)

        x_match = re.search(r'X\s+([-0-9.]+)', line)
        y_match = re.search(r'Y\s+([-0-9.]+)', line)
        z_match = re.search(r'Z\s+([-0-9.]+)', line)
        story_match = re.search(r'STORY\s+"([^"]+)"', line)

        if x_match and y_match:
            x = float(x_match.group(1))
            y = float(y_match.group(1))
            z = float(z_match.group(1)) if z_match else 0.0
        else:
            tokens = line.split()
            nums = [t for t in tokens[2:] if re.match(r'^-?[0-9.]+$', t)]
            if len(nums) >= 2:
                x = float(nums[0])
                y = float(nums[1])
                z = float(nums[2]) if len(nums) >= 3 else 0.0
            else:
                return

        self.model.nodes[node_id] = Node(
            id=node_id,
            x=x, y=y, z=z,
            story=story_match.group(1) if story_match else None
        )

    def _parse_line_connectivity(self, line: str):
        quotes = re.findall(r'"([^"]+)"', line)
        if len(quotes) >= 3:
            frame_id = quotes[0]
            p1_id = quotes[1]
            p2_id = quotes[2]
            self.line_nodes[frame_id] = (p1_id, p2_id)
            if "COLUMN" in line:
                self.line_types[frame_id] = "Column"
            else:
                self.line_types[frame_id] = "Beam"

    def _parse_line_assign(self, line: str):
        quotes = re.findall(r'"([^"]+)"', line)
        if not quotes:
            return
        frame_id = quotes[0]
        story_name = quotes[1] if len(quotes) >= 2 else "Level 1"
        sec_match = re.search(r'SECTION\s+"([^"]+)"', line)
        sec_name = sec_match.group(1) if sec_match else "DEFAULT"

        (p1_id, p2_id) = self.line_nodes.get(frame_id, ("N1", "N2"))
        p1_node = self.model.nodes.get(p1_id, Node(id=p1_id, x=0, y=0, z=0))
        p2_node = self.model.nodes.get(p2_id, Node(id=p2_id, x=0, y=0, z=0))

        f_type_str = self.line_types.get(frame_id, "Column" if "C" in frame_id or "COL" in sec_name.upper() else "Beam")
        f_type = FrameType.COLUMN if f_type_str.lower() == "column" else FrameType.BEAM

        self.model.frames.append(Frame(
            id=f"{frame_id}_{story_name}",
            type=f_type,
            start_node=p1_id,
            end_node=p2_id,
            start_point=Point3D(x=p1_node.x, y=p1_node.y, z=p1_node.z),
            end_point=Point3D(x=p2_node.x, y=p2_node.y, z=p2_node.z),
            section=sec_name,
            story=story_name
        ))

    def _parse_area_connectivity(self, line: str):
        quotes = re.findall(r'"([^"]+)"', line)
        if len(quotes) >= 2:
            area_id = quotes[0]
            pt_names = quotes[1:]
            self.area_nodes[area_id] = pt_names
            if "PANEL" in line or area_id.startswith("W"):
                self.area_types[area_id] = "Wall"
            else:
                self.area_types[area_id] = "Slab"

    def _parse_area_assign(self, line: str):
        quotes = re.findall(r'"([^"]+)"', line)
        if not quotes:
            return
        area_id = quotes[0]
        story_name = quotes[1] if len(quotes) >= 2 else "Level 1"
        sec_match = re.search(r'(?:SECTION|PROPERTY)\s+"([^"]+)"', line)
        prop_name = sec_match.group(1) if sec_match else "SLAB"
        is_opening = prop_name.upper() in ["OPENING", "VOID", "OPEN"]

        pt_ids = self.area_nodes.get(area_id, [])
        polygon = [Point2D(x=self.model.nodes[pid].x, y=self.model.nodes[pid].y) for pid in pt_ids if pid in self.model.nodes]

        if area_id.startswith("W") or self.area_types.get(area_id) == "Wall" or "WALL" in prop_name.upper() or "CW" in prop_name.upper() or "SW" in prop_name.upper():
            self.model.walls.append(Wall(
                id=f"{area_id}_{story_name}",
                story=story_name,
                polygon=polygon,
                thickness=0.3,
                property_name=prop_name
            ))
        else:
            self.model.slabs.append(Slab(
                id=f"{area_id}_{story_name}",
                story=story_name,
                polygon=polygon,
                thickness=0.25,
                property_name=prop_name,
                is_opening=is_opening
            ))

    def _post_process(self):
        # Calculate cumulative story elevations if missing
        if self.model.stories and all(st.elevation == 0.0 for st in self.model.stories):
            cum = 0.0
            for st in reversed(self.model.stories):
                cum += st.height
                st.elevation = round(cum, 2)


filepath = os.path.join(os.path.dirname(__file__), "..", "..", "sample_models", "P-796-ULT-V22.3-UPDATED-01-06-2026.$et")
with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

parser = RobustE2KParser()
model = parser.parse_string(content)

print("\n=== Robust Parser Test Result on Real Model ===")
print(f"Stories Count: {len(model.stories)}")
for st in model.stories:
    st_slabs = [s for s in model.slabs if s.story == st.name]
    st_walls = [w for w in model.walls if w.story == st.name]
    st_frames = [f for f in model.frames if f.story == st.name]
    valid_slabs = [s for s in st_slabs if len(s.polygon) > 0]
    print(f"  Story: {st.name:8s} Elev={st.elevation:5.1f}m | Slabs={len(st_slabs)} (valid_geom={len(valid_slabs)}) | Walls={len(st_walls)} | Frames={len(st_frames)}")
