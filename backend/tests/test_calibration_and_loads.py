import pytest
import numpy as np
from app.geometry.processor import GeometryProcessor


def test_find_rotation_matrix_90deg_ccw():
    # Rotate [1, 0] to [0, 1] (90 deg counter-clockwise)
    rot = GeometryProcessor.find_rotation_matrix((1, 0), (0, 1))
    expected = np.array([[0, -1], [1, 0]])
    assert np.allclose(rot, expected, atol=1e-5)


def test_find_rotation_matrix_same_direction():
    rot = GeometryProcessor.find_rotation_matrix((2, 2), (1, 1))
    expected = np.eye(2)
    assert np.allclose(rot, expected, atol=1e-5)


def test_calibrate_coordinates_translation_and_rotation():
    # Control points in ETABS coordinate system
    etabs_pt1 = (-1.0, 0.0)
    etabs_pt2 = (1.0, 0.0)
    # Target control points in RAM Concept coordinate system
    ram_pt1 = (1.0, 1.0)
    ram_pt2 = (1.0, 3.0)

    rot_matrix, translation = GeometryProcessor.calibrate_coordinates(etabs_pt1, etabs_pt2, ram_pt1, ram_pt2)

    # Verify transformation maps etabs_pt1 -> ram_pt1 and etabs_pt2 -> ram_pt2
    transformed1 = GeometryProcessor.transform_point_2d(etabs_pt1[0], etabs_pt1[1], rot_matrix, translation)
    transformed2 = GeometryProcessor.transform_point_2d(etabs_pt2[0], etabs_pt2[1], rot_matrix, translation)

    assert np.allclose(transformed1, ram_pt1, atol=1e-4)
    assert np.allclose(transformed2, ram_pt2, atol=1e-4)


def test_calibration_transform_api_route():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    payload = {
        "etabs_pt1": [-1.0, 0.0],
        "etabs_pt2": [1.0, 0.0],
        "ram_pt1": [1.0, 1.0],
        "ram_pt2": [1.0, 3.0]
    }
    response = client.post("/api/calibration/transform", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "rotation_matrix" in data
    assert "translation" in data
    assert np.allclose(data["preview"]["etabs_pt1_transformed"], [1.0, 1.0], atol=1e-4)
    assert np.allclose(data["preview"]["etabs_pt2_transformed"], [1.0, 3.0], atol=1e-4)
