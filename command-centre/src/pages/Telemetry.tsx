import React from 'react';
import { TelemetryPanel } from '../components/telemetry/TelemetryPanel';

export const Telemetry: React.FC = () => {
  return (
    <div className="p-6 max-w-[1500px] mx-auto w-full">
      <TelemetryPanel />
    </div>
  );
};
