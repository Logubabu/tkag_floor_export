"""
Unit Conversion Matrix and Engineering Units Management System.
Supports ETABS engineering units: kN, N, kgf, kip, lb, m, mm, cm, ft, in.
"""
from dataclasses import dataclass
from typing import Dict

LENGTH_TO_METERS: Dict[str, float] = {
    "M": 1.0,
    "METER": 1.0,
    "METERS": 1.0,
    "MM": 0.001,
    "MILLIMETER": 0.001,
    "MILLIMETERS": 0.001,
    "CM": 0.01,
    "CENTIMETER": 0.01,
    "CENTIMETERS": 0.01,
    "FT": 0.3048,
    "FEET": 0.3048,
    "FOOT": 0.3048,
    "IN": 0.0254,
    "INCH": 0.0254,
    "INCHES": 0.0254,
}

FORCE_TO_KN: Dict[str, float] = {
    "KN": 1.0,
    "KILONEWTON": 1.0,
    "KILONEWTONS": 1.0,
    "N": 0.001,
    "NEWTON": 0.001,
    "NEWTONS": 0.001,
    "KIP": 4.4482216152605,
    "KIPS": 4.4482216152605,
    "LB": 0.0044482216152605,
    "LBS": 0.0044482216152605,
    "POUND": 0.0044482216152605,
    "POUNDS": 0.0044482216152605,
    "KGF": 0.00980665,
    "KG": 0.00980665,
}

def convert_length(value: float, from_unit: str, to_unit: str) -> float:
    from_u = from_unit.upper().strip()
    to_u = to_unit.upper().strip()
    
    if from_u not in LENGTH_TO_METERS:
        raise ValueError(f"Unsupported length unit: {from_unit}")
    if to_u not in LENGTH_TO_METERS:
        raise ValueError(f"Unsupported length unit: {to_unit}")
        
    meters = value * LENGTH_TO_METERS[from_u]
    return meters / LENGTH_TO_METERS[to_u]

def convert_force(value: float, from_unit: str, to_unit: str) -> float:
    from_u = from_unit.upper().strip()
    to_u = to_unit.upper().strip()
    
    if from_u not in FORCE_TO_KN:
        raise ValueError(f"Unsupported force unit: {from_unit}")
    if to_u not in FORCE_TO_KN:
        raise ValueError(f"Unsupported force unit: {to_unit}")
        
    kn = value * FORCE_TO_KN[from_u]
    return kn / FORCE_TO_KN[to_u]

def convert_pressure(value: float, from_force: str, from_length: str, to_force: str, to_length: str) -> float:
    """Converts uniform surface load (e.g. kN/m² -> kip/ft²)."""
    force_val = convert_force(value, from_force, to_force)
    area_factor = (convert_length(1.0, from_length, to_length)) ** 2
    return force_val / area_factor

@dataclass
class UnitsSystem:
    force: str = "KN"
    length: str = "M"
    temperature: str = "C"

    def scale_length_to_m(self, val: float) -> float:
        return convert_length(val, self.length, "M")

    def scale_force_to_kn(self, val: float) -> float:
        return convert_force(val, self.force, "KN")
