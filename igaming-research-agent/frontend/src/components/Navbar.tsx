import { NavLink } from 'react-router-dom';

// TODO: Replace with brand logo component.
export default function Navbar() {
  return (
    <nav className="bg-slate-900 text-white px-4 py-3">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <h1 className="font-bold">iGaming Research Agent</h1>
        <div className="flex gap-4 text-sm">
          <NavLink to="/" className="hover:underline">Home</NavLink>
          <NavLink to="/history" className="hover:underline">History</NavLink>
          <NavLink to="/settings" className="hover:underline">Settings</NavLink>
        </div>
      </div>
    </nav>
  );
}
