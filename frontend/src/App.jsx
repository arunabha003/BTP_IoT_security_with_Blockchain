import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { 
  Home, 
  UserPlus, 
  Shield, 
  Trash2, 
  Database,
  Activity,
  FileSignature,
  Users
} from 'lucide-react';

// Import pages
import Dashboard from './pages/Dashboard';
import EnrollDevice from './pages/EnrollDevice';
import AuthenticateDevice from './pages/AuthenticateDevice';
import RevokeDevice from './pages/RevokeDevice';
import DeviceList from './pages/DeviceList';
import SystemStatus from './pages/SystemStatus';
import MultiSigPropose from './pages/MultiSigPropose';
import MultiSigApprove from './pages/MultiSigApprove';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Toaster position="top-right" />
        <Navigation />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/enroll" element={<EnrollDevice />} />
            <Route path="/authenticate" element={<AuthenticateDevice />} />
            <Route path="/revoke" element={<RevokeDevice />} />
            <Route path="/devices" element={<DeviceList />} />
            <Route path="/multisig-propose" element={<MultiSigPropose />} />
            <Route path="/multisig-approve" element={<MultiSigApprove />} />
            <Route path="/status" element={<SystemStatus />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

function Navigation() {
  const location = useLocation();
  
  const navItems = [
    { path: '/', label: 'Dashboard', icon: Home },
    { path: '/enroll', label: 'Enroll Device', icon: UserPlus },
    { path: '/authenticate', label: 'Authenticate', icon: Shield },
    { path: '/revoke', label: 'Revoke Device', icon: Trash2 },
    { path: '/devices', label: 'Devices', icon: Database },
    { path: '/multisig-propose', label: 'Multi-Sig Propose', icon: FileSignature },
    { path: '/multisig-approve', label: 'Multi-Sig Approve', icon: Users },
    { path: '/status', label: 'System Status', icon: Activity },
  ];

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <Shield className="h-8 w-8 text-primary-600" />
              <span className="ml-2 text-xl font-bold text-gray-900">
                IoT Identity Gateway
              </span>
            </div>
            <div className="hidden sm:ml-8 sm:flex sm:space-x-4">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                      isActive
                        ? 'text-primary-700 bg-primary-50'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      </div>
      
      {/* Mobile menu */}
      <div className="sm:hidden px-2 pt-2 pb-3 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center px-3 py-2 text-base font-medium rounded-md ${
                isActive
                  ? 'text-primary-700 bg-primary-50'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <Icon className="h-5 w-5 mr-3" />
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

export default App;
