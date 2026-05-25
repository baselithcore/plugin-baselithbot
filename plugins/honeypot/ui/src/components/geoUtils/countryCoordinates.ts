export interface GeoCoordinate {
  lat: number;
  lng: number;
}

export const COUNTRY_COORDINATES: Record<string, GeoCoordinate> = {
  // North America
  US: { lat: 37.0902, lng: -95.7129 },
  CA: { lat: 56.1304, lng: -106.3468 },
  MX: { lat: 23.6345, lng: -102.5528 },

  // Central America & Caribbean
  PA: { lat: 8.538, lng: -80.7821 },
  CR: { lat: 9.7489, lng: -83.7534 },
  CU: { lat: 21.5218, lng: -77.7812 },
  DO: { lat: 18.7357, lng: -70.1627 },
  GT: { lat: 15.7835, lng: -90.2308 },
  HN: { lat: 15.2, lng: -86.2419 },
  JM: { lat: 18.1096, lng: -77.2975 },
  PR: { lat: 18.2208, lng: -66.5901 },

  // South America
  BR: { lat: -14.235, lng: -51.9253 },
  AR: { lat: -38.4161, lng: -63.6167 },
  CL: { lat: -35.6751, lng: -71.543 },
  CO: { lat: 4.5709, lng: -74.2973 },
  PE: { lat: -9.19, lng: -75.0152 },
  VE: { lat: 6.4238, lng: -66.5897 },
  EC: { lat: -1.8312, lng: -78.1834 },
  UY: { lat: -32.5228, lng: -55.7658 },
  PY: { lat: -23.4425, lng: -58.4438 },
  BO: { lat: -16.2902, lng: -63.5887 },

  // Western Europe
  GB: { lat: 55.3781, lng: -3.436 },
  FR: { lat: 46.2276, lng: 2.2137 },
  DE: { lat: 51.1657, lng: 10.4515 },
  IT: { lat: 41.8719, lng: 12.5674 },
  ES: { lat: 40.4637, lng: -3.7492 },
  PT: { lat: 39.3999, lng: -8.2245 },
  NL: { lat: 52.1326, lng: 5.2913 },
  BE: { lat: 50.5039, lng: 4.4699 },
  CH: { lat: 46.8182, lng: 8.2275 },
  AT: { lat: 47.5162, lng: 14.5501 },
  IE: { lat: 53.4129, lng: -8.2439 },
  LU: { lat: 49.8153, lng: 6.1296 },
  MC: { lat: 43.7384, lng: 7.4246 },

  // Northern Europe
  SE: { lat: 60.1282, lng: 18.6435 },
  NO: { lat: 60.472, lng: 8.4689 },
  FI: { lat: 61.9241, lng: 25.7482 },
  DK: { lat: 56.2639, lng: 9.5018 },
  IS: { lat: 64.9631, lng: -19.0208 },

  // Baltic States
  LT: { lat: 55.1694, lng: 23.8813 },
  LV: { lat: 56.8796, lng: 24.6032 },
  EE: { lat: 58.5953, lng: 25.0136 },

  // Central Europe
  PL: { lat: 51.9194, lng: 19.1451 },
  CZ: { lat: 49.8175, lng: 15.473 },
  SK: { lat: 48.669, lng: 19.699 },
  HU: { lat: 47.1625, lng: 19.5033 },
  SI: { lat: 46.1512, lng: 14.9955 },

  // Eastern Europe
  UA: { lat: 48.3794, lng: 31.1656 },
  RU: { lat: 61.524, lng: 105.3188 },
  BY: { lat: 53.7098, lng: 27.9534 },
  MD: { lat: 47.4116, lng: 28.3699 },

  // Southeastern Europe (Balkans)
  RO: { lat: 45.9432, lng: 24.9668 },
  BG: { lat: 42.7339, lng: 25.4858 },
  GR: { lat: 39.0742, lng: 21.8243 },
  HR: { lat: 45.1, lng: 15.2 },
  RS: { lat: 44.0165, lng: 21.0059 },
  BA: { lat: 43.9159, lng: 17.6791 },
  ME: { lat: 42.7087, lng: 19.3744 },
  MK: { lat: 41.5124, lng: 21.7453 },
  AL: { lat: 41.1533, lng: 20.1683 },
  XK: { lat: 42.6026, lng: 20.903 },
  CY: { lat: 35.1264, lng: 33.4299 },
  MT: { lat: 35.9375, lng: 14.3754 },

  // Middle East
  TR: { lat: 38.9637, lng: 35.2433 },
  IL: { lat: 31.0461, lng: 34.8516 },
  SA: { lat: 23.8859, lng: 45.0792 },
  AE: { lat: 23.4241, lng: 53.8478 },
  IR: { lat: 32.4279, lng: 53.688 },
  IQ: { lat: 33.2232, lng: 43.6793 },
  SY: { lat: 34.8021, lng: 38.9968 },
  JO: { lat: 30.5852, lng: 36.2384 },
  LB: { lat: 33.8547, lng: 35.8623 },
  KW: { lat: 29.3117, lng: 47.4818 },
  QA: { lat: 25.3548, lng: 51.1839 },
  BH: { lat: 26.0667, lng: 50.5577 },
  OM: { lat: 21.4735, lng: 55.9754 },
  YE: { lat: 15.5527, lng: 48.5164 },

  // Central Asia
  KZ: { lat: 48.0196, lng: 66.9237 },
  UZ: { lat: 41.3775, lng: 64.5853 },
  TM: { lat: 38.9697, lng: 59.5563 },
  KG: { lat: 41.2044, lng: 74.7661 },
  TJ: { lat: 38.861, lng: 71.2761 },
  AZ: { lat: 40.1431, lng: 47.5769 },
  GE: { lat: 42.3154, lng: 43.3569 },
  AM: { lat: 40.0691, lng: 45.0382 },

  // South Asia
  IN: { lat: 20.5937, lng: 78.9629 },
  PK: { lat: 30.3753, lng: 69.3451 },
  BD: { lat: 23.685, lng: 90.3563 },
  LK: { lat: 7.8731, lng: 80.7718 },
  NP: { lat: 28.3949, lng: 84.124 },

  // East Asia
  CN: { lat: 35.8617, lng: 104.1954 },
  JP: { lat: 36.2048, lng: 138.2529 },
  KR: { lat: 35.9078, lng: 127.7669 },
  KP: { lat: 40.3399, lng: 127.5101 },
  TW: { lat: 23.6978, lng: 120.9605 },
  HK: { lat: 22.3193, lng: 114.1694 },
  MO: { lat: 22.1987, lng: 113.5439 },
  MN: { lat: 46.8625, lng: 103.8467 },

  // Southeast Asia
  ID: { lat: -0.7893, lng: 113.9213 },
  VN: { lat: 14.0583, lng: 108.2772 },
  TH: { lat: 15.87, lng: 100.9925 },
  SG: { lat: 1.3521, lng: 103.8198 },
  MY: { lat: 4.2105, lng: 101.9758 },
  PH: { lat: 12.8797, lng: 121.774 },
  MM: { lat: 21.9162, lng: 95.956 },
  KH: { lat: 12.5657, lng: 104.991 },
  LA: { lat: 19.8563, lng: 102.4955 },
  BN: { lat: 4.5353, lng: 114.7277 },

  // Africa - North
  EG: { lat: 26.8206, lng: 30.8025 },
  MA: { lat: 31.7917, lng: -7.0926 },
  DZ: { lat: 28.0339, lng: 1.6596 },
  TN: { lat: 33.8869, lng: 9.5375 },
  LY: { lat: 26.3351, lng: 17.2283 },
  SD: { lat: 12.8628, lng: 30.2176 },

  // Africa - West
  NG: { lat: 9.082, lng: 8.6753 },
  GH: { lat: 7.9465, lng: -1.0232 },
  CI: { lat: 7.54, lng: -5.5471 },
  SN: { lat: 14.4974, lng: -14.4524 },
  CM: { lat: 7.3697, lng: 12.3547 },

  // Africa - East
  KE: { lat: -0.0236, lng: 37.9062 },
  TZ: { lat: -6.369, lng: 34.8888 },
  ET: { lat: 9.145, lng: 40.4897 },
  UG: { lat: 1.3733, lng: 32.2903 },
  RW: { lat: -1.9403, lng: 29.8739 },

  // Africa - South
  ZA: { lat: -30.5595, lng: 22.9375 },
  AO: { lat: -11.2027, lng: 17.8739 },
  ZW: { lat: -19.0154, lng: 29.1549 },
  MZ: { lat: -18.6657, lng: 35.5296 },
  ZM: { lat: -13.1339, lng: 27.8493 },
  BW: { lat: -22.3285, lng: 24.6849 },
  NA: { lat: -22.9576, lng: 18.4904 },
  MU: { lat: -20.3484, lng: 57.5522 },
  MG: { lat: -18.7669, lng: 46.8691 },

  // Oceania
  AU: { lat: -25.2744, lng: 133.7751 },
  NZ: { lat: -40.9006, lng: 174.886 },
  FJ: { lat: -17.7134, lng: 178.065 },
  PG: { lat: -6.315, lng: 143.9555 },
  NC: { lat: -20.9043, lng: 165.618 },
};

export function getCountryCoordinates(countryCode: string | undefined): GeoCoordinate | null {
  if (!countryCode) return null;
  return COUNTRY_COORDINATES[countryCode.toUpperCase()] || null;
}
