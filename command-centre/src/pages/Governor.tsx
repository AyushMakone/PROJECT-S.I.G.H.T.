import React from 'react';
import { GovernorPanel } from '../components/governor/GovernorPanel';

export const Governor: React.FC = () => {
  return (
    <div className="p-6 max-w-[1500px] mx-auto w-full">
      <GovernorPanel />
    </div>
  );
};
