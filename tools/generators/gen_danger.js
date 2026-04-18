#!/usr/bin/env node
// Generate build/danger-plugin-no-animal-violence/src/index.ts from rules.yaml

"use strict";

const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const RULES_YAML = path.join(REPO_ROOT, "rules.yaml");
const OUTPUT_PATH = path.join(
	REPO_ROOT,
	"build",
	"danger-plugin-no-animal-violence",
	"src",
	"index.ts",
);

function loadRules() {
	const content = fs.readFileSync(RULES_YAML, "utf8");
	const data = yaml.load(content);
	return data.rules;
}

function buildPatternEntries(rules) {
	return rules.map((r) => {
		const wb = r.word_boundary !== false;
		const raw = wb ? `\\b${r.regex}\\b` : r.regex;
		const altsJson = JSON.stringify(r.alternatives);
		return `  { regex: new RegExp(${JSON.stringify(raw)}, "gi"), phrase: ${JSON.stringify(r.terms[0])}, alternatives: ${altsJson} },`;
	}).join("\n");
}

const STATIC_HEADER = `// AUTO-GENERATED from Open-Paws/no-animal-violence. Do not edit directly.
import { DangerDSLType } from "danger";

declare const danger: DangerDSLType;
declare function warn(message: string): void;
declare function message(message: string): void;

interface NoAnimalViolenceOptions {
  severity?: "warn" | "message";
}

interface Pattern {
  regex: RegExp;
  phrase: string;
  alternatives: string[];
}

const PATTERNS: Pattern[] = [
`;

const STATIC_FOOTER = `];

export default async function noAnimalViolence(options: NoAnimalViolenceOptions = {}) {
  const report = options.severity === "message" ? message : warn;
  const modifiedFiles = danger.git.modified_files.concat(danger.git.created_files);

  const diffs = await Promise.all(modifiedFiles.map(f => danger.git.diffForFile(f)));
  for (let i = 0; i < modifiedFiles.length; i++) {
    const result = diffs[i];
    if (!result) continue;
    const file = modifiedFiles[i];
    const added = result.added;

    for (const pattern of PATTERNS) {
      if (pattern.regex.test(added)) {
        report(
          \`**\${file}**: Found "\${pattern.phrase}". \` +
          \`Consider: \${pattern.alternatives.map(a => \`"\${a}"\`).join(" or ")}. \` +
          \`[Why?](https://doi.org/10.1007/s43681-023-00380-w)\`
        );
        pattern.regex.lastIndex = 0;
      }
    }
  }
}
`;

function main() {
	const rules = loadRules();
	const patternEntries = buildPatternEntries(rules);
	const output = STATIC_HEADER + patternEntries + "\n" + STATIC_FOOTER;

	const outDir = path.dirname(OUTPUT_PATH);
	fs.mkdirSync(outDir, { recursive: true });
	fs.writeFileSync(OUTPUT_PATH, output, "utf8");
	console.log(`Danger: wrote ${OUTPUT_PATH}`);
}

main();
