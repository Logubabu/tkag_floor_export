import React, { useState } from 'react';
import { DashboardPage } from './pages/DashboardPage';
import { ModelViewerPage } from './pages/ModelViewerPage';

export function App() {
  const [currentPage, setCurrentPage] = useState<'dashboard' | 'viewer'>('viewer');

  if (currentPage === 'dashboard') {
    return <DashboardPage onNavigateToViewer={() => setCurrentPage('viewer')} />;
  }

  return <ModelViewerPage onNavigateHome={() => setCurrentPage('dashboard')} />;
}

export default App;
