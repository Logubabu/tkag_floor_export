// Unit Conversion Utilities for Length and Force Display

export interface UnitConfig {
  length: string; // m, mm, ft, in
  force: string;  // kN, N, kip, lb
}

export function formatLength(meters: number, unit: string): string {
  if (isNaN(meters) || meters === null || meters === undefined) return '0.00';

  switch (unit.toLowerCase()) {
    case 'mm':
      return `${(meters * 1000).toFixed(1)} mm`;
    case 'ft':
      return `${(meters * 3.28084).toFixed(2)} ft`;
    case 'in':
      return `${(meters * 39.3701).toFixed(2)} in`;
    case 'm':
    default:
      return `${meters.toFixed(2)} m`;
  }
}

export function formatForce(kN: number, unit: string): string {
  if (isNaN(kN) || kN === null || kN === undefined) return '0.00';

  switch (unit.toLowerCase()) {
    case 'n':
      return `${(kN * 1000).toFixed(0)} N`;
    case 'kip':
      return `${(kN * 0.224809).toFixed(2)} kip`;
    case 'lb':
      return `${(kN * 224.809).toFixed(1)} lb`;
    case 'kn':
    default:
      return `${kN.toFixed(2)} kN`;
  }
}

export function formatAreaLoad(kNm2: number, unit: string): string {
  if (isNaN(kNm2) || kNm2 === null || kNm2 === undefined) return '0.00';

  switch (unit.toLowerCase()) {
    case 'mm':
    case 'n':
      return `${(kNm2 * 0.001).toFixed(3)} N/mm²`;
    case 'ft':
    case 'kip':
      return `${(kNm2 * 0.0208854).toFixed(3)} ksf`;
    case 'in':
    case 'lb':
      return `${(kNm2 * 0.145038).toFixed(3)} psi`;
    case 'm':
    case 'kn':
    default:
      return `${kNm2.toFixed(2)} kN/m²`;
  }
}
