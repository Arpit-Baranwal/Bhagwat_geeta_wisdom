import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { Heart, History as HistoryIcon, BookOpen } from "lucide-react";

const navItems = [
  { to: "/", label: "Seek", icon: BookOpen, testId: "nav-home" },
  { to: "/favorites", label: "Saved", icon: Heart, testId: "nav-favorites" },
  { to: "/history", label: "Journey", icon: HistoryIcon, testId: "nav-history" },
];

export default function Layout() {
  const location = useLocation();
  return (
    <div className="min-h-screen bg-sand text-ink flex flex-col">
      {/* Header */}
      <header className="border-b border-border-soft/60 bg-sand/80 backdrop-blur-md sticky top-0 z-30">
        <div className="max-w-5xl mx-auto px-6 md:px-12 py-5 flex items-center justify-between">
          <Link to="/" className="flex items-baseline gap-3" data-testid="logo-link">
            <span className="font-serif text-2xl md:text-3xl tracking-tight text-ink">
              Geeta<span className="text-moss italic"> Wisdom</span>
            </span>
            <span className="hidden sm:inline font-sanskrit text-sm text-stone">गीता ज्ञान</span>
          </Link>
          <nav className="flex items-center gap-1 md:gap-2">
            {navItems.map(({ to, label, icon: Icon, testId }) => (
              <NavLink
                key={to}
                to={to}
                data-testid={testId}
                className={({ isActive }) =>
                  `inline-flex items-center gap-2 px-3 md:px-4 py-2 rounded-full text-sm font-sans tracking-wide transition-all ${
                    isActive
                      ? "bg-moss text-sand"
                      : "text-stone hover:text-ink hover:bg-subtle/70"
                  }`
                }
                end
              >
                <Icon className="w-4 h-4" strokeWidth={1.5} />
                <span className="hidden sm:inline">{label}</span>
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      {/* Main */}
      <motion.main
        key={location.pathname}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="flex-1"
      >
        <Outlet />
      </motion.main>

      {/* Footer */}
      <footer className="border-t border-border-soft/60 py-8 mt-16">
        <div className="max-w-5xl mx-auto px-6 md:px-12 text-center">
          <p className="font-sanskrit text-base text-stone">
            सर्वे भवन्तु सुखिनः
          </p>
          <p className="text-xs uppercase tracking-[0.25em] text-lightStone mt-2">
            May all beings be happy
          </p>
        </div>
      </footer>
    </div>
  );
}
