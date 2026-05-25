/**
 * Honeypot Dashboard Type Definitions
 *
 * This module re-exports all types for backward compatibility.
 * Types are organized into focused domain modules:
 * - events: Core event and session types
 * - discovery: Botnet detection and threat intelligence
 * - pentest: Pentesting and vulnerability types
 * - reports: Security report types
 * - visualization: Graph and visualization types
 */

// Re-export all types from domain modules
export * from './types/events';
export * from './types/discovery';
export * from './types/pentest';
export * from './types/reports';
export * from './types/visualization';
