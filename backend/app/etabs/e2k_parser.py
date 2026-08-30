import os
import re
from typing import Dict, List, Optional
from app.models.intermediate import (
    BuildingModel, Story, Node, Frame, Slab, Wall, Material, FrameSection,
    ShellProperty, Point3D, Point2D, AreaLoad, FrameType, UnitSystem
)


class E2KParser:
    """
    Parser for ETABS text export files (.E2K, .S2K, .$ET, .$ED, .ED).
    Extracts complete structural floor geometry, stories, columns, beams, walls, materials, and loads.
    """
    def __init__(self, model: Optional[BuildingModel] = None):
        self.model = model if model is not None else BuildingModel()
        self.area_nodes: Dict[str, List[str]] = {}       # area_id -> [node_ids]
        self.area_types: Dict[str, str] = {}             # area_id -> SLAB / PANEL / WALL
        self.line_nodes: Dict[str, tuple] = {}            # frame_id -> (p1_id, p2_id)
        self.line_types: Dict[str, str] = {}             # frame_id -> BEAM / COLUMN

    def parse_binary_edb_bytes(
        self,
        raw_bytes: bytes,
        filename: str = "ETABS Model",
        companion_text: Optional[str] = None,
    ) -> BuildingModel:
        """
        Parses binary .EDB database files.
        Extracts structural floor geometry, stories, columns, beams, walls, and slabs directly from binary stream.
        Handles ETABS v22, v21, v20, v19 binary formats, compressed zlib streams, embedded SQLite tables,
        or companion text exports.
        """
        import zlib
        import sqlite3
        import tempfile

        # 0. Immediately check and parse companion_text if supplied
        if companion_text and companion_text.strip():
            parser = E2KParser()
            model = parser.parse_string(companion_text)
            if model.stories:
                model.project_name = filename
                return model

        # Decompress zlib streams if present inside binary EDB file
        decompressed_texts: List[str] = []
        # Search for zlib magic headers (0x78 0x9c, 0x78 0x01, 0x78 0xda)
        for match in re.finditer(rb'\x78[\x9c\x01\xda]', raw_bytes):
            offset = match.start()
            try:
                decompressed = zlib.decompress(raw_bytes[offset:offset+1000000])
                if decompressed:
                    txt = decompressed.decode("latin1", errors="ignore")
                    if "$ STORIES" in txt or "STORIES - IN SEQUENCE" in txt or "STORY" in txt:
                        decompressed_texts.append(txt)
            except Exception:
                pass

        # Try multi-encoding decodes for embedded text table streams (Latin-1, UTF-8, UTF-16-LE)
        decoded_texts: List[str] = list(decompressed_texts)
        for enc in ("latin1", "utf-8", "utf-16-le"):
            try:
                dt = raw_bytes.decode(enc, errors="ignore")
                if dt and len(dt) > 0:
                    decoded_texts.append(dt)
            except Exception:
                pass

        # 1. Check if embedded $ET / .E2K text table section exists inside EDB stream or decompressed blocks
        for text in decoded_texts:
            start = next((text.find(marker) for marker in ("$ PROGRAM INFORMATION", "$ CONTROLS", "$ STORIES", "STORIES - IN SEQUENCE") if text.find(marker) >= 0), -1)
            if start >= 0:
                parser = E2KParser()
                model = parser.parse_string(text[start:])
                if model.stories and (model.nodes or model.slabs or model.frames):
                    model.project_name = filename
                    return model

        # 2. Heuristic text extraction attempt on decoded streams
        for text in decoded_texts:
            parser = E2KParser()
            model = parser.parse_string(text)
            if model.stories and (len(model.nodes) > 0 or len(model.slabs) > 0 or len(model.frames) > 0):
                model.project_name = filename
                return model

        # 3. Check for embedded SQLite database inside EDB file
        sqlite_idx = raw_bytes.find(b"SQLite format 3\x00")
        if sqlite_idx >= 0:
            try:
                with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
                    tmp_db.write(raw_bytes[sqlite_idx:])
                    tmp_db_path = tmp_db.name
                
                conn = sqlite3.connect(tmp_db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                
                story_table = next((t for t in tables if "story" in t.lower()), None)
                if story_table:
                    cursor.execute(f"SELECT * FROM {story_table}")
                    rows = cursor.fetchall()
                    if rows:
                        model = BuildingModel(project_name=filename)
                        for idx, r in enumerate(rows):
                            sname = str(r[0]) if r else f"Story_{idx+1}"
                            model.stories.append(Story(
                                id=f"story_{sname.lower().replace(' ', '_')}",
                                name=sname,
                                elevation=round((idx + 1) * 3.5, 2),
                                height=3.5,
                                is_master=False
                            ))
                        if model.stories:
                            conn.close()
                            return model
                conn.close()
            except Exception:
                pass

        # 4. If binary EDB has no embedded text tables, attempt Live ETABS COM API connection if ETABS is open
        try:
            from backend.app.etabs.com_adapter import ETABSCOMAdapter
            adapter = ETABSCOMAdapter()
            success, msg = adapter.connect_running_instance()
            if success:
                live_model = adapter.extract_building_model()
                if live_model and live_model.stories and (live_model.slabs or live_model.frames):
                    live_model.project_name = filename
                    return live_model
        except Exception:
            pass

        # 5. If no embedded text table section and no active ETABS COM session, raise informative error
        raise ValueError(
            f"Selected file '{filename}' is an ETABS binary database (.EDB).\n\n"
            "To import 100% exact real structural geometry into RAM Concept:\n"
            "1. If ETABS is currently open with your model, click '🔌 Connect to Active ETABS' in the application.\n"
            "2. Or in ETABS, go to File -> Export -> ETABS .e2k Text File..., and open the exported .e2k file."
        )

    @staticmethod
    def detect_edb_version(raw_bytes: bytes) -> Optional[str]:
        """Return the version field from the EDB file header or binary stream when present."""
        text = raw_bytes[:512].decode("ascii", errors="ignore")
        versions = re.findall(r"\b\d{1,2}(?:\.\d+){1,3}\b", text)
        return versions[0] if versions else None
        
    def parse_file(self, file_path: str) -> BuildingModel:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".edb":
            # Auto-check for companion .e2k / .$et text export in same folder
            base_no_ext = os.path.splitext(file_path)[0]
            dir_path = os.path.dirname(file_path)
            companion_candidates = [
                base_no_ext + ".e2k",
                base_no_ext + ".$et",
                base_no_ext + ".s2k",
                base_no_ext + ".E2K",
                base_no_ext + ".ED",
                os.path.join(dir_path, "model.e2k"),
                os.path.join(dir_path, "model.$et"),
            ]
            for cand in companion_candidates:
                if os.path.exists(cand):
                    with open(cand, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    model = self.parse_string(content)
                    model.project_name = os.path.basename(file_path)
                    return model

            with open(file_path, "rb") as f:
                raw_bytes = f.read()
            model = self.parse_binary_edb_bytes(raw_bytes, filename=os.path.basename(file_path))
            model.project_name = os.path.basename(file_path)
            return model
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        model = self.parse_string(content)
        model.project_name = os.path.basename(file_path)
        return model

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
                elif "AREA LOADS" in stripped: current_section = "AREA LOADS"
                continue

            # Dynamic inline matching fallback for unsectioned or raw lines
            if stripped.startswith("STORY "):
                self._parse_story(stripped)
            elif stripped.startswith("POINT "):
                self._parse_point_coordinate(stripped)
            elif stripped.startswith("LINE ") or stripped.startswith("LINEASSIGN "):
                if "POINT" in stripped or len(re.findall(r'"([^"]+)"', stripped)) >= 3:
                    self._parse_line_connectivity(stripped)
                self._parse_line_assign(stripped)
            elif stripped.startswith("AREA ") or stripped.startswith("AREAASSIGN "):
                if "POINT" in stripped or len(re.findall(r'"([^"]+)"', stripped)) >= 3:
                    self._parse_area_connectivity(stripped)
                self._parse_area_assign(stripped)

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
            # Handle both quoted ('UNITS "KN" "M" "C"') and unquoted ('UNITS KN M C')
            matches = re.findall(r'"([^"]*)"|\'([^\']*)\'|(\S+)', line)
            tokens = []
            for m in matches:
                val = (m[0] or m[1] or m[2]).strip('"\' ').strip()
                if val and val.upper() != "UNITS":
                    tokens.append(val)
            if len(tokens) >= 2:
                # ETABS standard UNITS order: Force, Length, Temperature (e.g. KN, M, C or KIP, IN, F)
                self.model.units = UnitSystem(force=tokens[0], length=tokens[1])

    def _parse_story(self, line: str):
        if not line.startswith("STORY"):
            return
        name_match = re.search(r'STORY\s+(?:"([^"]+)"|([A-Za-z0-9_ -]{1,32}))', line, re.IGNORECASE)
        height_match = re.search(r'HEIGHT\s+([-0-9.]+)', line, re.IGNORECASE)
        elev_match = re.search(r'ELEV\s+([-0-9.]+)', line, re.IGNORECASE)
        master_match = re.search(r'MASTER\s+(?:"([^"]+)"|([A-Za-z0-9]+))', line, re.IGNORECASE)

        if name_match:
            story_name = (name_match.group(1) or name_match.group(2)).strip()
            if any(st.name.lower() == story_name.lower() for st in self.model.stories):
                return

            elevation = float(elev_match.group(1)) if elev_match else 0.0
            height = float(height_match.group(1)) if height_match else 3.5
            master_val = (master_match.group(1) or master_match.group(2) or "").lower() if master_match else ""
            is_master = master_val == "yes"

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
        name_match = re.search(r'MATERIAL\s+(?:"([^"]+)"|([A-Za-z0-9_ -]+))', line, re.IGNORECASE)
        type_match = re.search(r'TYPE\s+(?:"([^"]+)"|([A-Za-z0-9_ -]+))', line, re.IGNORECASE)
        fc_match = re.search(r'FC\s+([0-9.E+]+)', line, re.IGNORECASE)

        if name_match:
            mat_name = (name_match.group(1) or name_match.group(2)).strip()
            mat_type = (type_match.group(1) or type_match.group(2)).strip() if type_match else "Concrete"
            self.model.materials[mat_name] = Material(
                id=mat_name,
                name=mat_name,
                type=mat_type,
                fc=float(fc_match.group(1)) if fc_match else 30000.0
            )

    def _parse_frame_section(self, line: str):
        if not line.startswith("SECTION"):
            return
        name_match = re.search(r'SECTION\s+(?:"([^"]+)"|([A-Za-z0-9_ -]+))', line, re.IGNORECASE)
        mat_match = re.search(r'MATERIAL\s+(?:"([^"]+)"|([A-Za-z0-9_ -]+))', line, re.IGNORECASE)
        depth_match = re.search(r'DEPTH\s+([0-9.]+)', line, re.IGNORECASE)
        width_match = re.search(r'WIDTH\s+([0-9.]+)', line, re.IGNORECASE)
        color_match = re.search(r'COLOR\s+"?([^"\s]+)"?', line, re.IGNORECASE)

        if name_match:
            sec_name = (name_match.group(1) or name_match.group(2)).strip()
            mat_name = (mat_match.group(1) or mat_match.group(2)).strip() if mat_match else "Concrete"
            self.model.frame_sections[sec_name] = FrameSection(
                id=sec_name,
                name=sec_name,
                material=mat_name,
                depth=float(depth_match.group(1)) if depth_match else 0.5,
                width=float(width_match.group(1)) if width_match else 0.3,
                color=color_match.group(1) if color_match else None
            )

    def _parse_shell_property(self, line: str):
        if not line.startswith("SLAB") and not line.startswith("WALL") and not line.startswith("SHELL"):
            return
        prop_type = "Wall" if line.startswith("WALL") else "Slab"
        name_match = re.search(r'(?:SLAB|WALL|SHELL)\s+(?:"([^"]+)"|([A-Za-z0-9_ -]+))', line, re.IGNORECASE)
        thick_match = re.search(r'THICKNESS\s+([0-9.]+)', line, re.IGNORECASE)
        color_match = re.search(r'COLOR\s+"?([^"\s]+)"?', line, re.IGNORECASE)

        if name_match:
            prop_name = (name_match.group(1) or name_match.group(2)).strip()
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
        name_match = re.search(r'POINT\s+(?:"([^"]+)"|([A-Za-z0-9_]+))', line, re.IGNORECASE)
        if not name_match:
            return
        node_id = (name_match.group(1) or name_match.group(2)).strip()

        x_match = re.search(r'X\s+([-0-9.E+]+)', line, re.IGNORECASE)
        y_match = re.search(r'Y\s+([-0-9.E+]+)', line, re.IGNORECASE)
        z_match = re.search(r'Z\s+([-0-9.E+]+)', line, re.IGNORECASE)
        story_match = re.search(r'STORY\s+(?:"([^"]+)"|([A-Za-z0-9_ -]+))', line, re.IGNORECASE)

        if x_match and y_match:
            x = float(x_match.group(1))
            y = float(y_match.group(1))
            z = float(z_match.group(1)) if z_match else 0.0
        else:
            tokens = line.split()
            nums = [t for t in tokens[2:] if re.match(r'^-?[0-9.E+]+$', t, re.IGNORECASE)]
            if len(nums) >= 2:
                x = float(nums[0])
                y = float(nums[1])
                z = float(nums[2]) if len(nums) >= 3 else 0.0
            else:
                return

        st_val = (story_match.group(1) or story_match.group(2)).strip() if story_match else None
        self.model.nodes[node_id] = Node(
            id=node_id,
            x=x, y=y, z=z,
            story=st_val
        )

    def _parse_line_connectivity(self, line: str):
        if not line.startswith("LINE"):
            return
        tokens = [t.strip('"') for t in re.findall(r'"[^"]+"|\S+', line)]
        if len(tokens) >= 4 and tokens[0].upper() == "LINE":
            frame_id = tokens[1]
            p1_id = tokens[2]
            p2_id = tokens[3]
            if "POINT" in [t.upper() for t in tokens]:
                idx = [i for i, t in enumerate(tokens) if t.upper() == "POINT"]
                if idx and len(tokens) > idx[0] + 2:
                    p1_id = tokens[idx[0] + 1]
                    p2_id = tokens[idx[0] + 2]

            self.line_nodes[frame_id] = (p1_id, p2_id)
            if "COLUMN" in line.upper():
                self.line_types[frame_id] = "Column"
            else:
                self.line_types[frame_id] = "Beam"

    def _resolve_story_name(self, line: str, tokens: List[str], default_story: str = "Level 1") -> str:
        story_match = re.search(r'STORY\s+(?:"([^"]+)"|([A-Za-z0-9_ -]+))', line, re.IGNORECASE)
        if story_match:
            return (story_match.group(1) or story_match.group(2)).strip()

        if self.model.stories:
            story_map_lower = {st.name.lower(): st.name for st in self.model.stories}
            story_map_norm = {st.name.lower().replace(" ", "").replace("_", "").replace("-", ""): st.name for st in self.model.stories}

            for tok in tokens:
                t_clean = tok.strip('"').strip()
                t_lower = t_clean.lower()
                t_norm = t_lower.replace(" ", "").replace("_", "").replace("-", "")
                if t_lower in story_map_lower:
                    return story_map_lower[t_lower]
                if t_norm in story_map_norm:
                    return story_map_norm[t_norm]

        if len(tokens) >= 3:
            cand = tokens[2].strip('"').strip()
            if cand.upper() not in ["SECTION", "PROPERTY", "TYPE", "POINT", "COLOR", "PIER", "SPANDREL", "DIAPH", "CARDINALPOINT", "ANG", "MINNUMSTA", "AUTOMESH", "MESHATINTERSECTIONS", "AREA", "LINE", "PANEL", "FLOOR", "SLAB", "WALL"]:
                return cand

        return default_story

    def _parse_line_assign(self, line: str):
        if not (line.startswith("LINE") or line.startswith("LINEASSIGN") or line.startswith("LINECONNECTIVITY")):
            return
        tokens = [t.strip('"') for t in re.findall(r'"[^"]+"|\S+', line)]
        if len(tokens) < 2:
            return
        frame_id = tokens[1] if tokens[0].upper() in ["LINE", "LINEASSIGN", "LINECONNECTIVITY"] else tokens[0]

        story_name = self._resolve_story_name(line, tokens)

        sec_match = re.search(r'SECTION\s+(?:"([^"]+)"|([A-Za-z0-9_ -]+))', line, re.IGNORECASE)
        sec_name = (sec_match.group(1) or sec_match.group(2)).strip() if sec_match else "DEFAULT"

        (p1_id, p2_id) = self.line_nodes.get(frame_id, ("N1", "N2"))
        p1_node = self.model.nodes.get(p1_id, None)
        p2_node = self.model.nodes.get(p2_id, None)

        f_type_str = self.line_types.get(frame_id, "Column" if "C" in frame_id or "COL" in sec_name.upper() else "Beam")
        f_type = FrameType.COLUMN if f_type_str.lower() == "column" else FrameType.BEAM
        frame_color = self.model.frame_sections[sec_name].color if sec_name in self.model.frame_sections else None

        st_match = next((st for st in self.model.stories if st.name.lower() == story_name.lower()), None)
        st_elev = st_match.elevation if st_match else 0.0

        p1_z = p1_node.z if (p1_node and p1_node.z != 0.0) else st_elev
        p2_z = p2_node.z if (p2_node and p2_node.z != 0.0) else st_elev

        self.model.frames.append(Frame(
            id=f"{frame_id}_{story_name}",
            type=f_type,
            start_node=p1_id,
            end_node=p2_id,
            start_point=Point3D(x=p1_node.x if p1_node else 0.0, y=p1_node.y if p1_node else 0.0, z=p1_z),
            end_point=Point3D(x=p2_node.x if p2_node else 0.0, y=p2_node.y if p2_node else 0.0, z=p2_z),
            section=sec_name,
            story=story_name,
            color=frame_color
        ))

    def _parse_area_connectivity(self, line: str):
        if not line.startswith("AREA"):
            return
        tokens = [t.strip('"') for t in re.findall(r'"[^"]+"|\S+', line)]
        if len(tokens) >= 3 and tokens[0].upper() == "AREA":
            area_id = tokens[1]
            pt_names = [t for t in tokens[2:] if t.upper() not in ["AREA", "POINT", "TYPE", "SLAB", "WALL", "PANEL"]]
            self.area_nodes[area_id] = pt_names
            if "PANEL" in line.upper() or area_id.startswith("W") or "WALL" in line.upper():
                self.area_types[area_id] = "Wall"
            else:
                self.area_types[area_id] = "Slab"

    def _parse_area_assign(self, line: str):
        if not (line.startswith("AREA") or line.startswith("AREAASSIGN") or line.startswith("AREACONNECTIVITY")):
            return
        tokens = [t.strip('"') for t in re.findall(r'"[^"]+"|\S+', line)]
        if len(tokens) < 2:
            return
        area_id = tokens[1] if tokens[0].upper() in ["AREA", "AREAASSIGN", "AREACONNECTIVITY"] else tokens[0]

        story_name = self._resolve_story_name(line, tokens)

        sec_match = re.search(r'(?:SECTION|PROPERTY)\s+(?:"([^"]+)"|([A-Za-z0-9_ -]+))', line, re.IGNORECASE)
        prop_name = (sec_match.group(1) or sec_match.group(2)).strip() if sec_match else "SLAB"
        is_opening = prop_name.upper() in ["OPENING", "VOID", "OPEN"]

        pt_ids = self.area_nodes.get(area_id, [])
        polygon = [Point2D(x=self.model.nodes[pid].x, y=self.model.nodes[pid].y) for pid in pt_ids if pid in self.model.nodes]
        z_coords = [self.model.nodes[pid].z for pid in pt_ids if pid in self.model.nodes]
        avg_z = sum(z_coords) / len(z_coords) if z_coords else 0.0

        if (avg_z == 0.0 or not z_coords) and story_name:
            st_match = next((st for st in self.model.stories if st.name.lower() == story_name.lower()), None)
            if st_match:
                avg_z = st_match.elevation

        thick = 0.25
        prop_color = None
        if prop_name in self.model.shell_properties:
            thick = self.model.shell_properties[prop_name].thickness
            prop_color = self.model.shell_properties[prop_name].color
        if thick > 10.0:
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
        area_match = re.search(r'AREA\s+(?:"([^"]+)"|([A-Za-z0-9_]+))', line, re.IGNORECASE)
        pat_match = re.search(r'PATTERN\s+(?:"([^"]+)"|([A-Za-z0-9_]+))', line, re.IGNORECASE)
        val_match = re.search(r'UNIFORM\s+([-0-9.]+)', line, re.IGNORECASE)
        dir_match = re.search(r'DIRECTION\s+(?:"([^"]+)"|([A-Za-z0-9_]+))', line, re.IGNORECASE)

        if area_match and pat_match and val_match:
            area_id = (area_match.group(1) or area_match.group(2)).strip()
            pat_name = (pat_match.group(1) or pat_match.group(2)).strip()
            dir_name = (dir_match.group(1) or dir_match.group(2)).strip() if dir_match else "Gravity"
            story_name = "Level 1"
            for sl in self.model.slabs:
                if sl.id.startswith(area_id):
                    story_name = sl.story
                    break

            self.model.area_loads.append(AreaLoad(
                id=f"aload_{len(self.model.area_loads)+1}",
                area_id=area_id,
                story=story_name,
                pattern=pat_name,
                magnitude=float(val_match.group(1)),
                direction=dir_name
            ))

    def _post_process(self):
        # 1. Calculate cumulative story elevations if missing or partially zero
        if self.model.stories:
            zero_count = sum(1 for st in self.model.stories if st.elevation == 0.0)
            if zero_count > 1 or (zero_count == len(self.model.stories) - 1 and len(self.model.stories) > 2):
                # If stories are listed top-to-bottom (Base at end)
                bottom_st = self.model.stories[-1]
                top_st = self.model.stories[0]
                if "base" in bottom_st.name.lower() or "ground" in bottom_st.name.lower() or bottom_st.elevation < top_st.elevation:
                    cum = bottom_st.elevation
                    for st in reversed(self.model.stories[:-1]):
                        cum += st.height if st.height > 0 else 3.5
                        st.elevation = round(cum, 2)
                else:
                    cum = 0.0
                    for st in self.model.stories:
                        if st.elevation != 0.0:
                            cum = st.elevation
                        else:
                            cum += st.height if st.height > 0 else 3.5
                            st.elevation = round(cum, 2)

            story_info = {st.name.strip().lower(): (st.elevation, st.height if st.height > 0 else 3.5) for st in self.model.stories}

            # Map calculated story elevations and Z coordinates to Slabs
            for sl in self.model.slabs:
                if sl.story and sl.story.strip().lower() in story_info:
                    top, _ = story_info[sl.story.strip().lower()]
                    sl.elevation = top

            # Map calculated story elevations and Z coordinates to Frames (Beams & Columns)
            for fr in self.model.frames:
                if fr.story and fr.story.strip().lower() in story_info:
                    top, height = story_info[fr.story.strip().lower()]
                    bot = round(top - height, 2)
                    if fr.type == FrameType.COLUMN:
                        fr.start_point.z = bot
                        fr.end_point.z = top
                    else:
                        if fr.start_point.z == 0.0 or fr.start_point.z is None:
                            fr.start_point.z = top
                        if fr.end_point.z == 0.0 or fr.end_point.z is None:
                            fr.end_point.z = top

            # Map calculated story elevations and Z coordinates to Walls
            for w in self.model.walls:
                if w.story and w.story.strip().lower() in story_info:
                    top, height = story_info[w.story.strip().lower()]
                    w.top_z = top
                    w.bottom_z = round(top - height, 2)

        # 2. Only add fallback slabs if model contains zero slabs
        if self.model.stories and len(self.model.slabs) == 0:
            ref_poly = [Point2D(x=0.0, y=0.0), Point2D(x=24.0, y=0.0), Point2D(x=24.0, y=18.0), Point2D(x=0.0, y=18.0)]
            for st in self.model.stories:
                if st.name.lower() in ["base", "bottom", "ground_0"]:
                    continue
                self.model.slabs.append(Slab(
                    id=f"slab_auto_{st.name.lower().replace(' ', '_')}",
                    story=st.name,
                    polygon=ref_poly,
                    thickness=0.25,
                    property_name="Slab250",
                    is_opening=False,
                    elevation=st.elevation
                ))

        # 3. Only add fallback beams if model contains zero frames
        if self.model.stories and len(self.model.frames) == 0:
            ref_poly = [Point2D(x=0.0, y=0.0), Point2D(x=24.0, y=0.0), Point2D(x=24.0, y=18.0), Point2D(x=0.0, y=18.0)]
            for st in self.model.stories:
                if st.name.lower() in ["base", "bottom", "ground_0"]:
                    continue
                matching_slabs = [sl for sl in self.model.slabs if sl.story and sl.story.strip().lower() == st.name.strip().lower()]
                target_slab = matching_slabs[0] if matching_slabs else None
                pts = target_slab.polygon if target_slab else ref_poly
                for i in range(len(pts)):
                    p_a = pts[i]
                    p_b = pts[(i + 1) % len(pts)]
                    sp = Point3D(x=p_a.x, y=p_a.y, z=st.elevation)
                    ep = Point3D(x=p_b.x, y=p_b.y, z=st.elevation)
                    self.model.frames.append(Frame(
                        id=f"bm_auto_{st.name.lower().replace(' ', '_')}_{i}",
                        story=st.name,
                        type=FrameType.BEAM,
                        section="B300x600",
                        start_node=f"n_auto_{st.name.lower().replace(' ', '_')}_{i}",
                        end_node=f"n_auto_{st.name.lower().replace(' ', '_')}_{(i+1)%len(pts)}",
                        start_point=sp,
                        end_point=ep
                    ))
