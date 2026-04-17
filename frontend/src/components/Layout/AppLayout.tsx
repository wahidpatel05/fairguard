import React from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

interface AppLayoutProps {
  title: string;
  children: React.ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ title, children }) => {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header title={title} />
        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </div>
    </div>
  );
};

export default AppLayout;
