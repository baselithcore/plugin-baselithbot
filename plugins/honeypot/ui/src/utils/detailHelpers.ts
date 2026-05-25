import { getCountryFlag } from '../components/geoUtils';
import { AttackEvent } from '../components/types';

// Get geo display info
export const getGeoDisplay = (event: AttackEvent) => {
  const geo = event.geo;
  const countryCode = geo?.country_code;

  // Handle special country codes
  if (countryCode === 'LAN') {
    return {
      flag: '🏠',
      location: 'Local Network',
      detail: 'Private/Local IP Address',
      isLocal: true,
    };
  }

  if (countryCode === 'UNK' || !countryCode) {
    return {
      flag: '❓',
      location: 'Unknown Location',
      detail: 'Geo lookup unavailable',
      isLocal: false,
    };
  }

  return {
    flag: getCountryFlag(countryCode),
    location: geo?.city ? `${geo.city}, ${geo.country}` : geo?.country || 'Unknown',
    detail: geo?.country || '',
    isLocal: false,
  };
};

export const getPayloadContent = (event: AttackEvent) => {
  if (event.command) {
    return { type: 'command', content: event.command };
  }
  if (event.http_path) {
    return {
      type: 'http',
      content: `${event.http_method || 'GET'} ${event.http_path}`,
      body: event.http_body,
    };
  }
  if (event.raw_data) {
    return { type: 'raw', content: event.raw_data };
  }
  return { type: 'none', content: 'No payload captured' };
};
