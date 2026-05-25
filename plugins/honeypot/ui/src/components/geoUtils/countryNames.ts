/**
 * Country Names - Full name mapping for country codes
 */

export const COUNTRY_NAMES: Record<string, string> = {
  US: 'United States',
  CN: 'China',
  RU: 'Russia',
  GB: 'United Kingdom',
  DE: 'Germany',
  FR: 'France',
  IT: 'Italy',
  ES: 'Spain',
  BR: 'Brazil',
  IN: 'India',
  JP: 'Japan',
  KR: 'South Korea',
  AU: 'Australia',
  CA: 'Canada',
  NL: 'Netherlands',
  SE: 'Sweden',
  NO: 'Norway',
  FI: 'Finland',
  PL: 'Poland',
  UA: 'Ukraine',
  TR: 'Turkey',
  IR: 'Iran',
  SA: 'Saudi Arabia',
  AE: 'UAE',
  ID: 'Indonesia',
  VN: 'Vietnam',
  TH: 'Thailand',
  MY: 'Malaysia',
  SG: 'Singapore',
  MX: 'Mexico',
  AR: 'Argentina',
  CO: 'Colombia',
  CL: 'Chile',
  VE: 'Venezuela',
  ZA: 'South Africa',
  EG: 'Egypt',
  NG: 'Nigeria',
  KE: 'Kenya',
  MA: 'Morocco',
  LAN: 'Local Network',
  UNK: 'Unknown',
};

/**
 * Get full country name from code
 */
export function getCountryName(countryCode: string | undefined): string {
  if (!countryCode) return 'Unknown';
  return COUNTRY_NAMES[countryCode.toUpperCase()] || countryCode;
}
