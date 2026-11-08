import React from 'react'
import Card from 'react-bootstrap/Card';

function format(timeRef) {
	const diffSec = Math.floor((timeRef - Date.now()) / 1000);
	if (diffSec < 0) {
		return "Already\nhappened";
	}
	const days = Math.floor(diffSec / 86400);
	const hours = Math.floor((diffSec % 86400) / 3600).toString().padStart(2, "0");
	const mins = Math.floor((diffSec % 3600) / 60).toString().padStart(2, "0");
	const secs = (diffSec % 60).toString().padStart(2, "0");
	return `${days} days\n${hours}:${mins}:${secs}`;
}

class Timer extends React.Component {
	constructor(props) {
		super(props);
		const timeRef = new Date(props.time).getTime();
		this.state = { timeRef, timeLeft: format(timeRef) };
	}

	tick = () => {
		const timeLeft = format(this.state.timeRef);
		// Don't re-render when nothing changed
		if (timeLeft !== this.state.timeLeft) {
			this.setState({ timeLeft });
		}
	}

	componentDidMount() {
		// Display only has one second resolution, no point ticking faster
		this.interval = setInterval(this.tick, 1000);
	}

	componentWillUnmount() {
		clearInterval(this.interval);
	}

	render() {
		return (
			<Card bg="light">
				<Card.Body className="text-center mb-3 mt-3">
					<h1 className="mb-3 font-monospace fw-bold" style={{ whiteSpace: "pre" }}>{this.state.timeLeft}</h1>
					<p className="mb-1">{this.state.timeRef < Date.now() ? "Time since" : "Time until"}</p>
					<p className="fw-bold mb-0 fs-5">{this.props.event}</p>
				</Card.Body>
			</Card>
		);
	}
}

export default Timer;
