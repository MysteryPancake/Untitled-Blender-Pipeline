import { API_URL } from '../api';

function Debug() {
	return (
		<div className="m-3">
			<h1>Welcome to Hell</h1>
			<p className="mt-3">Website backend is set to {' '}
				<a href={API_URL}>{API_URL}</a>
			</p>
		</div>
	);
}

export default Debug;