import { NavLink } from 'react-router-dom';

// TODO: Replace with brand logo component.
export default function Navbar() {
  const linkClass = ({ isActive }: { isActive: boolean }): string =>
    `text-sm transition-colors ${isActive ? 'text-[#2563eb]' : 'text-[#888888] hover:text-white'}`;

  return (
    <nav className="h-14 w-full border-b border-[#222222] bg-[#0a0a0a] px-4">
      <div className="mx-auto flex h-full max-w-6xl items-center justify-between">
        <h1 className="flex items-center gap-2 font-semibold text-white">
          <span className="h-2 w-2 rounded-full bg-[#2563eb]" aria-hidden />
          iGaming Research
        </h1>
        <div className="flex gap-5">
          <NavLink to="/" className={linkClass}>Dashboard</NavLink>
          <NavLink to="/history" className={linkClass}>History</NavLink>
          <NavLink to="/settings" className={linkClass}>Settings</NavLink>
        </div>
      </div>
    </nav>
  );
}
