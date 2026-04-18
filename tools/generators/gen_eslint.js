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

function buildMapEntries(rules) {
	return rules
		.map((r) => {
			const term = r.terms[0];
			const alt = r.alternatives[0];
			return `\t[${JSON.stringify(term)}, ${JSON.stringify(alt)}],`;
		})
		.join("\n");
}

// Static boilerplate lines for the generated ESLint rule file.
// Stored as an array to avoid complex escaping in template literals.
const STATIC_BOILERPLATE_LINES = [
	"",
	"function buildPattern() {",
	"\tconst escaped = Array.from(VIOLENT_ANIMAL_PHRASES.keys()).map((phrase) =>",
	'\t\tphrase.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\\\$&"),',
	"\t);",
	"\tescaped.sort((a, b) => b.length - a.length);",
	'\treturn new RegExp(`\\\\b(?:${escaped.join("|")})\\\\b`, "gi");',
	"}",
	"",
	"const PATTERN = buildPattern();",
	"",
	"function checkText(context, node, text, offsetCalculator) {",
	"\tPATTERN.lastIndex = 0;",
	"\tlet match = PATTERN.exec(text);",
	"\twhile (match !== null) {",
	"\t\tconst phrase = match[0].toLowerCase();",
	"\t\tconst alternative = VIOLENT_ANIMAL_PHRASES.get(phrase);",
	"\t\tif (alternative) {",
	"\t\t\tconst loc = offsetCalculator ? offsetCalculator(match.index) : node.loc.start;",
	"\t\t\tcontext.report({",
	"\t\t\t\tnode,",
	"\t\t\t\tloc,",
	'\t\t\t\tmessageId: "avoidViolentAnimalLanguage",',
	"\t\t\t\tdata: {",
	"\t\t\t\t\tphrase: match[0],",
	"\t\t\t\t\talternatives: alternative,",
	"\t\t\t\t},",
	"\t\t\t});",
	"\t\t}",
	"\t\tmatch = PATTERN.exec(text);",
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
	"\t\t\t\t\t\t\tlineOffset === 0 ? matchIndex + (comment.type === \"Block\" ? 2 : 2) : lines[lines.length - 1].length;",
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
	const mapEntries = buildMapEntries(rules);

	const output = [
		"// AUTO-GENERATED from Open-Paws/no-animal-violence. Do not edit directly.",
		'"use strict";',
		"",
		"const VIOLENT_ANIMAL_PHRASES = new Map([",
		mapEntries,
		"]);",
		...STATIC_BOILERPLATE_LINES,
	].join("\n");

	const outDir = path.dirname(OUTPUT_PATH);
	fs.mkdirSync(outDir, { recursive: true });
	fs.writeFileSync(OUTPUT_PATH, output, "utf8");
	console.log(`ESLint: wrote ${OUTPUT_PATH}`);
}

main();
