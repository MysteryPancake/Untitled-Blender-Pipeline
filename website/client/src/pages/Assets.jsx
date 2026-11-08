import React from 'react';
import Alert from 'react-bootstrap/Alert';
import Table from 'react-bootstrap/Table';
import Spinner from 'react-bootstrap/Spinner';

import AddAsset from '../components/AddAsset';
import { apiGet } from '../api';

class Assets extends React.Component {
	constructor(props) {
		super(props);
		this.state = {};
	}

	load = () => {
		apiGet('/assets/get')
			.then((json) => this.setState({ assets: json, error: undefined }))
			.catch((err) => this.setState({ error: err.message }));
	}

	componentDidMount() {
		this.load();
	}

	render() {
		return (
			<div className="m-3">
				<div className="mb-2">
					<h2 className="d-inline-block">Assets</h2>
					<AddAsset className="float-end" onAdded={this.load}>+ Add Asset</AddAsset>
				</div>
				{
					this.state.assets
					? <Table bordered>
						<thead style={{ backgroundColor: "#EEE" }}>
							<tr>
								<th>Thumbnail</th>
								<th>Asset Name</th>
								<th>Type</th>
								<th>Description</th>
								<th>Status</th>
							</tr>
						</thead>
						<tbody>
							{
								this.state.assets.map((asset, i) => {
									return <tr key={i}>
										<td>{asset.thumbnail}</td>
										<td>{asset.name}{asset.untracked && <span className="text-muted" title="Published from Blender but not added on the website. Use + Add Asset with this name to register it."> (Blender only)</span>}</td>
										<td>{asset.type}</td>
										<td>{asset.description}</td>
										<td>{asset.status}</td>
									</tr>
								})
							}
						</tbody>
					</Table>
					: (
						this.state.error
						? <Alert variant="danger">{this.state.error}</Alert>
						: <Spinner animation="border" />
					)
				}
				
			</div>
		);
	}
}

export default Assets;