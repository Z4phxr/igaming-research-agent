import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import Navbar from '@/components/Navbar';
import Dashboard from '@/pages/Dashboard';
import History from '@/pages/History';
import Settings from '@/pages/Settings';

// TODO: Add route guards or 404 page if needed.
export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen">
        <Navbar />
        <main className="max-w-6xl mx-auto p-4">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/history" element={<History />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
