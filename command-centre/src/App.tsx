import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { Dashboard } from './pages/Dashboard';
import { Mission } from './pages/Mission';
import { MapView } from './pages/MapView';
import { AIEvents } from './pages/AIEvents';
import { Governor } from './pages/Governor';
import { Communications } from './pages/Communications';
import { Telemetry } from './pages/Telemetry';
import { Evidence } from './pages/Evidence';
import { Simulator } from './pages/Simulator';
import { Settings } from './pages/Settings';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="mission" element={<Mission />} />
          <Route path="map" element={<MapView />} />
          <Route path="ai-events" element={<AIEvents />} />
          <Route path="governor" element={<Governor />} />
          <Route path="communications" element={<Communications />} />
          <Route path="telemetry" element={<Telemetry />} />
          <Route path="evidence" element={<Evidence />} />
          <Route path="simulator" element={<Simulator />} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
