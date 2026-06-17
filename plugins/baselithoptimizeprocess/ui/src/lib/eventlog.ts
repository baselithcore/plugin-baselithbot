import type { EventRecord } from '../api/types';

/**
 * Parse an event log from either a JSON array or CSV text.
 *
 * CSV is expected with a header row containing (in any order) the columns
 * `case_id, activity, timestamp` and an optional `resource`. JSON must be an
 * array of objects with the same keys. Throws on an unrecognised shape.
 */
export function parseEventLog(text: string): EventRecord[] {
  const trimmed = text.trim();
  if (!trimmed) return [];
  if (trimmed.startsWith('[') || trimmed.startsWith('{')) {
    return parseJson(trimmed);
  }
  return parseCsv(trimmed);
}

function parseJson(text: string): EventRecord[] {
  const data = JSON.parse(text);
  const rows = Array.isArray(data) ? data : [data];
  return rows.map((r, i) => coerce(r, i));
}

function parseCsv(text: string): EventRecord[] {
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  if (lines.length < 2) throw new Error('CSV needs a header row and at least one row');
  const header = splitRow(lines[0]).map((h) => h.trim().toLowerCase());
  const idx = {
    case_id: header.indexOf('case_id'),
    activity: header.indexOf('activity'),
    timestamp: header.indexOf('timestamp'),
    resource: header.indexOf('resource'),
  };
  if (idx.case_id < 0 || idx.activity < 0 || idx.timestamp < 0) {
    throw new Error('CSV header must include case_id, activity, timestamp');
  }
  return lines.slice(1).map((line) => {
    const cells = splitRow(line);
    return coerce(
      {
        case_id: cells[idx.case_id],
        activity: cells[idx.activity],
        timestamp: cells[idx.timestamp],
        resource: idx.resource >= 0 ? cells[idx.resource] : '',
      },
      0
    );
  });
}

function splitRow(line: string): string[] {
  return line.split(',').map((c) => c.trim());
}

function coerce(raw: unknown, index: number): EventRecord {
  const r = raw as Record<string, unknown>;
  const caseId = String(r.case_id ?? '').trim();
  const activity = String(r.activity ?? '').trim();
  const timestamp = String(r.timestamp ?? '').trim();
  if (!caseId || !activity || !timestamp) {
    throw new Error(`Row ${index + 1}: missing case_id/activity/timestamp`);
  }
  return {
    case_id: caseId,
    activity,
    timestamp,
    resource: r.resource ? String(r.resource) : '',
  };
}

export const SAMPLE_EVENT_LOG = `case_id,activity,timestamp
c1,Intake,2026-06-01T09:00:00Z
c1,Review,2026-06-01T09:05:00Z
c1,Ship,2026-06-01T09:12:00Z
c2,Intake,2026-06-01T10:00:00Z
c2,Review,2026-06-01T10:20:00Z
c2,Ship,2026-06-01T11:05:00Z
c3,Intake,2026-06-01T11:00:00Z
c3,Ship,2026-06-01T11:03:00Z`;
