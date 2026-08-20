import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error caught by ErrorBoundary:', error, errorInfo);
    this.setState({ errorInfo });
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
          <div className="max-w-lg w-full bg-slate-900 border border-red-500/40 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center space-x-3 text-red-400">
              <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <h2 className="text-xl font-bold">Application Error</h2>
            </div>
            <p className="text-sm text-slate-300">
              An unexpected runtime error occurred while rendering the application.
            </p>
            {this.state.error && (
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs font-mono text-red-300 overflow-x-auto">
                {this.state.error.toString()}
              </div>
            )}
            <button
              onClick={() => window.location.reload()}
              className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-medium py-2 rounded-lg transition"
            >
              Reload Application
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
