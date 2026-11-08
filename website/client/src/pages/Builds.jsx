import React from 'react';
import Alert from 'react-bootstrap/Alert';
import Badge from 'react-bootstrap/Badge';
import Table from 'react-bootstrap/Table';
import Spinner from 'react-bootstrap/Spinner';

import { apiGet } from '../api';

function Version({ info }) {
	if (!info) return <span className="text-muted">None</span>;
	const when = info.modified ? new Date(info.modified).toLocaleString() : "";
	return <span title={info.file}>v{String(info.version).padStart(3, "0")}{when && <span className="text-muted"> ({when})</span>}</span>;
}

const STATUS_COLORS = { "Built": "success", "Needs rebuild": "warning", "In progress": "primary" };

function StatusBadge({ status }) {
	if (!status) return <span className="text-muted">Nothing published</span>;
	return <Badge bg={STATUS_COLORS[status] || "secondary"}>{status}</Badge>;
}

class Builds extends React.Component {
	constructor(props) {
		super(props);
		this.state = {};
	}

	componentDidMount() {
		apiGet('/builds/get')
			.then((builds) => this.setState({ builds }))
			.catch((err) => this.setState({ error: err.message }));
	}

	render() {
		const { builds, error } = this.state;
		return (
			<div className="m-3">
				<h2 className="mb-2">Builds</h2>
				{
					builds
					? (
						builds.length
						? <Table bordered>
							<thead style={{ backgroundColor: "#EEE" }}>
								<tr>
									<th>Asset</th>
									<th>Status</th>
									<th>Latest Build</th>
									<th>Work in Progress (latest per layer)</th>
								</tr>
							</thead>
							<tbody>
								{
									builds.map((b) => (
										<tr key={b.asset}>
											<td>{b.asset}</td>
											<td><StatusBadge status={b.status} /></td>
											<td><Version info={b.latestBuild} /></td>
											<td>
												{
													b.layers.length
													? b.layers.map((l) => (
														<div key={l.layer}>
															<span className="fw-bold">{l.label}</span>: <Version info={l.latest} />
														</div>
													))
													: <span className="text-muted">No layers</span>
												}
											</td>
										</tr>
									))
								}
							</tbody>
						</Table>
						: <p className="text-muted">No assets or builds yet.</p>
					)
					: (
						error
						? <Alert variant="danger">{error}</Alert>
						: <Spinner animation="border" />
					)
				}
			</div>
		);
	}
}

export default Builds;
