"""
ETABS Installation and Version Detector for Windows.
Checks Windows registry and standard CSI program installation directories.
"""
import os
import sys
import winreg
from typing import List, Dict, Optional

class ETABSVersionDetector:
    """Detects installed ETABS versions on Windows systems."""
    
    STANDARD_PATHS = [
        r"C:\Program Files\Computers and Structures\ETABS 22",
        r"C:\Program Files\Computers and Structures\ETABS 21",
        r"C:\Program Files\Computers and Structures\ETABS 20",
        r"C:\Program Files\Computers and Structures\ETABS 19",
        r"C:\Program Files (x86)\Computers and Structures\ETABS 21",
        r"C:\Program Files (x86)\Computers and Structures\ETABS 20",
    ]
    
    REGISTRY_KEYS = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Computers and Structures, Inc.\ETABS"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Computers and Structures, Inc.\ETABS"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Computers and Structures, Inc.\ETABS"),
    ]

    @classmethod
    def detect_installations(cls) -> List[Dict[str, str]]:
        installations = []
        seen_paths = set()
        
        # 1. Check registry
        if sys.platform == "win32":
            for root_key, key_path in cls.REGISTRY_KEYS:
                try:
                    with winreg.OpenKey(root_key, key_path) as key:
                        idx = 0
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(key, idx)
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    try:
                                        install_path, _ = winreg.QueryValueEx(subkey, "InstallPath")
                                        ver_str, _ = winreg.QueryValueEx(subkey, "Version")
                                        exe_path = os.path.join(install_path, "ETABS.exe")
                                        if os.path.exists(exe_path) and exe_path.lower() not in seen_paths:
                                            seen_paths.add(exe_path.lower())
                                            installations.append({
                                                "version": ver_str or subkey_name,
                                                "path": install_path,
                                                "exe": exe_path,
                                                "source": "registry"
                                            })
                                    except OSError:
                                        pass
                                idx += 1
                            except OSError:
                                break
                except OSError:
                    pass
        
        # 2. Check standard program files directories
        for std_path in cls.STANDARD_PATHS:
            exe_path = os.path.join(std_path, "ETABS.exe")
            if os.path.exists(exe_path) and exe_path.lower() not in seen_paths:
                seen_paths.add(exe_path.lower())
                folder_name = os.path.basename(std_path)
                ver_name = folder_name.replace("ETABS ", "") + ".0"
                installations.append({
                    "version": ver_name,
                    "path": std_path,
                    "exe": exe_path,
                    "source": "directory_scan"
                })
                
        return installations

    @classmethod
    def get_latest_installation(cls) -> Optional[Dict[str, str]]:
        installs = cls.detect_installations()
        if not installs:
            return None
        # Sort descending by version
        return sorted(installs, key=lambda x: x["version"], reverse=True)[0]
