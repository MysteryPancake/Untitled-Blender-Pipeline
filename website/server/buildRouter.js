const path = require('path');
const express = require('express');
const { readJson } = require('./jsonStore.js');
const { subdirs, mergeNames, assetState } = require('./blendDb.js');
const router = express.Router();

router.get('/get', (req, res) => {
	try {
		const { WEB_DB, BLEND_DB } = req.app.locals;
		const registered = readJson(path.join(WEB_DB, 'assets.json')).map(a => a.name);
		
		// Include assets that only exist in Blender's folders, published from the addon
		const names = mergeNames(registered, subdirs(path.join(BLEND_DB, "build")), subdirs(path.join(BLEND_DB, "wip")));

		res.json(names.map(name => {
			const { builds, latestBuild, layers, stale, status } = assetState(BLEND_DB, name);
			return { asset: name, status, stale, latestBuild, builds, layers };
		}));
	} catch (err) {
		console.error(err);
		res.status(500).send(err.message);
	}
});

module.exports = router;