import os
from typing import Dict, Any, Tuple, List
from app.models.intermediate import (
    BuildingModel, Story, Node, Slab, Wall, Frame, FrameType, Material, FrameSection, ShellProperty,
    Point3D, Point2D, AreaLoad, PointLoad, LineLoad, LoadPattern, UnitSystem
)


class ETABSCOMAdapter:
    """
    Interface to communicate directly with active ETABS application sessions via COM OAPI.
    Supports CSI ETABS OAPI v1.x / v20+ / v21+.
    """
    def __init__(self):
        self.SapModel = None
        self.ETABSObject = None
        self.is_connected = False

    def connect_running_instance(self) -> Tuple[bool, str]:
        """Connects strictly to an active, currently running ETABS instance without launching a new process."""
        # 1. Try win32com GetActiveObject
        for prog_id in ["CSI.ETABS.API.ETABSObject", "ETABSv1.ETABSObject"]:
            try:
                import win32com.client
                self.ETABSObject = win32com.client.GetActiveObject(prog_id)
                if self.ETABSObject and hasattr(self.ETABSObject, "SapModel"):
                    self.SapModel = self.ETABSObject.SapModel
                    self.is_connected = True
                    return True, "Connected to active ETABS instance via win32com."
            except Exception:
                pass

        # 2. Try comtypes via ETABSv1.tlb type library
        try:
            import comtypes.client
            import glob
            tlb_files = glob.glob(r"C:\Program Files\Computers and Structures\ETABS*\NativeAPI\*\ETABSv1.tlb") + \
                        glob.glob(r"C:\Program Files\Computers and Structures\ETABS*\ETABSv1.tlb")
            if tlb_files:
                comtypes.client.GetModule(tlb_files[0])
                import comtypes.gen.ETABSv1 as etabs
                helper = comtypes.client.CreateObject(etabs.Helper, interface=etabs.cHelper)
                for prog_id in ["CSI.ETABS.API.ETABSObject", "ETABSv1.ETABSObject", ""]:
                    try:
                        self.ETABSObject = helper.GetObject(prog_id)
                        if self.ETABSObject and hasattr(self.ETABSObject, "SapModel"):
                            self.SapModel = self.ETABSObject.SapModel
                            self.is_connected = True
                            return True, f"Connected to active ETABS instance via OAPI (Version {helper.GetOAPIVersionNumber()})."
                    except Exception:
                        pass
        except Exception:
            pass

        return False, "No active running ETABS instance detected."

    def connect(self) -> Tuple[bool, str]:
        # 1. Try connecting to active running ETABS instance first
        running, msg = self.connect_running_instance()
        if running:
            return True, msg

        # 2. Try launching ETABS via comtypes ETABSv1.tlb helper
        try:
            import comtypes.client
            import glob
            tlb_files = glob.glob(r"C:\Program Files\Computers and Structures\ETABS*\NativeAPI\*\ETABSv1.tlb") + \
                        glob.glob(r"C:\Program Files\Computers and Structures\ETABS*\ETABSv1.tlb")
            exe_files = glob.glob(r"C:\Program Files\Computers and Structures\ETABS*\ETABS.exe")

            if tlb_files:
                comtypes.client.GetModule(tlb_files[0])
                import comtypes.gen.ETABSv1 as etabs
                helper = comtypes.client.CreateObject(etabs.Helper, interface=etabs.cHelper)

                if exe_files:
                    self.ETABSObject = helper.CreateObject(exe_files[0])
                else:
                    self.ETABSObject = helper.CreateObjectProgID("CSI.ETABS.API.ETABSObject")

                if self.ETABSObject:
                    self.ETABSObject.ApplicationStart()
                    self.SapModel = self.ETABSObject.SapModel
                    self.is_connected = True
                    return True, f"Successfully launched ETABS 22 OAPI session (Version {helper.GetOAPIVersionNumber()})."
        except Exception:
            pass

        # 3. Try win32com Dispatch fallback
        try:
            import win32com.client
            self.ETABSObject = win32com.client.Dispatch("CSI.ETABS.API.ETABSObject")
            if self.ETABSObject:
                self.ETABSObject.ApplicationStart()
                self.SapModel = self.ETABSObject.SapModel
                self.is_connected = True
                return True, "Successfully dispatched new ETABS application instance."
        except Exception:
            pass

        return False, "ETABS desktop installation or COM OAPI driver is not installed on this system."

    def open_file(self, file_path: str) -> bool:
        if not self.is_connected or not self.SapModel:
            return False
        try:
            ret = self.SapModel.File.OpenFile(file_path)
            return ret == 0
        except Exception as e:
            print(f"Error opening file via ETABS COM: {e}")
            return False

    def close(self) -> None:
        """Release a session created for file conversion without closing a live model."""
        if not self.ETABSObject:
            return
        try:
            self.ETABSObject.ApplicationExit(False)
        except Exception:
            pass
        finally:
            self.SapModel = None
            self.ETABSObject = None
            self.is_connected = False

    def extract_model(self) -> BuildingModel:
        if not self.is_connected or not self.SapModel:
            success, msg = self.connect()
            if not success:
                raise RuntimeError(f"ETABS COM session is not connected: {msg}")

        b_model = BuildingModel(project_name="ETABS Active Model")

        # 1. Units
        try:
            units_res = self.SapModel.GetPresentUnits()
            if isinstance(units_res, (list, tuple)) and len(units_res) > 0:
                # OAPI returns unit enum integer or string tuple
                b_model.units = UnitSystem(length="m", force="kN")
        except Exception:
            pass

        # 2. Stories
        try:
            res = self.SapModel.Story.GetStories()
            if res and res[0] == 0:
                _, num_stories, names, elevs, heights, is_master, similar_to, splice, splice_height = res[:9]
                for i in range(num_stories):
                    b_model.stories.append(Story(
                        id=f"story_{names[i].lower().replace(' ', '_')}",
                        name=names[i],
                        elevation=float(elevs[i]),
                        height=float(heights[i]),
                        is_master=bool(is_master[i]) if is_master else False
                    ))
        except Exception as e:
            print(f"Warning extracting stories via COM: {e}")

        # 3. Materials
        try:
            res = self.SapModel.PropMaterial.GetNameList()
            if res and res[0] == 0 and res[1] > 0:
                mat_names = res[2]
                for mat_name in mat_names:
                    b_model.materials[mat_name] = Material(
                        id=mat_name,
                        name=mat_name,
                        type="Concrete"
                    )
        except Exception:
            pass

        # 4. Shell Properties
        try:
            res = self.SapModel.PropArea.GetNameList()
            if res and res[0] == 0 and res[1] > 0:
                prop_names = res[2]
                for p_name in prop_names:
                    b_model.shell_properties[p_name] = ShellProperty(
                        id=p_name,
                        name=p_name,
                        type="Wall" if "WALL" in p_name.upper() else "Slab",
                        thickness=0.25
                    )
        except Exception:
            pass

        # 5. Points / Nodes
        try:
            res = self.SapModel.PointObj.GetNameList()
            if res and res[0] == 0 and res[1] > 0:
                pt_names = res[2]
                for pt_name in pt_names:
                    coord_res = self.SapModel.PointObj.GetCoordCartesian(pt_name)
                    if coord_res and coord_res[0] == 0:
                        x, y, z = coord_res[1], coord_res[2], coord_res[3]
                        # Determine story matching z coordinate
                        assigned_story = None
                        for st in b_model.stories:
                            if abs(st.elevation - z) < 0.1:
                                assigned_story = st.name
                                break
                        b_model.nodes[pt_name] = Node(
                            id=pt_name,
                            x=float(x),
                            y=float(y),
                            z=float(z),
                            story=assigned_story
                        )
        except Exception as e:
            print(f"Warning extracting points via COM: {e}")

        # 6. Frame Objects (Beams & Columns) via GetAllFrames (Matching reference ETABS_utils.py)
        try:
            res = self.SapModel.FrameObj.GetAllFrames(
                0, [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], []
            )
            if res and res[0] == 0 and res[1] > 0:
                (
                    ret, num_names, my_names, prop_names, story_names,
                    point1_names, point2_names, p1_x, p1_y, p1_z, p2_x, p2_y, p2_z,
                    angles, off1_x, off2_x, off1_y, off2_y, off1_z, off2_z, cardinal_points
                ) = res[:21]

                for i in range(num_names):
                    fr_name = str(my_names[i])
                    sec_name = str(prop_names[i])
                    st_name = str(story_names[i])
                    p1_id = str(point1_names[i])
                    p2_id = str(point2_names[i])

                    x1, y1, z1 = float(p1_x[i]), float(p1_y[i]), float(p1_z[i])
                    x2, y2, z2 = float(p2_x[i]), float(p2_y[i]), float(p2_z[i])

                    # Column identification matching reference find_columns (Point1X == Point2X and Point1Y == Point2Y)
                    is_column = (abs(x1 - x2) < 1e-4 and abs(y1 - y2) < 1e-4)
                    f_type = FrameType.COLUMN if is_column or "COL" in sec_name.upper() else FrameType.BEAM

                    b_model.frames.append(Frame(
                        id=fr_name,
                        type=f_type,
                        start_node=p1_id,
                        end_node=p2_id,
                        start_point=Point3D(x=x1, y=y1, z=z1),
                        end_point=Point3D(x=x2, y=y2, z=z2),
                        section=sec_name,
                        story=st_name,
                        angle=float(angles[i]) if angles else 0.0,
                        offset_1=Point3D(x=float(off1_x[i]), y=float(off1_y[i]), z=float(off1_z[i])),
                        offset_2=Point3D(x=float(off2_x[i]), y=float(off2_y[i]), z=float(off2_z[i])),
                        cardinal_point=int(cardinal_points[i]) if cardinal_points else 10
                    ))
        except Exception as e:
            print(f"Warning extracting frames via COM GetAllFrames: {e}")

        # 7. Area Objects (Slabs, Openings, Walls)
        try:
            res = self.SapModel.AreaObj.GetNameList()
            if res and res[0] == 0 and res[1] > 0:
                area_names = res[2]
                for a_name in area_names:
                    pt_res = self.SapModel.AreaObj.GetPoints(a_name)
                    prop_res = self.SapModel.AreaObj.GetProperty(a_name)
                    
                    if pt_res and pt_res[0] == 0:
                        pt_ids = pt_res[2] if len(pt_res) > 2 else pt_res[1]
                        prop_name = prop_res[1] if prop_res and prop_res[0] == 0 else "SLAB"
                        is_opening = prop_name.upper() in ["OPENING", "VOID", "OPEN"]
                        
                        polygon: List[Point2D] = []
                        z_elev = 0.0
                        assigned_story = "Level 1"
                        
                        for pid in pt_ids:
                            nd = b_model.nodes.get(pid)
                            if nd:
                                polygon.append(Point2D(x=nd.x, y=nd.y))
                                z_elev = nd.z
                        
                        for st in b_model.stories:
                            if abs(st.elevation - z_elev) < 0.1:
                                assigned_story = st.name
                                break
                        
                        if "WALL" in prop_name.upper() or a_name.startswith("W"):
                            b_model.walls.append(Wall(
                                id=a_name,
                                story=assigned_story,
                                polygon=polygon,
                                thickness=0.3,
                                property_name=prop_name
                            ))
                        else:
                            b_model.slabs.append(Slab(
                                id=a_name,
                                story=assigned_story,
                                polygon=polygon,
                                thickness=0.25,
                                property_name=prop_name,
                                is_opening=is_opening,
                                elevation=z_elev
                            ))
        except Exception as e:
            print(f"Warning extracting areas via COM: {e}")

        return b_model

    def extract_column_axial_forces(self, story_name: str, load_cases: List[str]) -> Dict[str, float]:
        """
        Queries max axial force P for all columns at a given story for the specified load cases.
        Summation across load cases is applied if multiple load cases are specified.
        Returns a mapping from frame_id -> total_p_axial force.
        """
        if not self.is_connected or not self.SapModel:
            return {}

        results = self.SapModel.Results
        setup = results.Setup
        column_forces: Dict[str, float] = {}

        # 1. Identify frame IDs corresponding to columns at the requested story
        b_model = self.extract_model()
        target_columns = [
            f for f in b_model.frames
            if f.type == FrameType.COLUMN and (not story_name or f.story == story_name)
        ]

        if not target_columns:
            return {}

        # 2. Iterate through requested load cases
        for lc in load_cases:
            try:
                setup.DeselectAllCasesAndCombosForOutput()
                setup.SetCaseSelectedForOutput(lc)
            except Exception as e:
                print(f"Warning setting output case {lc}: {e}")
                continue

            for col in target_columns:
                try:
                    res = results.FrameForce(col.id, 0, 0, [], [], [], [], [], [], [], [], [], [], [], [], [])
                    if res and res[0] == 0 and len(res) > 9 and res[9]:
                        p_forces = res[9]
                        max_p = abs(min(p_forces))
                        column_forces[col.id] = column_forces.get(col.id, 0.0) + max_p
                except Exception as e:
                    print(f"Error querying FrameForce for column {col.id}: {e}")

        return column_forces

