import React from 'react';
import { Outlet } from 'react-router-dom';
import { TopBar } from './TopBar';
import { Sidebar } from '../navigation/Sidebar';

export const AppLayout: React.FC = () => {
  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#070a10] text-slate-100 font-sans">
      {/* Top Bar */}
      <TopBar />

      {/* Main App Body */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Navigation Sidebar */}
        <Sidebar />

        {/* Viewport Content */}
        <main className="flex-1 overflow-y-auto bg-[#070a10] relative flex flex-col">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
