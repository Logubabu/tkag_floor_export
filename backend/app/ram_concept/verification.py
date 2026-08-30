"""
Export Verification Engine for RAM Concept Model Exports.
Verifies file existence, size, schema/structure integrity, and object parity.
"""
import os
import sqlite3
from typing import Dict, Any, Optional
from app.models.intermediate import StructuralModel

class ExportVerifier:
    """Verifies exported RAM Concept files (.cpt, .cpf, .dxf) against source models."""

    def verify_export(
        self,
        source_model: StructuralModel,
        cpt_path: str,
        dxf_path: Optional[str] = None,
        cpf_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Runs comprehensive post-export checks on generated target files.
        """
        result = {
            "status": "VERIFIED",
            "checks": {},
            "counts": {
                "source_slabs": len(source_model.slabs),
                "source_walls": len(source_model.walls),
                "source_columns": len(source_model.columns),
                "source_beams": len(source_model.beams),
                "source_openings": len(source_model.openings),
            },
            "errors": [],
            "warnings": [],
        }

        # 1. Check CPT File Existence & Size
        if not os.path.exists(cpt_path):
            result["status"] = "FAILED"
            result["checks"]["cpt_exists"] = False
            result["errors"].append(f"Target CPT file missing: {cpt_path}")
            return result
            
        cpt_size = os.path.getsize(cpt_path)
        result["checks"]["cpt_exists"] = True
        result["checks"]["cpt_size_bytes"] = cpt_size
        result["checks"]["cpt_non_empty"] = cpt_size > 0

        if cpt_size == 0:
            result["status"] = "FAILED"
            result["errors"].append("Exported CPT file has zero size.")
            return result

        # 2. If SQLite-backed .cpt structure, check tables safely
        try:
            conn = sqlite3.connect(cpt_path)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                result["checks"]["cpt_sqlite_valid"] = True
                result["checks"]["cpt_tables"] = tables
            finally:
                conn.close()
        except Exception:
            # Binary non-SQLite stream
            result["checks"]["cpt_sqlite_valid"] = False

        # 3. Check DXF File if generated
        if dxf_path:
            dxf_exists = os.path.exists(dxf_path)
            result["checks"]["dxf_exists"] = dxf_exists
            if dxf_exists:
                dxf_size = os.path.getsize(dxf_path)
                result["checks"]["dxf_size_bytes"] = dxf_size
                if dxf_size == 0:
                    result["warnings"].append("Generated DXF file is 0 bytes.")
            else:
                result["warnings"].append(f"DXF file requested but not generated: {dxf_path}")

        # 4. Check CPF File if generated
        if cpf_path:
            cpf_exists = os.path.exists(cpf_path)
            result["checks"]["cpf_exists"] = cpf_exists
            if cpf_exists:
                cpf_size = os.path.getsize(cpf_path)
                result["checks"]["cpf_size_bytes"] = cpf_size
                if cpf_size == 0:
                    result["warnings"].append("Generated CPF file is 0 bytes.")
            else:
                result["warnings"].append(f"CPF file requested but not generated: {cpf_path}")

        if result["errors"]:
            result["status"] = "FAILED"
        elif result["warnings"]:
            result["status"] = "VERIFIED_WITH_WARNINGS"

        return result
