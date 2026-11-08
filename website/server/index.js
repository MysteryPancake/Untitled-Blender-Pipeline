const express = require('express');
const cors = require('cors');
const app = express();

const taskRouter = require('./taskRouter.js');
const assetRouter = require('./assetRouter.js');
const buildRouter = require('./buildRouter.js');
const { expandPath } = require('./blendDb.js');

function fail(message) {
	console.error(message);
	process.exit(1);
}

const PORT = process.env.REACT_APP_SG_PORT;
if (!PORT) {
	fail("Missing environment variable REACT_APP_SG_PORT!");
}

// Main folder for website database files, using JSON for the moment
const WEB_DB = (process.env.SG_WEB_DB || "").trim();
if (!WEB_DB) {
	fail("Missing environment variable SG_WEB_DB!");
}
app.locals.WEB_DB = expandPath(WEB_DB);
console.log(`Website database set to ${app.locals.WEB_DB}`);

// Main folder for Blender files, shared with the Blender addon through the same environment variable
const BLEND_DB = (process.env.SG_DATABASE || "").trim();
if (!BLEND_DB) {
	fail("Missing environment variable SG_DATABASE!");
}
app.locals.BLEND_DB = expandPath(BLEND_DB);
console.log(`Blender database set to ${app.locals.BLEND_DB}`);

// Local only by default, set SG_HOST to 0.0.0.0 to use the network
const HOST = (process.env.SG_HOST || "").trim() || "127.0.0.1";

// Let the frontend mess with the backend. By default only localhost origins are accepted
const allowedOrigins = (process.env.SG_CORS_ORIGIN || "").split(',').map(s => s.trim()).filter(Boolean);
app.use(cors({
	origin: (origin, callback) => {
		if (!origin) return callback(null, true); // same-origin or non-browser clients
		if (allowedOrigins.length) return callback(null, allowedOrigins.includes(origin));
		callback(null, /^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$/.test(origin));
	}
}));
app.use(express.json());

app.use('/tasks', taskRouter);
app.use('/assets', assetRouter);
app.use('/builds', buildRouter);

app.get('/', (req, res) => {
	res.send('Backend is working!');
});

app.listen(PORT, HOST, () => console.log(`Listening on ${HOST}:${PORT}`));