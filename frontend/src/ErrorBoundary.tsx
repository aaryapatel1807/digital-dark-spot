import { Component, type ReactNode } from "react";

// Task 1 defence: a render crash anywhere in the app used to leave a
// completely blank page with no clue. The boundary catches it and
// shows a plain fallback with a reload action instead of blankness.
// It does NOT hide the error: the message is shown, and the error is
// logged to the console for diagnosis.
export class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error) {
    console.error("GapLens render error:", error);
  }

  render() {
    if (this.state.error) {
      return (
        <main style={{ maxWidth: 640, margin: "4rem auto", padding: "0 1.5rem", fontFamily: "system-ui, sans-serif" }}>
          <h1>Something went wrong rendering GapLens</h1>
          <p>
            The page could not be displayed. Your saved reports are still in this browser; reloading usually
            restores the page.
          </p>
          <p>
            <code>{this.state.error.message}</code>
          </p>
          <button type="button" onClick={() => window.location.reload()} style={{ padding: "0.6rem 1.2rem", borderRadius: 12 }}>
            Reload GapLens
          </button>
        </main>
      );
    }
    return this.props.children;
  }
}
