import os
from typing import Dict, Any, Tuple
from app.models.intermediate import BuildingModel, Story, Node, Slab, Frame, FrameType, Point3D, Point2D


class ETABSCOMAdapter:
    """
    Interface to communicate directly with active ETABS application sessions via COM OAPI.
    """
    def __init__(self):
        self.SapModel = None
        self.ETABSObject = None
        self.is_connected = False

    def connect(self) -> Tuple[bool, str]:
        # Try win32com GetActiveObject first
        try:
            import win32com.client
            self.ETABSObject = win32com.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
            self.SapModel = self.ETABSObject.SapModel
            self.is_connected = True
            return True, "Connected to active ETABS instance via win32com."
        except Exception:
            pass

        # Try comtypes CreateObject / Helper
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

        return False, "ETABS COM API not available or ETABS is not running locally."

    def extract_model(self) -> BuildingModel:
        if not self.is_connected or not self.SapModel:
            raise RuntimeError("ETABS COM session is not connected.")
        
        # Build BuildingModel from live SapModel calls
        b_model = BuildingModel(project_name="ETABS Active Model")
        
        # 1. Stories
        ret, num_stories, names, elevs, heights, is_master, similar_to, splice, splice_height = self.SapModel.Story.GetStories()
        if ret == 0:
            for i in range(num_stories):
                b_model.stories.append(Story(
                    id=f"story_{names[i].lower()}",
                    name=names[i],
                    elevation=elevs[i],
                    height=heights[i],
                    is_master=is_master[i]
                ))

        return b_model
