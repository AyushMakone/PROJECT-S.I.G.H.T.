import React from 'react';
import { CommunicationPanel } from '../components/communication/CommunicationPanel';
import { MetricsPanel } from '../components/metrics/MetricsPanel';

export const Communications: React.FC = () => {
  return (
    <div className="p-6 max-w-[1500px] mx-auto w-full space-y-6">
      <CommunicationPanel />
      <MetricsPanel />
    </div>
  );
};
