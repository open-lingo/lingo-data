#!/usr/bin/env node
/**
 * validate.mjs — schema check for the Open Lingo data repo.
 *
 * Verifies that every data/<lang>/*.jsonl dictionary and every
 * data/<lang>/frequency.csv conforms to schema/. Exits non-zero on any error.
 *
 * Usage: node validate.mjs
 *
 * MIT-licensed (see LICENSE-CODE). The data it checks is CC BY 4.0 (see LICENSE).
 */
import { readdirSync, readFileSync, existsSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const DATA = path.join(ROOT, "data");

const REQUIRED_DICT = ["lemma", "lang", "source"];
const KNOWN_SOURCES = new Set([
  "open-lingo-curriculum",
  "open-lingo-curriculum-order",
  "jlpt-n5",
]);

let errors = 0;
let entries = 0;
const err = (m) => {
  errors++;
  console.error("  ERROR: " + m);
};

function parseCsvLine(line) {
  const out = [];
  let cur = "";
  let q = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (q) {
      if (c === '"' && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else if (c === '"') q = false;
      else cur += c;
    } else if (c === '"') q = true;
    else if (c === ",") {
      out.push(cur);
      cur = "";
    } else cur += c;
  }
  out.push(cur);
  return out;
}

function checkDict(file, lang) {
  const lines = readFileSync(file, "utf8").split("\n");
  lines.forEach((line, idx) => {
    if (!line.trim()) return;
    let o;
    try {
      o = JSON.parse(line);
    } catch (e) {
      return err(`${file}:${idx + 1} not valid JSON: ${e.message}`);
    }
    entries++;
    for (const f of REQUIRED_DICT) {
      if (o[f] === undefined || o[f] === "")
        err(`${file}:${idx + 1} missing required field "${f}"`);
    }
    if (!o.gloss && !(Array.isArray(o.senses) && o.senses.length))
      err(`${file}:${idx + 1} needs either "gloss" or non-empty "senses"`);
    if (o.lang && lang && o.lang !== lang)
      err(`${file}:${idx + 1} lang "${o.lang}" != dir "${lang}"`);
    if (o.source && !KNOWN_SOURCES.has(o.source))
      err(`${file}:${idx + 1} source "${o.source}" not in schema/source-tags.md`);
  });
}

function checkFreq(file, lang) {
  const lines = readFileSync(file, "utf8").split("\n").filter((l) => l.trim());
  if (!lines.length) return err(`${file} empty`);
  const header = parseCsvLine(lines[0]);
  if (header[0] !== "rank" || !header.includes("lemma") || !header.includes("source"))
    err(`${file} header must include rank, lemma, source (got ${header.join(",")})`);
  const langCol = header.indexOf("lang");
  const srcCol = header.indexOf("source");
  for (let i = 1; i < lines.length; i++) {
    const cells = parseCsvLine(lines[i]);
    if (cells.length !== header.length)
      err(`${file}:${i + 1} expected ${header.length} cols, got ${cells.length}`);
    if (!/^\d+$/.test(cells[0]))
      err(`${file}:${i + 1} rank "${cells[0]}" not a positive integer`);
    if (langCol >= 0 && lang && cells[langCol] !== lang)
      err(`${file}:${i + 1} lang "${cells[langCol]}" != dir "${lang}"`);
    if (srcCol >= 0 && !KNOWN_SOURCES.has(cells[srcCol]))
      err(`${file}:${i + 1} source "${cells[srcCol]}" not in schema/source-tags.md`);
  }
}

if (!existsSync(DATA)) {
  console.error("no data/ directory");
  process.exit(1);
}

for (const lang of readdirSync(DATA)) {
  const dir = path.join(DATA, lang);
  if (!statSync(dir).isDirectory()) continue;
  for (const f of readdirSync(dir)) {
    const full = path.join(dir, f);
    if (f.endsWith(".jsonl")) {
      console.log(`dict  ${lang}/${f}`);
      checkDict(full, lang);
    } else if (f === "frequency.csv") {
      console.log(`freq  ${lang}/${f}`);
      checkFreq(full, lang);
    }
  }
}

console.log(`\nchecked ${entries} dictionary entries`);
if (errors) {
  console.error(`FAILED with ${errors} error(s)`);
  process.exit(1);
}
console.log("OK — all data conforms to schema/");
