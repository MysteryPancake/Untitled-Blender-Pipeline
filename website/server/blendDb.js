const fs = require('fs');
const os = require('os');
const path = require('path');

// Same as `_VERSION_RE` in blender/utils.py
const VERSION_RE = /_v(\d+)\.blend$/;

// Same as `folder` in blender/layers.py, in pipeline order
const LAYERS = [
	{ layer: "models", label: "Modelling" },
	{ layer: "grooms", label: "Grooming" },
	{ layer: "rigs", label: "Rigging" },
	{ layer: "materials", label: "Surfacing / UVs" },
	{ layer: "assembly", label: "Assembly / Layout" },
	{ layer: "anims", label: "Animation" },
	{ layer: "lights", label: "Lighting" }
];

// Same as `get_database()` in blender/utils.py
function expandPath(p) {
	p = p.trim();
	if (p === "~" || p.startsWith("~/") || p.startsWith("~\\")) {
		p = os.homedir() + p.slice(1);
	}
	p = p.replace(/%([^%]+)%/g, (m, name) => process.env[name] ?? m);
	p = p.replace(/\$(\w+)|\$\{(\w+)\}/g, (m, a, b) => process.env[a || b] ?? m);
	return path.resolve(p);
}

function subdirs(dir) {
	if (!fs.existsSync(dir)) return [];
	return fs.readdirSync(dir, { withFileTypes: true }).filter(e => e.isDirectory()).map(e => e.name);
}

// Versioned .blend files directly inside dir, sorted oldest to newest
function versionsIn(dir) {
	if (!fs.existsSync(dir)) return [];
	return fs.readdirSync(dir, { withFileTypes: true })
		.filter(e => e.isFile())
		.map(e => ({ match: VERSION_RE.exec(e.name), file: e.name }))
		.filter(e => e.match)
		.map(e => {
			let modified = null;
			try { modified = fs.statSync(path.join(dir, e.file)).mtime.toISOString(); } catch (err) { /* Who cares */ }
			return { version: parseInt(e.match[1], 10), file: e.file, modified };
		})
		.sort((a, b) => a.version - b.version);
}

const latest = (list) => list.length ? list[list.length - 1] : null;

// Find a folder by name, case insensitive
const findDir = (parent, name) => subdirs(parent).find(d => d.toLowerCase() === name.toLowerCase());

// Case insensitive union of names
function mergeNames(...lists) {
	const seen = new Map();
	for (const name of lists.flat()) {
		if (!seen.has(name.toLowerCase())) seen.set(name.toLowerCase(), name);
	}
	return [...seen.values()];
}

// Everything on disk for one asset
function assetState(blendDb, name) {
	const buildRoot = path.join(blendDb, "build");
	const wipRoot = path.join(blendDb, "wip");

	const buildDir = findDir(buildRoot, name);
	const builds = buildDir ? versionsIn(path.join(buildRoot, buildDir)) : [];
	const latestBuild = latest(builds);

	// Known layers first in pipeline order, then any other folder someone made
	const layers = [];
	const wipDir = findDir(wipRoot, name);
	if (wipDir) {
		const assetWip = path.join(wipRoot, wipDir);
		const folders = subdirs(assetWip);
		const known = LAYERS.map(l => l.layer);
		const ordered = [...known.filter(l => folders.includes(l)), ...folders.filter(f => !known.includes(f))];
		for (const folder of ordered) {
			const info = LAYERS.find(l => l.layer === folder);
			layers.push({ layer: folder, label: info ? info.label : folder, latest: latest(versionsIn(path.join(assetWip, folder))) });
		}
	}

	const hasWip = layers.some(l => l.latest);
	// A build is out of date when any layer was published after it was made
	const stale = !!latestBuild && layers.some(l => l.latest && l.latest.modified > latestBuild.modified);
	const status = latestBuild ? (stale ? "Needs rebuild" : "Built") : (hasWip ? "In progress" : null);

	return { builds, latestBuild, layers, stale, status };
}

module.exports = { VERSION_RE, LAYERS, expandPath, subdirs, versionsIn, latest, findDir, mergeNames, assetState };