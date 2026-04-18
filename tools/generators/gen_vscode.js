#!/usr/bin/env node
// Generate build/vscode-no-animal-violence/extension.js from rules.yaml

"use strict";

const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const RULES_YAML = path.join(REPO_ROOT, "rules.yaml");
const OUTPUT_PATH = path.join(
	REPO_ROOT,
	"build",
	"vscode-no-animal-violence",
	"extension.js",
);

function loadRules() {
	const content = fs.readFileSync(RULES_YAML, "utf8");
	const data = yaml.load(content);
	return data.rules;
}

function buildPatternEntries(rules) {
	return rules.map((r) => {
		const regex = r.regex;
		const wb = r.word_boundary;
		const pattern = wb ? `\\\\b${regex}\\\\b` : regex;
		const phrase = r.terms[0];
		const suggest = r.alternatives[0];
		return `\t\t{\n\t\t\tpattern: /${pattern}/gi,\n\t\t\tphrase: "${phrase}",\n\t\t\tsuggest: "${suggest}",\n\t\t},`;
	}).join("\n");
}

const STATIC_HEADER = `// AUTO-GENERATED from Open-Paws/no-animal-violence. Do not edit directly.
"use strict";

const vscode = require("vscode");

const PATTERNS = [
`;

const STATIC_FOOTER = `
];

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
	const collection = vscode.languages.createDiagnosticCollection("no-animal-violence");

	function analyzeDocument(document) {
		const diagnostics = [];
		const text = document.getText();

		for (const { pattern, phrase, suggest } of PATTERNS) {
			pattern.lastIndex = 0;
			let match;
			while ((match = pattern.exec(text)) !== null) {
				const startPos = document.positionAt(match.index);
				const endPos = document.positionAt(match.index + match[0].length);
				const range = new vscode.Range(startPos, endPos);
				const diagnostic = new vscode.Diagnostic(
					range,
					\`Avoid "\${phrase}". Consider: "\${suggest}"\`,
					vscode.DiagnosticSeverity.Warning,
				);
				diagnostic.source = "no-animal-violence";
				diagnostics.push(diagnostic);
			}
		}

		collection.set(document.uri, diagnostics);
	}

	if (vscode.window.activeTextEditor) {
		analyzeDocument(vscode.window.activeTextEditor.document);
	}

	context.subscriptions.push(
		vscode.workspace.onDidOpenTextDocument(analyzeDocument),
		vscode.workspace.onDidChangeTextDocument((e) => analyzeDocument(e.document)),
		vscode.workspace.onDidCloseTextDocument((doc) => collection.delete(doc.uri)),
		collection,
	);
}

function deactivate() {}

module.exports = { activate, deactivate };
`;

function main() {
	const rules = loadRules();
	const patternEntries = buildPatternEntries(rules);
	const output = STATIC_HEADER + patternEntries + STATIC_FOOTER;

	const outDir = path.dirname(OUTPUT_PATH);
	fs.mkdirSync(outDir, { recursive: true });
	fs.writeFileSync(OUTPUT_PATH, output, "utf8");
	console.log(`VS Code: wrote ${OUTPUT_PATH}`);
}

main();
