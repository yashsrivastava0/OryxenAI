// ErrorBoundary component (docs/Frontend/05 §18, §19 Phase 5).
// Prevents any unhandled component/rendering exception in a stage surface
// from unmounting the whole application. Renders an honest Editorial Swiss
// recovery surface with reload/retry capability.

import { Component, type ComponentChildren } from "preact";

export interface ErrorBoundaryProps {
  children: ComponentChildren;
  fallbackTitle?: string;
  fallbackMessage?: string;
  onReset?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: unknown): void {
    // Keep diagnostics available for local debugging without exposing raw trace to user
    if (typeof console !== "undefined" && console.error) {
      console.error("[OryxenAI ErrorBoundary] Caught render exception:", error, errorInfo);
    }
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
    this.props.onReset?.();
  };

  render() {
    if (this.state.hasError) {
      const title = this.props.fallbackTitle || "Something went wrong displaying this stage";
      const message =
        this.props.fallbackMessage ||
        "An unexpected error occurred while rendering. Your approved portfolio work is safely saved on the server.";

      return (
        <div className="stage-error-boundary-panel" role="alert">
          <div className="error-boundary-card">
            <span className="error-boundary-icon" aria-hidden="true">⚠</span>
            <h2 className="error-boundary-title">{title}</h2>
            <p className="error-boundary-message">{message}</p>
            {this.state.error?.message && (
              <p className="error-boundary-detail">
                <small>Reference: {this.state.error.message}</small>
              </p>
            )}
            <div className="error-boundary-actions">
              <button
                type="button"
                className="btn-primary"
                onClick={this.handleRetry}
              >
                Reload surface
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
