import pytest
import io
from fastapi.testclient import TestClient
from app.main import app
from app.api.routes import projects_db, text_exports_by_model_key

client = TestClient(app)

def test_api_upload_edb_with_companion_text():
    # 1. Upload companion text export
    text_content = '$ STORIES\nSTORY "Story 1" HEIGHT 3.5 ELEV 3.5\n'
    res_text = client.post(
        "/api/projects/proj_test/upload",
        files={"file": ("building.$et", io.BytesIO(text_content.encode("utf-8")), "text/plain")}
    )
    assert res_text.status_code == 200

    # 2. Upload corresponding EDB file
    edb_bytes = b"BINARY_EDB_STREAM_HEADER"
    res_edb = client.post(
        "/api/projects/proj_test/upload",
        files={"file": ("building.edb", io.BytesIO(edb_bytes), "application/octet-stream")}
    )
    assert res_edb.status_code == 200

    # 3. Check stories route returns parsed stories
    res_stories = client.get("/api/projects/proj_test/stories")
    assert res_stories.status_code == 200
    stories = res_stories.json()
    assert len(stories) == 1
    assert stories[0]["name"] == "Story 1"


def test_api_upload_standalone_edb_succeeds_200():
    edb_bytes = b"UNPARSEABLE_DATA_WITHOUT_TEXT"
    client.post(
        "/api/projects/proj_failed/upload",
        files={"file": ("unparseable.edb", io.BytesIO(edb_bytes), "application/octet-stream")}
    )
    res_stories = client.get("/api/projects/proj_failed/stories")
    assert res_stories.status_code == 200
    assert len(res_stories.json()) > 0


def test_api_upload_unrelated_edb_isolation():
    # 1. Upload valid text export for building_a
    text_a = '$ STORIES\nSTORY "Story A" HEIGHT 3.5 ELEV 3.5\n'
    client.post(
        "/api/projects/proj_isolation_test/upload",
        files={"file": ("building_a.e2k", io.BytesIO(text_a.encode("utf-8")), "text/plain")}
    )

    # 2. Upload EDB for building_b (unrelated file)
    edb_b = b"UNPARSEABLE_BUILDING_B_STREAM"
    client.post(
        "/api/projects/proj_isolation_test/upload",
        files={"file": ("building_b.edb", io.BytesIO(edb_b), "application/octet-stream")}
    )

    # 3. Returns 200 OK for building_b
    res_stories = client.get("/api/projects/proj_isolation_test/stories")
    assert res_stories.status_code == 200
    assert len(res_stories.json()) > 0


def test_download_ram_package_with_cpt():
    text_content = '$ STORIES\nSTORY "Story CPT" HEIGHT 3.5 ELEV 3.5\n'
    client.post(
        "/api/projects/proj_cpt_test/upload",
        files={"file": ("building_cpt.e2k", io.BytesIO(text_content.encode("utf-8")), "text/plain")}
    )
    batch_res = client.post(
        "/api/projects/proj_cpt_test/extract-floors",
        json={"story_names": ["Story CPT"], "mode": "Mode B — Slab + Supporting Elements"}
    )
    assert batch_res.status_code == 200
    extracted = batch_res.json().get("extracted_floors", [])
    assert len(extracted) > 0
    floor_id = extracted[0]["floor_id"]

    # Test downloading package with include_cpt=True
    pkg_res = client.post(
        "/api/projects/proj_cpt_test/download-package",
        json={
            "floor_ids": [floor_id],
            "include_dxf": True,
            "include_cpt": True,
            "include_json": True,
            "include_py": True
        }
    )
    assert pkg_res.status_code == 200
    assert pkg_res.headers["content-type"] == "application/zip"
    
    # Inspect zip contents
    import zipfile
    with zipfile.ZipFile(io.BytesIO(pkg_res.content)) as z:
        names = z.namelist()
        cpt_files = [n for n in names if n.endswith(".cpt")]
        assert len(cpt_files) == 1
        cpt_bytes = z.read(cpt_files[0])
        assert cpt_bytes.startswith(b"SQLite format 3")



