export const API_URL = `${process.env.REACT_APP_SG_SERVER}:${process.env.REACT_APP_SG_PORT}`;

// Turn any failure into an Error with a proper message
async function request(path, options) {
	let res;
	try {
		res = await fetch(`${API_URL}${path}`, options);
	} catch (err) {
		throw new Error(`Could not reach the server at ${API_URL}`);
	}
	if (!res.ok) {
		const text = await res.text().catch(() => "");
		throw new Error(text || `Server responded with ${res.status} ${res.statusText}`);
	}
	return res;
}

export async function apiGet(path) {
	return (await request(path)).json();
}

export async function apiPost(path, body) {
	await request(path, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
}
