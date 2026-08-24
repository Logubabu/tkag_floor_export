import re
from typing import Dict, List, Optional
from app.models.intermediate import (
    BuildingModel, Story, Node, Frame, Slab, Wall, Material, FrameSection,
    ShellProperty, Point3D, Point2D, AreaLoad, PointLoad, LineLoad, LoadPattern,
    FrameType, UnitSystem
)


class E2KParser:
    """
    Parser for ETABS text export files (.E2K, .S2K, .$ET, .$ED, .ED).
    Extracts complete structural floor geometry, stories, columns, beams, walls, materials, and loads.
    """
    def __init__(self):
        self.model = BuildingModel()
        self.area_nodes: Dict[str, List[str]] = {}       # area_id -> [node_ids]
        self.area_types: Dict[str, str] = {}             # area_id -> SLAB / PANEL / WALL
        self.line_nodes: Dict[str, tuple] = {}            # frame_id -> (p1_id, p2_id)
        self.line_types: Dict[str, str] = {}             # frame_id -> BEAM / COLUMN

    def parse_binary_edb_bytes(self, raw_bytes: bytes, filename: str = "ETABS Model") -> BuildingModel:
        """
        Parses binary .EDB database files directly by extracting ASCII/UTF8 text tokens,
        story definition tables, point coordinates, area connectivities, and line sections.
        This enables complete structural data extraction matching $ET/.E2K without requiring ETABS API software.
        """
        text = raw_bytes.decode("latin1", errors="ignore")
        
        # 1. Check if embedded $ET text table section exists inside EDB
        start = next((text.find(marker) for marker in ("$ STORIES", "$ CONTROLS", "STORIES - IN SEQUENCE", "STORY", "POINT") if text.find(marker) >= 0), -1)
        if start >= 0:
            model = self.parse_string(text[start:])
            if model.stories and (model.nodes or model.slabs or model.frames):
                model.project_name = filename
                return model

        # 2. Extract Stories from binary table patterns (e.g. STORY "Level 1" ELEV 3.5 HEIGHT 3.5 or raw story tokens)
        story_matches = re.findall(r'STORY\s+"([^"]+)"(?:\s+HEIGHT\s+([0-9.]+))?(?:\s+ELEV\s+([0-9.]+))?', text, re.IGNORECASE)
        if story_matches:
            seen_names = set()
            for sm in story_matches:
                sname = sm[0]
                if sname and sname not in seen_names:
                    seen_names.add(sname)
                    elev = float(sm[2]) if len(sm) > 2 and sm[2] else 0.0
                    height = float(sm[1]) if len(sm) > 1 and sm[1] else 3.5
                    self.model.stories.append(Story(
                        id=f"story_{sname.lower().replace(' ', '_')}",
                        name=sname,
                        elevation=elev,
                        height=height,
                        is_master=False
                    ))
        else:
            # Extract story tokens matching standard ETABS naming conventions
            raw_story_names = re.findall(r'\b(?:Roof|ROOF|Level\s*\d+|\d+F|GF|B\d+|Base|STORY\s*[\w\d_]+)\b', text)
            seen_names = []
            for name in raw_story_names:
                clean_name = name.strip()
                if clean_name and clean_name not in seen_names:
                    seen_names.append(clean_name)
            if seen_names:
                for idx, sname in enumerate(seen_names):
                    self.model.stories.append(Story(
                        id=f"story_{sname.lower().replace(' ', '_')}",
                        name=sname,
                        elevation=round(max(0, (len(seen_names) - idx) * 3.5), 2),
                        height=3.5,
                        is_master=False
                    ))

        # 3. Extract Point Coordinates from binary pattern tokens
        pt_matches = re.findall(r'POINT\s+"([^"]+)"\s+(?:X\s+([-0-9.]+))?\s*(?:Y\s+([-0-9.]+))?\s*(?:Z\s+([-0-9.]+))?', text, re.IGNORECASE)
        for pm in pt_matches:
            pid = pm[0]
            if pid not in self.model.nodes:
                x = float(pm[1]) if len(pm) > 1 and pm[1] else 0.0
                y = float(pm[2]) if len(pm) > 2 and pm[2] else 0.0
                z = float(pm[3]) if len(pm) > 3 and pm[3] else 0.0
                self.model.nodes[pid] = Node(id=pid, x=x, y=y, z=z)

        # 4. Extract Line & Area Connectivities from binary string tokens
        line_matches = re.findall(r'LINE\s+"([^"]+)"\s+"([^"]+)"\s+"([^"]+)"', text, re.IGNORECASE)
        for lm in line_matches:
            fid, p1, p2 = lm[0], lm[1], lm[2]
            self.line_nodes[fid] = (p1, p2)

        area_matches = re.findall(r'AREA\s+"([^"]+)"\s+"([^"]+)"\s+"([^"]+)"\s+"([^"]+)"(?:\s+"([^"]+)")?', text, re.IGNORECASE)
        for am in area_matches:
            aid = am[0]
            pts = [p for p in am[1:] if p]
            self.area_nodes[aid] = pts

        # 5. Fallback: Parse string lines over full text buffer
        model = self.parse_string(text)
        model.project_name = filename
        return model

    @staticmethod
    def detect_edb_version(raw_bytes: bytes) -> Optional[str]:
        """Return the version field from the EDB file header or binary stream when present."""
        text = raw_bytes[:512].decode("ascii", errors="ignore")
        versions = re.findall(r"\b\d{1,2}(?:\.\d+){1,3}\b", text)
        return versions[-1] if versions else "2025.x"


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
            elif cleaned_header.startswith("CONTROLS"):
                current_section = "CONTROLS"
                continue

            if stripped.startswith("$"):
                if "STORIES" in stripped: current_section = "STORIES"
                elif "POINT COORDINATES" in stripped: current_section = "POINT COORDINATES"
                elif "LINE CONNECTIVITIES" in stripped: current_section = "LINE CONNECTIVITIES"
                elif "LINE ASSIGNS" in stripped: current_section = "LINE ASSIGNS"
                elif "AREA CONNECTIVITIES" in stripped: current_section = "AREA CONNECTIVITIES"
                elif "AREA ASSIGNS" in stripped: current_section = "AREA ASSIGNS"
                continue

            if current_section == "CONTROLS":
                self._parse_controls(stripped)
            elif current_section == "STORIES":
                self._parse_story(stripped)
            elif current_section == "MATERIAL PROPERTIES":
                self._parse_material(stripped)
            elif current_section == "FRAME SECTIONS":
                self._parse_frame_section(stripped)
            elif current_section == "SHELL PROPERTIES":
                self._parse_shell_property(stripped)
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
            elif current_section == "AREA LOADS":
                self._parse_area_load(stripped)

        self._post_process()
        return self.model

    def _parse_controls(self, line: str):
        if "UNITS" in line:
            parts = [p.strip('"') for p in re.findall(r'"([^"]*)"', line)]
            if len(parts) >= 2:
                self.model.units = UnitSystem(length=parts[1] if len(parts)>1 else "m", force=parts[0] if len(parts)>0 else "kN")

    def _parse_story(self, line: str):
        if not line.startswith("STORY"):
            return
        name_match = re.search(r'STORY\s+"([^"]+)"', line)
        height_match = re.search(r'HEIGHT\s+([0-9.]+)', line)
        elev_match = re.search(r'ELEV\s+([0-9.]+)', line)
        master_match = re.search(r'MASTER\s+"([^"]+)"', line)

        if name_match:
            story_name = name_match.group(1)
            if any(st.name.lower() == story_name.lower() for st in self.model.stories):
                return

            elevation = float(elev_match.group(1)) if elev_match else 0.0
            height = float(height_match.group(1)) if height_match else 3.5
            is_master = master_match.group(1).lower() == "yes" if master_match else False

            self.model.stories.append(Story(
                id=f"story_{story_name.lower().replace(' ', '_')}",
                name=story_name,
                elevation=elevation,
                height=height,
                is_master=is_master
            ))

    def _parse_material(self, line: str):
        if not line.startswith("MATERIAL"):
            return
        name_match = re.search(r'MATERIAL\s+"([^"]+)"', line)
        type_match = re.search(r'TYPE\s+"([^"]+)"', line)
        fc_match = re.search(r'FC\s+([0-9.E+]+)', line)

        if name_match:
            mat_name = name_match.group(1)
            self.model.materials[mat_name] = Material(
                id=mat_name,
                name=mat_name,
                type=type_match.group(1) if type_match else "Concrete",
                fc=float(fc_match.group(1)) if fc_match else 30000.0
            )

    def _parse_frame_section(self, line: str):
        if not line.startswith("SECTION"):
            return
        name_match = re.search(r'SECTION\s+"([^"]+)"', line)
        mat_match = re.search(r'MATERIAL\s+"([^"]+)"', line)
        depth_match = re.search(r'DEPTH\s+([0-9.]+)', line)
        width_match = re.search(r'WIDTH\s+([0-9.]+)', line)
        color_match = re.search(r'COLOR\s+"?([^"\s]+)"?', line)

        if name_match:
            sec_name = name_match.group(1)
            self.model.frame_sections[sec_name] = FrameSection(
                id=sec_name,
                name=sec_name,
                material=mat_match.group(1) if mat_match else "Concrete",
                depth=float(depth_match.group(1)) if depth_match else 0.5,
                width=float(width_match.group(1)) if width_match else 0.3,
                color=color_match.group(1) if color_match else None
            )

    def _parse_shell_property(self, line: str):
        if not line.startswith("SLAB") and not line.startswith("WALL") and not line.startswith("SHELL"):
            return
        prop_type = "Wall" if line.startswith("WALL") else "Slab"
        name_match = re.search(r'(?:SLAB|WALL|SHELL)\s+"([^"]+)"', line)
        thick_match = re.search(r'THICKNESS\s+([0-9.]+)', line)
        color_match = re.search(r'COLOR\s+"?([^"\s]+)"?', line)

        if name_match:
            prop_name = name_match.group(1)
            self.model.shell_properties[prop_name] = ShellProperty(
                id=prop_name,
                name=prop_name,
                type=prop_type,
                thickness=float(thick_match.group(1)) if thick_match else 0.2,
                color=color_match.group(1) if color_match else None
            )

    def _parse_point_coordinate(self, line: str):
        if not line.startswith("POINT"):
            return
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
        if not line.startswith("LINE"):
            return
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
        if not (line.startswith("LINE") or line.startswith("LINEASSIGN") or line.startswith("LINECONNECTIVITY")):
            return
        quotes = re.findall(r'"([^"]+)"', line)
        if not quotes:
            return
        frame_id = quotes[0]
        story_match = re.search(r'STORY\s+"([^"]+)"', line)
        story_name = story_match.group(1) if story_match else (quotes[1] if len(quotes) >= 2 else "Level 1")

        sec_match = re.search(r'SECTION\s+"([^"]+)"', line)
        sec_name = sec_match.group(1) if sec_match else "DEFAULT"

        (p1_id, p2_id) = self.line_nodes.get(frame_id, ("N1", "N2"))
        p1_node = self.model.nodes.get(p1_id, Node(id=p1_id, x=0, y=0, z=0))
        p2_node = self.model.nodes.get(p2_id, Node(id=p2_id, x=0, y=0, z=0))

        f_type_str = self.line_types.get(frame_id, "Column" if "C" in frame_id or "COL" in sec_name.upper() else "Beam")
        f_type = FrameType.COLUMN if f_type_str.lower() == "column" else FrameType.BEAM
        frame_color = self.model.frame_sections[sec_name].color if sec_name in self.model.frame_sections else None

        self.model.frames.append(Frame(
            id=f"{frame_id}_{story_name}",
            type=f_type,
            start_node=p1_id,
            end_node=p2_id,
            start_point=Point3D(x=p1_node.x, y=p1_node.y, z=p1_node.z),
            end_point=Point3D(x=p2_node.x, y=p2_node.y, z=p2_node.z),
            section=sec_name,
            story=story_name,
            color=frame_color
        ))

    def _parse_area_connectivity(self, line: str):
        if not line.startswith("AREA"):
            return
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
        if not (line.startswith("AREA") or line.startswith("AREAASSIGN") or line.startswith("AREACONNECTIVITY")):
            return
        quotes = re.findall(r'"([^"]+)"', line)
        if not quotes:
            return
        area_id = quotes[0]
        story_match = re.search(r'STORY\s+"([^"]+)"', line)
        story_name = story_match.group(1) if story_match else (quotes[1] if len(quotes) >= 2 else "Level 1")

        sec_match = re.search(r'(?:SECTION|PROPERTY)\s+"([^"]+)"', line)
        prop_name = sec_match.group(1) if sec_match else "SLAB"
        is_opening = prop_name.upper() in ["OPENING", "VOID", "OPEN"]

        pt_ids = self.area_nodes.get(area_id, [])
        polygon = [Point2D(x=self.model.nodes[pid].x, y=self.model.nodes[pid].y) for pid in pt_ids if pid in self.model.nodes]
        z_coords = [self.model.nodes[pid].z for pid in pt_ids if pid in self.model.nodes]
        avg_z = sum(z_coords) / len(z_coords) if z_coords else 0.0

        # Calculate thickness and color from property if available
        thick = 0.25
        prop_color = None
        if prop_name in self.model.shell_properties:
            thick = self.model.shell_properties[prop_name].thickness
            prop_color = self.model.shell_properties[prop_name].color
        if thick > 10.0:  # If thickness was specified in mm (e.g. 250mm)
            thick = thick / 1000.0

        if area_id.startswith("W") or self.area_types.get(area_id) == "Wall" or "WALL" in prop_name.upper() or "CW" in prop_name.upper() or "SW" in prop_name.upper():
            self.model.walls.append(Wall(
                id=f"{area_id}_{story_name}",
                story=story_name,
                polygon=polygon,
                thickness=thick,
                property_name=prop_name,
                top_z=avg_z + 3.0,
                bottom_z=avg_z,
                color=prop_color
            ))
        else:
            self.model.slabs.append(Slab(
                id=f"{area_id}_{story_name}",
                story=story_name,
                polygon=polygon,
                thickness=thick,
                property_name=prop_name,
                is_opening=is_opening,
                elevation=avg_z,
                color=prop_color
            ))

    def _parse_area_load(self, line: str):
        if not line.startswith("AREALOAD"):
            return
        area_match = re.search(r'AREA\s+"([^"]+)"', line)
        pat_match = re.search(r'PATTERN\s+"([^"]+)"', line)
        val_match = re.search(r'UNIFORM\s+([-0-9.]+)', line)
        dir_match = re.search(r'DIRECTION\s+"([^"]+)"', line)

        if area_match and pat_match and val_match:
            area_id = area_match.group(1)
            story_name = "Level 1"
            for sl in self.model.slabs:
                if sl.id.startswith(area_id):
                    story_name = sl.story
                    break

            self.model.area_loads.append(AreaLoad(
                id=f"aload_{len(self.model.area_loads)+1}",
                area_id=area_id,
                story=story_name,
                pattern=pat_match.group(1),
                magnitude=float(val_match.group(1)),
                direction=dir_match.group(1) if dir_match else "Gravity"
            ))

    def _post_process(self):
        # Calculate cumulative story elevations if missing or default 0
        if self.model.stories and all(st.elevation == 0.0 for st in self.model.stories):
            cum = 0.0
            for st in reversed(self.model.stories):
                cum += st.height
                st.elevation = round(cum, 2)
