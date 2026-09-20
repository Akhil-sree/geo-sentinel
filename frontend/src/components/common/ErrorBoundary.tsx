import { Component, type ReactNode } from "react";

interface State { error: Error | null; }

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State { return { error }; }

  componentDidCatch(error: Error) { console.error("UI crash:", error); }

  render() {
    if (this.state.error) {
      return (
        <div className="grid h-full place-items-center p-8 text-center text-[12px] text-gs-text-secondary">
          <div>
            <p className="mb-2 font-semibold text-risk-critical">Something broke in the UI.</p>
            <p className="mb-4 text-[10px] text-gs-text-secondary">{this.state.error.message}</p>
            <button onClick={() => this.setState({ error: null })}
              className="rounded-card bg-forest px-4 py-1.5 text-[11px] font-medium text-white transition hover:bg-forest-800">Reload view</button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
