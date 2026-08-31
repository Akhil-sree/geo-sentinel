import { Component, type ReactNode } from "react";

interface State { error: Error | null; }

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State { return { error }; }

  componentDidCatch(error: Error) { console.error("UI crash:", error); }

  render() {
    if (this.state.error) {
      return (
        <div className="grid h-full place-items-center p-8 text-center text-sm text-slate-400">
          <div>
            <p className="mb-2 font-semibold text-red-400">Something broke in the UI.</p>
            <p className="mb-4 font-mono text-xs text-slate-600">{this.state.error.message}</p>
            <button onClick={() => this.setState({ error: null })}
              className="rounded bg-sky-600 px-4 py-1.5 text-xs font-semibold">Reload view</button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
