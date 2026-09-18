import React from 'react';
import { AIEventFeed } from '../components/ai-events/AIEventFeed';

export const AIEvents: React.FC = () => {
  return (
    <div className="p-6 max-w-[1600px] mx-auto w-full">
      <AIEventFeed />
    </div>
  );
};
