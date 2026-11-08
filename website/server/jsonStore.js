const fs = require('fs');
const path = require('path');

// Read a JSON array from disk with some safety checks to prevent errors
function readJson(file) {
	if (!fs.existsSync(file)) {
		return [];
	}
	try {
		return JSON.parse(fs.readFileSync(file, 'utf8'));
	} catch (err) {
		throw new Error(`Database file ${path.basename(file)} is corrupt: ${err.message}`);
	}
}

// Write to a temp file then replace the real one in case it crashes
function writeJson(file, data) {
	fs.mkdirSync(path.dirname(file), { recursive: true });
	const tmp = `${file}.${process.pid}.tmp`;
	fs.writeFileSync(tmp, JSON.stringify(data));
	fs.renameSync(tmp, file);
}

module.exports = { readJson, writeJson };
