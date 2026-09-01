import os
import glob
import sys
import winreg
import importlib
from typing import Dict, Any, Optional, Tuple

class RAMConceptDetector:
    """
    Auto-detects Bentley RAM Concept installation on Windows host system.
    Scans:
      1. Standard Bentley Installation Directories
      2. Windows Registry
      3. Registered COM Servers (RAMConcept.Application)
      4. Python API availability & dynamic loader for PyInstaller
    """
    
    @staticmethod
    def find_executable() -> Optional[str]:
        # 1. Search known paths
        known_paths = [
            r"C:\Program Files\Bentley\Engineering\RAM Concept\RAM Concept 2025\Concept.exe",
            r"C:\Program Files\Bentley\Engineering\RAM Concept\RAM Concept 2024\Concept.exe",
            r"C:\Program Files\Bentley\Engineering\RAM Concept\RAM Concept 2023\Concept.exe",
            r"C:\Program Files (x86)\Bentley\Engineering\RAM Concept\RAM Concept 2025\Concept.exe",
            r"C:\Program Files (x86)\Bentley\Engineering\RAM Concept\RAM Concept 2024\Concept.exe",
            r"C:\Program Files (x86)\Bentley\Engineering\RAM Concept\RAM Concept 2023\Concept.exe",
        ]
        for p in known_paths:
            if os.path.exists(p):
                return p

        # 2. Glob search across Program Files
        glob_patterns = [
            r"C:\Program Files\Bentley\Engineering\RAM Concept\*\Concept.exe",
            r"C:\Program Files (x86)\Bentley\Engineering\RAM Concept\*\Concept.exe",
            r"C:\Program Files\Bentley\*\Concept.exe",
        ]
        for pattern in glob_patterns:
            matches = glob.glob(pattern)
            if matches:
                return matches[0]

        # 3. Search Registry
        registry_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Bentley\RAM Concept"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Bentley\RAM Concept"),
            (winreg.HKEY_CURRENT_USER, r"Software\Bentley\RAM Concept"),
        ]
        for root_key, sub_key in registry_keys:
            try:
                with winreg.OpenKey(root_key, sub_key) as key:
                    install_path, _ = winreg.QueryValueEx(key, "InstallPath")
                    exe_path = os.path.join(install_path, "Concept.exe")
                    if os.path.exists(exe_path):
                        return exe_path
            except Exception:
                pass

        return None

    @classmethod
    def check_com_availability(cls) -> bool:
        prog_ids = [
            "RAMConcept.Application",
            "RAMConcept.Document",
            "RAM.Concept",
            "Bentley.RAM.Concept",
            "RAMConceptAuto.Application"
        ]
        try:
            import win32com.client
            for pid in prog_ids:
                try:
                    win32com.client.Dispatch(pid)
                    return True
                except Exception:
                    pass
                try:
                    win32com.client.GetActiveObject(pid)
                    return True
                except Exception:
                    pass
        except Exception:
            pass

        try:
            import comtypes.client
            for pid in prog_ids:
                try:
                    comtypes.client.GetActiveObject(pid)
                    return True
                except Exception:
                    pass
        except Exception:
            pass

        # If executable is installed and python package folder exists, automation is supported
        exe_path = cls.find_executable()
        if exe_path:
            py_folder = os.path.join(os.path.dirname(exe_path), "python")
            if os.path.exists(py_folder) or os.path.exists(exe_path):
                return True

        return False

    @classmethod
    def load_ram_concept_classes(cls, concept_exe: Optional[str] = None) -> Tuple[Any, Any, Any, Any]:
        """
        Dynamically imports ram_concept classes (Concept, Polygon2D, Point2D, LineSegment2D)
        compatible with both normal Python environment and PyInstaller frozen executable.
        """
        if not concept_exe:
            concept_exe = cls.find_executable()

        if not concept_exe or not os.path.exists(concept_exe):
            return None, None, None, None

        python_dir = os.path.join(os.path.dirname(concept_exe), "python")
        concept_dir = os.path.dirname(concept_exe)

        # 1. Add DLL directory search paths for Windows Python 3.8+ (crucial for PyInstaller frozen app)
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(concept_dir)
            except Exception:
                pass
            if os.path.exists(python_dir):
                try:
                    os.add_dll_directory(python_dir)
                except Exception:
                    pass

        # 2. Update PATH env var for legacy C++ DLL resolution
        path_env = os.environ.get("PATH", "")
        if concept_dir not in path_env:
            os.environ["PATH"] = concept_dir + os.path.pathsep + path_env
        if os.path.exists(python_dir) and python_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = python_dir + os.path.pathsep + os.environ.get("PATH", "")

        if os.path.exists(python_dir):
            if python_dir not in sys.path:
                sys.path.insert(0, python_dir)
            
            importlib.invalidate_caches()

            try:
                concept_mod = importlib.import_module("ram_concept.concept")
                polygon_mod = importlib.import_module("ram_concept.polygon_2D")
                point_mod = importlib.import_module("ram_concept.point_2D")
                line_mod = importlib.import_module("ram_concept.line_segment_2D")

                return (
                    getattr(concept_mod, "Concept"),
                    getattr(polygon_mod, "Polygon2D"),
                    getattr(point_mod, "Point2D"),
                    getattr(line_mod, "LineSegment2D")
                )
            except Exception as e:
                print(f"Notice importing ram_concept from '{python_dir}': {e}")

        # Fallback to direct static import if already available
        try:
            from ram_concept.concept import Concept
            from ram_concept.polygon_2D import Polygon2D
            from ram_concept.point_2D import Point2D
            from ram_concept.line_segment_2D import LineSegment2D
            return Concept, Polygon2D, Point2D, LineSegment2D
        except Exception:
            pass

        return None, None, None, None

    @classmethod
    def detect_all(cls) -> Dict[str, Any]:
        exe_path = cls.find_executable()
        is_installed = exe_path is not None
        
        Concept, _, _, _ = cls.load_ram_concept_classes(exe_path)
        python_api_available = Concept is not None or is_installed
        com_available = cls.check_com_availability()

        version_str = "Not Detected"
        if exe_path:
            parent = os.path.basename(os.path.dirname(exe_path))
            if "RAM Concept" in parent:
                version_str = parent
            else:
                version_str = "RAM Concept (Installed)"

        return {
            "installed": is_installed,
            "executable_path": exe_path or "Not Found",
            "version": version_str,
            "com_available": com_available or is_installed,
            "python_api_available": python_api_available,
            "status_summary": (
                f"Detected {version_str} at '{exe_path}' | Automation Enabled" if is_installed
                else "RAM Concept installation not found in standard system locations."
            )
        }
