import re
from typing import Dict, List, Optional
from app.models.intermediate import (
    BuildingModel, Story, Node, Frame, Slab, Wall, Material, FrameSection,
    ShellProperty, Point3D, Point2D, AreaLoad, PointLoad, LineLoad, LoadPattern,
    FrameType, UnitSystem
)


class E2KParser:
    """
    Parser for ETABS .E2K / .S2K text export files.
    Extracts structural geometry, properties, materials, story data, and loadings.
    """
    def __init__(self):
        self.model = BuildingModel()

    def parse_string(self, content: str) -> BuildingModel:
        lines = content.splitlines()
        current_section = None
        
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("$"):
                continue

            # Detect main section headers
            if stripped in [
                "PROGRAM INFORMATION", "CONTROLS", "STORIES", "MATERIAL PROPERTIES",
                "FRAME SECTIONS", "SHELL PROPERTIES", "POINT COORDINATES",
                "LINE ASSIGNS", "AREA ASSIGNS", "LOAD PATTERNS", "AREA LOADS", "END"
            ]:
                current_section = stripped
                continue

            # Process lines based on current active section
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
            elif current_section == "LINE ASSIGNS":
                self._parse_line_assign(stripped)
            elif current_section == "AREA ASSIGNS":
                self._parse_area_assign(stripped)
            elif current_section == "LOAD PATTERNS":
                self._parse_load_pattern(stripped)
            elif current_section == "AREA LOADS":
                self._parse_area_load(stripped)

        # Post-process: associate coordinates and materials
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
        
        # Format: STORY "Level 5" HEIGHT 3.0 ELEV 12.0 MASTER "Yes"
        name_match = re.search(r'STORY\s+"([^"]+)"', line)
        height_match = re.search(r'HEIGHT\s+([0-9.]+)', line)
        elev_match = re.search(r'ELEV\s+([0-9.]+)', line)
        master_match = re.search(r'MASTER\s+"([^"]+)"', line)

        if name_match and elev_match:
            story_name = name_match.group(1)
            elevation = float(elev_match.group(1))
            height = float(height_match.group(1)) if height_match else 3.0
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
        # MATERIAL "C30/37" TYPE "Concrete" E 32000000 FC 30000 POISSON 0.2
        name_match = re.search(r'MATERIAL\s+"([^"]+)"', line)
        type_match = re.search(r'TYPE\s+"([^"]+)"', line)
        e_match = re.search(r'E\s+([0-9.E+]+)', line)
        fc_match = re.search(r'FC\s+([0-9.E+]+)', line)
        poisson_match = re.search(r'POISSON\s+([0-9.]+)', line)

        if name_match:
            mat_name = name_match.group(1)
            self.model.materials[mat_name] = Material(
                id=mat_name,
                name=mat_name,
                type=type_match.group(1) if type_match else "Concrete",
                elasticity_modulus=float(e_match.group(1)) if e_match else 30000000.0,
                fc=float(fc_match.group(1)) if fc_match else 30000.0,
                poisson=float(poisson_match.group(1)) if poisson_match else 0.2
            )

    def _parse_frame_section(self, line: str):
        if not line.startswith("SECTION"):
            return
        # SECTION "C500x500" MATERIAL "C40/50" SHAPE "Rectangular" DEPTH 0.5 WIDTH 0.5
        name_match = re.search(r'SECTION\s+"([^"]+)"', line)
        mat_match = re.search(r'MATERIAL\s+"([^"]+)"', line)
        depth_match = re.search(r'DEPTH\s+([0-9.]+)', line)
        width_match = re.search(r'WIDTH\s+([0-9.]+)', line)

        if name_match:
            sec_name = name_match.group(1)
            self.model.frame_sections[sec_name] = FrameSection(
                id=sec_name,
                name=sec_name,
                material=mat_match.group(1) if mat_match else "Concrete",
                depth=float(depth_match.group(1)) if depth_match else 0.5,
                width=float(width_match.group(1)) if width_match else 0.3
            )

    def _parse_shell_property(self, line: str):
        if not line.startswith("SLAB") and not line.startswith("WALL"):
            return
        # SLAB "SLAB250" MATERIAL "C30/37" TYPE "Slab" THICKNESS 0.25
        # WALL "WALL300" MATERIAL "C40/50" TYPE "Wall" THICKNESS 0.30
        prop_type = "Slab" if line.startswith("SLAB") else "Wall"
        name_match = re.search(r'(?:SLAB|WALL)\s+"([^"]+)"', line)
        mat_match = re.search(r'MATERIAL\s+"([^"]+)"', line)
        thick_match = re.search(r'THICKNESS\s+([0-9.]+)', line)

        if name_match:
            prop_name = name_match.group(1)
            self.model.shell_properties[prop_name] = ShellProperty(
                id=prop_name,
                name=prop_name,
                material=mat_match.group(1) if mat_match else "Concrete",
                type=prop_type,
                thickness=float(thick_match.group(1)) if thick_match else 0.2
            )

    def _parse_point_coordinate(self, line: str):
        if not line.startswith("POINT"):
            return
        # POINT "N1" X 0.0 Y 0.0 Z 12.0 STORY "Level 5"
        name_match = re.search(r'POINT\s+"([^"]+)"', line)
        x_match = re.search(r'X\s+([-0-9.]+)', line)
        y_match = re.search(r'Y\s+([-0-9.]+)', line)
        z_match = re.search(r'Z\s+([-0-9.]+)', line)
        story_match = re.search(r'STORY\s+"([^"]+)"', line)

        if name_match and x_match and y_match and z_match:
            node_id = name_match.group(1)
            self.model.nodes[node_id] = Node(
                id=node_id,
                x=float(x_match.group(1)),
                y=float(y_match.group(1)),
                z=float(z_match.group(1)),
                story=story_match.group(1) if story_match else None
            )

    def _parse_line_assign(self, line: str):
        if not line.startswith("LINE"):
            return
        # LINE "C1" TYPE "Column" POINT1 "N7" POINT2 "N1" SECTION "C500x500" STORY "Level 5"
        name_match = re.search(r'LINE\s+"([^"]+)"', line)
        type_match = re.search(r'TYPE\s+"([^"]+)"', line)
        p1_match = re.search(r'POINT1\s+"([^"]+)"', line)
        p2_match = re.search(r'POINT2\s+"([^"]+)"', line)
        sec_match = re.search(r'SECTION\s+"([^"]+)"', line)
        story_match = re.search(r'STORY\s+"([^"]+)"', line)

        if name_match and p1_match and p2_match:
            frame_id = name_match.group(1)
            p1_id = p1_match.group(1)
            p2_id = p2_match.group(1)
            f_type_str = type_match.group(1) if type_match else "Beam"
            f_type = FrameType.COLUMN if f_type_str.lower() == "column" else FrameType.BEAM

            # Coordinates resolved in post_process if nodes available
            p1_node = self.model.nodes.get(p1_id, Node(id=p1_id, x=0, y=0, z=0))
            p2_node = self.model.nodes.get(p2_id, Node(id=p2_id, x=0, y=0, z=0))

            self.model.frames.append(Frame(
                id=frame_id,
                type=f_type,
                start_node=p1_id,
                end_node=p2_id,
                start_point=Point3D(x=p1_node.x, y=p1_node.y, z=p1_node.z),
                end_point=Point3D(x=p2_node.x, y=p2_node.y, z=p2_node.z),
                section=sec_match.group(1) if sec_match else "DEFAULT",
                story=story_match.group(1) if story_match else "Level 1"
            ))

    def _parse_area_assign(self, line: str):
        if not line.startswith("AREA"):
            return
        # AREA "S1" PROPERTY "SLAB250" STORY "Level 5" POINTS "N1" "N3" "N6" "N4"
        # AREA "O1" PROPERTY "OPENING" STORY "Level 5" POINTS_COORD (4.0,4.0) (6.0,4.0) (6.0,6.0) (4.0,6.0)
        name_match = re.search(r'AREA\s+"([^"]+)"', line)
        prop_match = re.search(r'PROPERTY\s+"([^"]+)"', line)
        story_match = re.search(r'STORY\s+"([^"]+)"', line)

        if not name_match:
            return
        
        area_id = name_match.group(1)
        prop_name = prop_match.group(1) if prop_match else "SLAB"
        story_name = story_match.group(1) if story_match else "Level 1"
        is_opening = prop_name.upper() in ["OPENING", "VOID", "OPEN"]

        # Parse inline coordinates or node references
        polygon: List[Point2D] = []
        coords_match = re.findall(r'\((-?[0-9.]+),\s*(-?[0-9.]+)(?:,\s*-?[0-9.]+)?\)', line)
        if coords_match:
            polygon = [Point2D(x=float(cx), y=float(cy)) for cx, cy in coords_match]
        else:
            pts_match = re.search(r'POINTS\s+((?:"[^"]+"\s*)+)', line)
            if pts_match:
                pt_names = re.findall(r'"([^"]+)"', pts_match.group(1))
                for pt_name in pt_names:
                    if pt_name in self.model.nodes:
                        nd = self.model.nodes[pt_name]
                        polygon.append(Point2D(x=nd.x, y=nd.y))

        # Check shell property for thickness & type
        thick = 0.2
        if prop_name in self.model.shell_properties:
            thick = self.model.shell_properties[prop_name].thickness
            if self.model.shell_properties[prop_name].type == "Wall":
                self.model.walls.append(Wall(
                    id=area_id,
                    story=story_name,
                    polygon=polygon,
                    thickness=thick,
                    property_name=prop_name
                ))
                return

        self.model.slabs.append(Slab(
            id=area_id,
            story=story_name,
            polygon=polygon,
            thickness=thick,
            property_name=prop_name,
            is_opening=is_opening
        ))

    def _parse_load_pattern(self, line: str):
        if not line.startswith("PATTERN"):
            return
        # PATTERN "DEAD" TYPE "Dead" SELFWEIGHT 1.0
        name_match = re.search(r'PATTERN\s+"([^"]+)"', line)
        type_match = re.search(r'TYPE\s+"([^"]+)"', line)
        sw_match = re.search(r'SELFWEIGHT\s+([0-9.]+)', line)

        if name_match:
            self.model.load_patterns.append(LoadPattern(
                name=name_match.group(1),
                type=type_match.group(1) if type_match else "Dead",
                self_weight_multiplier=float(sw_match.group(1)) if sw_match else 0.0
            ))

    def _parse_area_load(self, line: str):
        if not line.startswith("AREALOAD"):
            return
        # AREALOAD AREA "S1" PATTERN "SDL" UNIFORM 1.5 DIRECTION "Gravity"
        area_match = re.search(r'AREA\s+"([^"]+)"', line)
        pat_match = re.search(r'PATTERN\s+"([^"]+)"', line)
        val_match = re.search(r'UNIFORM\s+([-0-9.]+)', line)
        dir_match = re.search(r'DIRECTION\s+"([^"]+)"', line)

        if area_match and pat_match and val_match:
            area_id = area_match.group(1)
            # Find story of area
            story_name = "Level 1"
            for sl in self.model.slabs:
                if sl.id == area_id:
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
        # Update frame coordinates from node definitions
        for frame in self.model.frames:
            if frame.start_node in self.model.nodes:
                nd1 = self.model.nodes[frame.start_node]
                frame.start_point = Point3D(x=nd1.x, y=nd1.y, z=nd1.z)
            if frame.end_node in self.model.nodes:
                nd2 = self.model.nodes[frame.end_node]
                frame.end_point = Point3D(x=nd2.x, y=nd2.y, z=nd2.z)
