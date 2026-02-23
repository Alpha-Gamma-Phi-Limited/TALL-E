/**
 * @typedef {Object} PageContext
 * @property {string} url
 * @property {string} title
 * @property {string} capturedAt
 *
 * @typedef {Object} LookupResponse
 * @property {{name: string, detectedFromUrl: string}} store
 * @property {{name: string, brand: string, size: string, matchedBy: string}} product
 * @property {{cents: number, display: string, capturedAt: string}} currentPrice
 * @property {{date: string, priceCents: number}[]} history
 * @property {{store: string, priceCents: number, display: string}[]} compare
 */

export {};
