import { useEffect, useState } from "react";
import { Heart } from "lucide-react";
import { Link } from "react-router-dom";
import ShlokaCard from "../components/ShlokaCard";

const FAV_KEY = "gita_favorites";

export default function Favorites() {
  const [favs, setFavs] = useState([]);
  const [activeId, setActiveId] = useState(null);

  useEffect(() => {
    try {
      const list = JSON.parse(localStorage.getItem(FAV_KEY) || "[]");
      setFavs(list);
      if (list[0]) setActiveId(list[0].id);
    } catch {
      setFavs([]);
    }
  }, []);

  const refresh = () => {
    try {
      setFavs(JSON.parse(localStorage.getItem(FAV_KEY) || "[]"));
    } catch {
      /* ignore */
    }
  };

  const active = favs.find((f) => f.id === activeId);

  return (
    <div className="max-w-5xl mx-auto px-6 md:px-12 py-12 md:py-20">
      <header className="mb-12">
        <p className="text-xs uppercase tracking-[0.3em] text-stone mb-4">Saved</p>
        <h1 className="font-serif text-4xl md:text-5xl text-ink tracking-tight">
          Verses you return to
        </h1>
        <p className="mt-4 font-sans text-base md:text-lg text-stone max-w-2xl">
          Saved on this device. Click a verse from the list to open it again.
        </p>
      </header>

      {favs.length === 0 ? (
        <div className="text-center py-16" data-testid="empty-favorites">
          <Heart className="w-10 h-10 mx-auto text-border-soft" strokeWidth={1.2} />
          <p className="mt-4 font-serif italic text-2xl text-stone">No verses saved yet</p>
          <p className="mt-2 text-sm text-lightStone">
            Save a verse from the home page to revisit it here.
          </p>
          <Link
            to="/"
            className="inline-flex mt-8 items-center gap-2 bg-moss hover:bg-moss-hover text-sand px-6 py-3 rounded-full text-sm tracking-wide"
            data-testid="go-home-btn"
          >
            Find a verse
          </Link>
        </div>
      ) : (
        <div className="grid md:grid-cols-12 gap-8">
          <aside className="md:col-span-4 space-y-1" data-testid="favorites-list">
            {favs.map((f) => (
              <button
                key={f.id}
                onClick={() => setActiveId(f.id)}
                data-testid={`fav-item-${f.id}`}
                className={`w-full text-left px-4 py-4 rounded-xl border transition-colors ${
                  activeId === f.id
                    ? "border-moss bg-paper"
                    : "border-transparent hover:bg-paper/60 border-b border-border-soft/60 rounded-none"
                }`}
              >
                <p className="text-xs uppercase tracking-[0.2em] text-stone">
                  {f.reference}
                </p>
                <p className="mt-1 font-serif text-base text-ink line-clamp-2 italic">
                  "{f.english_translation?.slice(0, 90)}…"
                </p>
                <p className="mt-2 text-xs text-lightStone line-clamp-1">
                  For: {f.situation}
                </p>
              </button>
            ))}
          </aside>
          <div className="md:col-span-8">
            {active && (
              <ShlokaCard key={active.id} shloka={active} />
            )}
            {favs.length > 0 && (
              <div className="mt-4 text-right">
                <button
                  onClick={() => {
                    if (window.confirm("Clear all saved verses?")) {
                      localStorage.removeItem(FAV_KEY);
                      refresh();
                      setActiveId(null);
                    }
                  }}
                  className="text-xs text-lightStone hover:text-terracotta"
                  data-testid="clear-favorites-btn"
                >
                  Clear all saved
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
