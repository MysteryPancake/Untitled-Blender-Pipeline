import React from 'react';
import Alert from 'react-bootstrap/Alert';
import Table from 'react-bootstrap/Table';
import Spinner from 'react-bootstrap/Spinner';

import AddTask from '../components/AddTask';
import { apiGet } from '../api';

class Tasks extends React.Component {
	constructor(props) {
		super(props);
		this.state = {};
	}

	load = () => {
		apiGet('/tasks/get')
			.then((json) => this.setState({ tasks: json, error: undefined }))
			.catch((err) => this.setState({ error: err.message }));
	}

	componentDidMount() {
		this.load();
	}

	render() {
		return (
			<div className="m-3">
				<div className="mb-2">
					<h2 className="d-inline-block">Tasks</h2>
					<AddTask className="float-end" onAdded={this.load}>+ Add Task</AddTask>
				</div>
				{
					this.state.tasks
					? <Table bordered>
						<thead style={{ backgroundColor: "#EEE" }}>
							<tr>
								<th>Task Name</th>
								<th>Description</th>
								<th>Assets</th>
							</tr>
						</thead>
						<tbody>
							{
								this.state.tasks.map((task, i) => {
									return <tr key={i}>
										<td>{task.name}</td>
										<td>{task.description}</td>
										<td>{task.assets}</td>
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

export default Tasks;