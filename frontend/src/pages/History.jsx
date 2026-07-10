import { useEffect, useState } from "react";
import { History as HistoryIcon } from "lucide-react";
import { Link } from "react-router-dom";
import ShlokaCard from "../components/ShlokaCard";

const HISTORY_KEY = "gita_history";

export default function History() {
  const [items, setItems] = useState([]);
  const [activeId, setActiveId] = useState(null);

  useEffect(() => {
    try {
      const list = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
      setItems(list);
      if (list[0]) setActiveId(list[0].id);
    } catch {
      setItems([]);
    }
  }, []);

  const refresh = () => {
    try {
      setItems(JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"));
    } catch {
      /* ignore */
    }
  };

  const active = items.find((f) => f.id === activeId);

  const formatDate = (iso) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-6 md:px-12 py-12 md:py-20">
      <header className="mb-12">
        <p className="text-xs uppercase tracking-[0.3em] text-stone mb-4">Journey</p>
        <h1 className="font-serif text-4xl md:text-5xl text-ink tracking-tight">
          Your path of inquiry
        </h1>
        <p className="mt-4 font-sans text-base md:text-lg text-stone max-w-2xl">
          Every verse you've received, in order. Stored privately on this device.
        </p>
      </header>

      {items.length === 0 ? (
        <div className="text-center py-16" data-testid="empty-history">
          <HistoryIcon className="w-10 h-10 mx-auto text-border-soft" strokeWidth={1.2} />
          <p className="mt-4 font-serif italic text-2xl text-stone">Your journey begins now</p>
          <Link
            to="/"
            className="inline-flex mt-8 items-center gap-2 bg-moss hover:bg-moss-hover text-sand px-6 py-3 rounded-full text-sm tracking-wide"
            data-testid="start-journey-btn"
          >
            Ask your first question
          </Link>
        </div>
      ) : (
        <div className="grid md:grid-cols-12 gap-8">
          <aside className="md:col-span-5 lg:col-span-4" data-testid="history-list">
            {items.map((f) => (
              <button
                key={f.id}
                onClick={() => setActiveId(f.id)}
                data-testid={`history-item-${f.id}`}
                className={`w-full text-left py-4 px-2 border-b border-border-soft/60 hover:bg-paper/60 transition-colors ${
                  activeId === f.id ? "bg-paper/60" : ""
                }`}
              >
                <p className="text-xs text-lightStone">{formatDate(f.created_at)}</p>
                <p className="mt-1 font-sans text-sm text-ink line-clamp-2">
                  {f.situation}
                </p>
                <p className="mt-1 text-xs uppercase tracking-[0.2em] text-moss">
                  {f.reference}
                </p>
              </button>
            ))}
            <div className="mt-4">
              <button
                onClick={() => {
                  if (window.confirm("Clear all history?")) {
                    localStorage.removeItem(HISTORY_KEY);
                    refresh();
                    setActiveId(null);
                  }
                }}
                className="text-xs text-lightStone hover:text-terracotta"
                data-testid="clear-history-btn"
              >
                Clear history
              </button>
            </div>
          </aside>
          <div className="md:col-span-7 lg:col-span-8">
            {active && <ShlokaCard key={active.id} shloka={active} />}
          </div>
        </div>
      )}
    </div>
  );
}
