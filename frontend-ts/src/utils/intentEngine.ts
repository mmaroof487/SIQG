export type IntentClass = 'SCHEMA' | 'QUERY';

const SCHEMA_REGEX = /\b(schemas?|tables?|columns?|foreign keys?|relation(s|ships?)?|realtions?|structures?|connected to|datatypes?)\b/i;

/**
 * Lightweight heuristic intent classifier.
 * 1. Checks if prompt references schema concepts
 * 2. Else treat as query
 */
export function classifyIntent(prompt: string): IntentClass | null {
    if (!prompt || prompt.trim() === '') {
        return null;
    }

    if (SCHEMA_REGEX.test(prompt)) {
        return 'SCHEMA';
    }

    return 'QUERY';
}
