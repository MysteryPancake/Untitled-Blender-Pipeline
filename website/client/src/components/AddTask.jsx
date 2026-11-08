import React from 'react';
import Alert from 'react-bootstrap/Alert';
import Button from 'react-bootstrap/Button';
import Modal from 'react-bootstrap/Modal';
import Form from 'react-bootstrap/Form';
import { apiPost } from '../api';

const EMPTY_FORM = { taskName: "", taskDesc: "" };

class AddTask extends React.Component {
	constructor(props) {
		super(props);
		this.state = {
			show: false,
			error: "",
			...EMPTY_FORM
		};
	}

	showModal = () => {
		this.setState({ show: true, error: "" });
	}

	hideModal = () => {
		this.setState({ show: false, error: "" });
	}

	submit = (e) => {
		e.preventDefault();
		this.setState({ error: "" });
		apiPost('/tasks/add', {
			taskName: this.state.taskName,
			taskDesc: this.state.taskDesc
		}).then(() => {
			this.setState({ show: false, ...EMPTY_FORM });
			if (this.props.onAdded) this.props.onAdded();
		}).catch((err) => this.setState({ error: err.message }));
	}

	render() {
		const { onAdded, ...buttonProps } = this.props;
		return (
			<>
				<Button {...buttonProps} onClick={this.showModal}>{this.props.children}</Button>
				<Modal show={this.state.show} onHide={this.hideModal} backdrop="static" keyboard={false} centered>
					<Form onSubmit={this.submit}>
						<Modal.Header closeButton>
							<Modal.Title>Add Task</Modal.Title>
						</Modal.Header>
						<Modal.Body>
							<Form.Label htmlFor="taskName">Task Name</Form.Label>
							<Form.Control
								id="taskName"
								name="taskName"
								type="text"
								autoFocus
								value={this.state.taskName}
								onChange={e => this.setState({ taskName: e.target.value })}
								required
							/>
							<Form.Label htmlFor="taskDesc" className="mt-3">Task Description</Form.Label>
							<Form.Control
								id="taskDesc"
								name="taskDesc"
								type="text"
								as="textarea"
								rows={6}
								value={this.state.taskDesc}
								onChange={e => this.setState({ taskDesc: e.target.value })}
							/>
						</Modal.Body>
						<Modal.Footer>
							<Alert variant="danger" show={!!this.state.error}>{this.state.error}</Alert>
							<Button variant="secondary" onClick={this.hideModal}>Cancel</Button>
							<Button type="submit" variant="primary">Add Task</Button>
						</Modal.Footer>
					</Form>
				</Modal>
			</>
		);
	}
}

export default AddTask;