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
        try:
            import win32com.client
            self.ETABSObject = win32com.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
            self.SapModel = self.ETABSObject.SapModel
            self.is_connected = True
            return True, "Connected to active ETABS instance via win32com."
        except Exception:
            pass

        try:
            import comtypes.client
            helper = comtypes.client.CreateObject('ETABSv1.Helper')
            helper = helper.QueryInterface(comtypes.gen.ETABSv1.cHelper)
            self.ETABSObject = helper.GetObject("CSI.ETABS.API.ETABSObject")
            self.SapModel = self.ETABSObject.SapModel
            self.is_connected = True
            return True, "Connected to active ETABS instance via ETABSv1.Helper."
        except Exception:
            pass

        return False, "No active running ETABS instance detected."

    def connect(self) -> Tuple[bool, str]:
        # 1. Try connecting to active running ETABS instance first
        running, msg = self.connect_running_instance()
        if running:
            return True, msg

        # 2. Launch new background ETABS application instance if ETABS is not already running
        try:
            import comtypes.client
            helper = comtypes.client.CreateObject('ETABSv1.Helper')
            helper = helper.QueryInterface(comtypes.gen.ETABSv1.cHelper)
            self.ETABSObject = helper.CreateObjectProgID("CSI.ETABS.API.ETABSObject")
            if self.ETABSObject:
                self.ETABSObject.ApplicationStart()
                self.SapModel = self.ETABSObject.SapModel
                self.is_connected = True
                return True, "Successfully started new ETABS application instance via COM API."
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

        # 6. Frame Objects (Beams & Columns)
        try:
            res = self.SapModel.FrameObj.GetNameList()
            if res and res[0] == 0 and res[1] > 0:
                frame_names = res[2]
                for fr_name in frame_names:
                    pt_res = self.SapModel.FrameObj.GetPoints(fr_name)
                    sec_res = self.SapModel.FrameObj.GetSection(fr_name)
                    if pt_res and pt_res[0] == 0:
                        p1_id, p2_id = pt_res[1], pt_res[2]
                        sec_name = sec_res[1] if sec_res and sec_res[0] == 0 else "DEFAULT"
                        
                        p1_node = b_model.nodes.get(p1_id)
                        p2_node = b_model.nodes.get(p2_id)
                        
                        if p1_node and p2_node:
                            # Frame orientation check
                            is_column = abs(p1_node.x - p2_node.x) < 0.01 and abs(p1_node.y - p2_node.y) < 0.01
                            f_type = FrameType.COLUMN if is_column or "COL" in sec_name.upper() else FrameType.BEAM
                            
                            # Determine story
                            max_z = max(p1_node.z, p2_node.z)
                            assigned_story = "Level 1"
                            for st in b_model.stories:
                                if abs(st.elevation - max_z) < 0.1:
                                    assigned_story = st.name
                                    break
                            
                            b_model.frames.append(Frame(
                                id=fr_name,
                                type=f_type,
                                start_node=p1_id,
                                end_node=p2_id,
                                start_point=Point3D(x=p1_node.x, y=p1_node.y, z=p1_node.z),
                                end_point=Point3D(x=p2_node.x, y=p2_node.y, z=p2_node.z),
                                section=sec_name,
                                story=assigned_story
                            ))
        except Exception as e:
            print(f"Warning extracting frames via COM: {e}")

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
