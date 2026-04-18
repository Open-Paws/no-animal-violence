#!/usr/bin/env node
// Generate build/eslint-plugin-no-animal-violence/lib/rules/no-violent-language.js
// from rules.yaml

"use strict";

const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const RULES_YAML = path.join(REPO_ROOT, "rules.yaml");
const OUTPUT_PATH = path.join(
	REPO_ROOT,
	"build",
	"eslint-plugin-no-animal-violence",
	"lib",
	"rules",
	"no-violent-language.js",
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
		const patternForLiteral = raw.replace(/\//g, "\\/");
		const phrase = r.terms[0].replace(/\\/g, "\\\\").replace(/"/g, '\\"');
		const alt = r.alternatives[0].replace(/\\/g, "\\\\").replace(/"/g, '\\"');
		return `\t{ pattern: /${patternForLiteral}/gi, phrase: "${phrase}", alt: "${alt}" },`;
	}).join("\n");
}

// Static boilerplate lines for the generated ESLint rule file.
// Stored as an array to avoid complex escaping in template literals.
const STATIC_BOILERPLATE_LINES = [
	"",
	"function checkText(context, node, text, offsetCalculator) {",
	"\tfor (const { pattern, phrase, alt } of PATTERNS) {",
	"\t\tpattern.lastIndex = 0;",
	"\t\tlet match;",
	"\t\twhile ((match = pattern.exec(text)) !== null) {",
	"\t\t\tconst loc = offsetCalculator ? offsetCalculator(match.index) : node.loc.start;",
	"\t\t\tcontext.report({",
	"\t\t\t\tnode,",
	"\t\t\t\tloc,",
	'\t\t\t\tmessageId: "avoidViolentAnimalLanguage",',
	"\t\t\t\tdata: {",
	"\t\t\t\t\tphrase: match[0],",
	"\t\t\t\t\talternatives: alt,",
	"\t\t\t\t},",
	"\t\t\t});",
	"\t\t}",
	"\t}",
	"}",
	"",
	"module.exports = {",
	"\tmeta: {",
	'\t\ttype: "suggestion",',
	"\t\tdocs: {",
	'\t\t\tdescription: "Detect and discourage language normalizing violence toward animals in comments and strings",',
	'\t\t\tcategory: "Best Practices",',
	"\t\t\trecommended: true,",
	'\t\t\turl: "https://github.com/Open-Paws/eslint-plugin-no-animal-violence#no-violent-language",',
	"\t\t},",
	"\t\tmessages: {",
	'\t\t\tavoidViolentAnimalLanguage: \'Avoid "{{phrase}}". Consider: {{alternatives}}\',',
	"\t\t},",
	"\t\tschema: [],",
	"\t},",
	"\tcreate(context) {",
	"\t\tconst sourceCode = context.getSourceCode ? context.getSourceCode() : context.sourceCode;",
	"\t\treturn {",
	"\t\t\tLiteral(node) {",
	'\t\t\t\tif (typeof node.value === "string") {',
	"\t\t\t\t\tcheckText(context, node, node.value);",
	"\t\t\t\t}",
	"\t\t\t},",
	"\t\t\tTemplateLiteral(node) {",
	"\t\t\t\tnode.quasis.forEach((quasi) => {",
	"\t\t\t\t\tcheckText(context, quasi, quasi.value.raw);",
	"\t\t\t\t});",
	"\t\t\t},",
	"\t\t\tProgram() {",
	"\t\t\t\tconst comments = sourceCode.getAllComments ? sourceCode.getAllComments() : sourceCode.comments || [];",
	"\t\t\t\tcomments.forEach((comment) => {",
	"\t\t\t\t\tcheckText(context, comment, comment.value, (matchIndex) => {",
	'\t\t\t\t\t\tconst lines = comment.value.substring(0, matchIndex).split("\\n");',
	"\t\t\t\t\t\tconst lineOffset = lines.length - 1;",
	"\t\t\t\t\t\tconst columnOffset =",
	"\t\t\t\t\t\t\tlineOffset === 0 ? matchIndex + 2 : lines[lines.length - 1].length;",
	"\t\t\t\t\t\treturn {",
	"\t\t\t\t\t\t\tline: comment.loc.start.line + lineOffset,",
	"\t\t\t\t\t\t\tcolumn: lineOffset === 0 ? comment.loc.start.column + columnOffset : columnOffset,",
	"\t\t\t\t\t\t};",
	"\t\t\t\t\t});",
	"\t\t\t\t});",
	"\t\t\t},",
	"\t\t};",
	"\t},",
	"};",
	"",
];

function main() {
	const rules = loadRules();
	const patternEntries = buildPatternEntries(rules);

	const output = [
		"// AUTO-GENERATED from Open-Paws/no-animal-violence. Do not edit directly.",
		'"use strict";',
		"",
		"const PATTERNS = [",
		patternEntries,
		"];",
		...STATIC_BOILERPLATE_LINES,
	].join("\n");

	const outDir = path.dirname(OUTPUT_PATH);
	fs.mkdirSync(outDir, { recursive: true });
	fs.writeFileSync(OUTPUT_PATH, output, "utf8");
	console.log(`ESLint: wrote ${OUTPUT_PATH}`);
}

main();
