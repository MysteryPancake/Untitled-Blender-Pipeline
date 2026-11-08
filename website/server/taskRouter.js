const path = require('path');
const express = require('express');
const { readJson, writeJson } = require('./jsonStore.js');
const router = express.Router();
const TASK_DB = 'tasks.json';

router.post('/add', (req, res) => {
	try {
		const taskName = typeof req.body.taskName === "string" ? req.body.taskName.trim() : "";
		if (!taskName) {
			res.status(400).send("Missing task name!");
			return;
		}

		// Task description is not essential
		const taskDesc = typeof req.body.taskDesc === "string" ? req.body.taskDesc.trim() : "";

		const jsonFile = path.join(req.app.locals.WEB_DB, TASK_DB);
		const jsonData = readJson(jsonFile);
		// Add new task to array
		jsonData.push({
			name: taskName,
			description: taskDesc,
			assets: []
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
		res.json(readJson(path.join(req.app.locals.WEB_DB, TASK_DB)));
	} catch (err) {
		console.error(err);
		res.status(500).send(err.message);
	}
});

module.exports = router;