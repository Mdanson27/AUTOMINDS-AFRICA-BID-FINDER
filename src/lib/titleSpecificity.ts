import type { Bid } from "@/lib/types";

const GENERIC_TITLES = [
  /^request for quotations?(?:\/proposals?)?$/i,
  /^request for proposals?$/i,
  /^request for bids?$/i,
  /^request for quotation notice$/i,
  /^invitation to bid$/i,
  /^invitation for bids$/i,
  /^invitation to tender$/i,
  /^open domestic(?: bidding)?$/i,
  /^open international(?: bidding)?$/i,
  /^micro procurement$/i,
  /^direct procurement$/i,
  /^restricted bidding$/i,
  /^expressions? of interest$/i,
  /^procurement notice$/i,
  /^bid notice$/i,
  /^tender notice$/i,
  /^tender$/i,
  /^bidding$/i,
  /^bids?$/i,
  /^proposals?$/i,
  /^quotations?$/i,
  /^rfp$/i,
  /^rfq$/i,
  /^prequalification$/i,
  /^supplier prequalification$/i,
  /^supplies$/i,
  /^works$/i,
  /^services$/i,
  /^consultancy services$/i,
  /^non consultancy services$/i,
];

const TITLE_METADATA_KEYS = new Set([
  "subject of procurement",
  "procurement subject",
  "subject",
  "tender title",
  "bid title",
  "title of procurement",
  "description of procurement",
  "procurement description",
  "assignment title",
  "assignment",
  "scope of procurement",
  "scope of work",
  "description of goods",
  "description of works",
  "description of services",
  "lot description",
  "project title",
]);

const METHOD_PREFIX = /^(?:request\s+for\s+(?:quotations?(?:\/proposals?)?|proposals?|bids?)|invitation\s+(?:to\s+bid|to\s+tender|for\s+bids?)|open\s+(?:domestic|international)(?:\s+bidding)?|micro\s+procurement|direct\s+procurement|restricted\s+bidding|expressions?\s+of\s+interest|procurement\s+notice|bid\s+notice|tender\s+notice)\s*(?:[-–—:|/]\s*)+/i;
const SPECIFIC_PHRASE = /\b(?:procurement|supply|provision|construction|rehabilitation|maintenance|development|acquisition|purchase|installation|upgrade|implementation|design|consultancy\s+services|non[- ]consultancy\s+services|framework\s+contract|prequalification)\s+(?:of|for)\s+[^\n\r.;]{8,260}/i;

function clean(value: unknown) {
  return String(value || "").replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim();
}

function key(value: unknown) {
  return clean(value).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

export function isGenericProcurementTitle(value: unknown) {
  const title = clean(value).toLowerCase().replace(/^[ .:\-–—]+|[ .:\-–—]+$/g, "");
  if (!title) return true;
  return GENERIC_TITLES.some((pattern) => pattern.test(title));
}

function stripMethodPrefix(value: unknown) {
  const text = clean(value);
  const stripped = text.replace(METHOD_PREFIX, "").replace(/^[ \-–—:|/]+|[ \-–—:|/]+$/g, "");
  return stripped && stripped !== text && !isGenericProcurementTitle(stripped) ? stripped : text;
}

function specificPhrase(value: unknown) {
  const match = clean(value).match(SPECIFIC_PHRASE);
  if (!match) return "";
  const candidate = clean(match[0]).replace(/^[ \-–—:|/]+|[ \-–—:|/]+$/g, "");
  return candidate.length >= 16 && !isGenericProcurementTitle(candidate) ? candidate : "";
}

export function resolveSpecificBidTitle(bid: Bid): string | null {
  if (bid.displayEligible === false && bid.titleSpecificity === "unresolved") return null;

  // The publisher's explicit Subject of Procurement (or equivalent field)
  // always outranks method/category/listing labels for every source.
  for (const [rawKey, rawValue] of Object.entries(bid.sourceMetadata || {})) {
    if (!TITLE_METADATA_KEYS.has(key(rawKey))) continue;
    const candidate = stripMethodPrefix(rawValue);
    if (candidate && !isGenericProcurementTitle(candidate)) return candidate.slice(0, 320);
  }

  const current = stripMethodPrefix(bid.title);
  if (current && !isGenericProcurementTitle(current)) return current.slice(0, 320);

  const fromDescription = specificPhrase(bid.description);
  if (fromDescription) return fromDescription.slice(0, 320);

  for (const [rawKey, rawValue] of Object.entries(bid.sourceMetadata || {})) {
    const normalized = key(rawKey);
    if (!["subject", "title", "description", "scope", "assignment", "goods", "works", "services", "project"].some((token) => normalized.includes(token))) continue;
    const candidate = stripMethodPrefix(rawValue);
    if (candidate.length >= 16 && !isGenericProcurementTitle(candidate)) return candidate.slice(0, 320);
    const phrase = specificPhrase(rawValue);
    if (phrase) return phrase.slice(0, 320);
  }

  return null;
}
