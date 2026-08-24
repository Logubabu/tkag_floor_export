import os
import sys
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger("ETABSAdapter")

class ETABSAdapter:
    """
    Adapter layer interfacing directly with official ETABS OAPI on Windows.
    Provides fallback to E2K text parser when running on non-Windows environment.
    """
    def __init__(self, etabs_path: Optional[str] = None):
        self.etabs_path = etabs_path
        self.helper = None
        self.sap_model = None
        self.is_connected = False

    def connect(self) -> Tuple[bool, str]:
        if sys.platform != "win32":
            return False, "ETABS OAPI requires Windows OS (win32com). Cross-platform mode uses E2K text parser."

        try:
            import comtypes.client # type: ignore
            helper = comtypes.client.CreateObject('ETABSv1.Helper')
            helper = helper.QueryInterface(comtypes.client.GetModule(['{776D58D2-605B-4BBA-B777-76E046D09435}', 1, 0]).cHelper)
            
            # Try connecting to active ETABS instance
            my_etabs = helper.GetObject("CSI.ETABS.API.ETABSObject")
            if my_etabs:
                self.sap_model = my_etabs.SapModel
                self.is_connected = True
                return True, "Successfully connected to active ETABS instance."
            
            return False, "ETABS application is not running or COM interface is unavailable."
        except Exception as e:
            logger.warning(f"ETABS OAPI COM connection error: {e}")
            return False, f"ETABS OAPI connection failed: {e}"

    def open_model(self, file_path: str) -> Tuple[bool, str]:
        if not self.is_connected or not self.sap_model:
            return False, "Not connected to ETABS SapModel."

        try:
            ret = self.sap_model.File.OpenFile(file_path)
            if ret == 0:
                return True, f"Opened model file {file_path} successfully."
            return False, f"ETABS returned error code {ret} when opening file {file_path}."
        except Exception as e:
            return False, f"Failed to open model: {e}"

    def get_stories(self) -> Dict[str, Any]:
        if not self.sap_model:
            return {"stories": []}
        try:
            num_stories, story_names, story_elevs, story_heights, is_master, similar_to, ret = self.sap_model.Story.GetStories()
            stories = []
            for i in range(num_stories):
                stories.append({
                    "id": f"ST_{i+1}",
                    "name": story_names[i],
                    "elevation": float(story_elevs[i]),
                    "height": float(story_heights[i]),
                    "is_master": bool(is_master[i]),
                    "similar_to": similar_to[i]
                })
            return {"stories": stories}
        except Exception as e:
            logger.error(f"Error fetching stories via OAPI: {e}")
            return {"stories": []}
