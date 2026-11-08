const fs = require('fs');
const path = require('path');
const express = require('express');
const { readJson, writeJson } = require('./jsonStore.js');
const { subdirs, mergeNames, assetState } = require('./blendDb.js');
const router = express.Router();
const ASSET_DB = 'assets.json';

router.post('/add', (req, res) => {
	try {
		// Prevent folder name issues
		const assetName = typeof req.body.assetName === 'string' ? req.body.assetName.trim() : "";
		if (!assetName) {
			res.status(400).send("Missing asset name!");
			return;
		}
		if (/[^\w\- ]/.test(assetName)) {
			res.status(400).send("Asset name contains characters not allowed in filenames!");
			return;
		} else if (assetName.length > 255) {
			res.status(400).send("Asset name is too long! Keep it under 256 characters.");
			return;
		}

		const assetType = typeof req.body.assetType === 'string' ? req.body.assetType.trim() : "";
		if (!assetType) {
			res.status(400).send("Missing asset type!");
			return;
		}

		// Asset description is optional
		const assetDesc = typeof req.body.assetDesc === 'string' ? req.body.assetDesc.trim() : "";

		const jsonFile = path.join(req.app.locals.WEB_DB, ASSET_DB);
		const jsonData = readJson(jsonFile);

		// Names are case insensitive since "Rock" and "rock" are the same on Windows
		const lowerName = assetName.toLowerCase();

		// Don't override existing data
		if (jsonData.some(e => String(e.name).toLowerCase() === lowerName)) {
			res.status(400).send("Asset name already exists!");
			return;
		}

		// Create the master/wip/asset subfolder first, so if SG_DATABASE is broken the JSON isn't changed
		const wipFolder = path.join(req.app.locals.BLEND_DB, "wip", assetName);
		try {
			fs.mkdirSync(wipFolder, { recursive: true });
		} catch (err) {
			console.error(`Could not create ${wipFolder}:`, err);
			res.status(500).send(`Could not create the asset folder: ${err.message}`);
			return;
		}

		// Add new asset to array
		jsonData.push({
			name: assetName,
			type: assetType,
			description: assetDesc,
			thumbnail: "",
			status: "TODO"
		});
		writeJson(jsonFile, jsonData);

		res.sendStatus(200);
	} catch (err) {
		console.error(err);
		res.status(500).send(err.message);
	}
});

router.get('/get', (req, res) => {
	try {
		const registered = readJson(path.join(req.app.locals.WEB_DB, ASSET_DB));
		const blendDb = req.app.locals.BLEND_DB;

		// Show progress from the Blender folders
		const assets = registered.map(asset => {
			const { status } = assetState(blendDb, asset.name);
			return { ...asset, status: asset.status === "TODO" && status ? status : asset.status };
		});

		// Assets published from Blender that were never added on the website
		const known = registered.map(a => a.name);
		const extra = mergeNames(subdirs(path.join(blendDb, "wip")), subdirs(path.join(blendDb, "build")))
			.filter(n => !known.some(k => String(k).toLowerCase() === n.toLowerCase()));
		for (const name of extra) {
			assets.push({ name, type: "", description: "", thumbnail: "", status: assetState(blendDb, name).status || "Untracked", untracked: true });
		}

		res.json(assets);
	} catch (err) {
		console.error(err);
		res.status(500).send(err.message);
	}
});

module.exports = router;