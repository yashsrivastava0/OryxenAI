import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = { children: ReactNode };
type State = { failed: boolean };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(_error: Error, _info: ErrorInfo): void {
    // The trusted runtime boundary deliberately exposes only a safe state.
  }

  render() {
    if (this.state.failed) {
      return <main className="route-page"><h1>Something went wrong</h1><p>This portfolio could not render the requested view.</p></main>;
    }
    return this.props.children;
  }
}
