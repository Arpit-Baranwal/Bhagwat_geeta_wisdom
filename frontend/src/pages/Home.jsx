import { useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import { Sparkles, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import ShlokaCard from "../components/ShlokaCard";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const HISTORY_KEY = "gita_history";

const SUGGESTIONS = [
  "I feel anxious about my career",
  "I'm grieving a loss",
  "I can't focus and feel restless",
  "I am afraid of failure",
  "I feel envious of others' success",
  "I struggle to forgive someone",
];

export default function Home() {
  const [situation, setSituation] = useState("");
  const [loading, setLoading] = useState(false);
  const [shloka, setShloka] = useState(null);

  const saveToHistory = (item) => {
    try {
      const hist = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
      const next = [item, ...hist.filter((h) => h.id !== item.id)].slice(0, 50);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
    } catch {
      /* ignore */
    }
  };

  const handleSubmit = async (e) => {
    e?.preventDefault?.();
    const text = situation.trim();
    if (text.length < 3) {
      toast.error("Please share a bit more about your situation");
      return;
    }
    setLoading(true);
    setShloka(null);
    try {
      const { data } = await axios.post(`${API}/shloka/generate`, {
        situation: text,
      });
      setShloka(data);
      if (!data.crisis) saveToHistory(data);
    } catch (e) {
      toast.error(
        e?.response?.data?.detail || "Could not find wisdom right now. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const applySuggestion = (s) => {
    setSituation(s);
  };

  return (
    <div className="max-w-4xl mx-auto px-6 md:px-12 py-12 md:py-20">
      {/* Hero */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7 }}
        className="mb-12 md:mb-16"
      >
        <p
          className="text-xs md:text-sm uppercase tracking-[0.3em] text-stone mb-6"
          data-testid="hero-eyebrow"
        >
          Ancient verse · For this moment
        </p>
        <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl leading-[1.05] text-ink tracking-tight">
          Wherever you stand,<br />
          <span className="italic text-moss">the Gita has a verse for you.</span>
        </h1>
        <p className="mt-6 md:mt-8 font-sans text-base md:text-lg text-stone max-w-2xl leading-relaxed">
          Share what you're feeling or facing. Receive a Bhagavad Gita shloka chosen
          for your moment in Sanskrit, with Hindi & English translations and
          a quiet line of guidance for the path ahead.
        </p>
      </motion.section>

      {/* Input */}
      <motion.form
        onSubmit={handleSubmit}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.15 }}
        className="mb-10"
      >
        <label htmlFor="situation" className="block text-xs uppercase tracking-[0.25em] text-stone mb-3">
          Your situation
        </label>
        <div className="relative">
          <textarea
            id="situation"
            data-testid="situation-input"
            value={situation}
            onChange={(e) => setSituation(e.target.value)}
            placeholder="e.g. I feel overwhelmed by responsibilities and uncertain about my path…"
            rows={4}
            className="w-full bg-paper/80 border border-border-soft rounded-2xl p-5 md:p-6 font-sans text-base md:text-lg text-ink placeholder:text-lightStone resize-none focus:outline-none focus:ring-2 focus:ring-moss/40 focus:border-moss/60 transition-all"
          />
        </div>

        {/* Suggestion chips */}
        <div className="mt-5 flex gap-2 flex-wrap" data-testid="suggestions-row">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => applySuggestion(s)}
              data-testid={`suggestion-${s.slice(0, 12).replace(/\s+/g, "-").toLowerCase()}`}
              className="inline-flex items-center px-4 py-2 rounded-full border border-border-soft text-sm font-sans text-stone hover:border-moss hover:text-moss bg-paper/40"
            >
              {s}
            </button>
          ))}
        </div>

        <div className="mt-8 flex items-center gap-4">
          <button
            type="submit"
            disabled={loading}
            data-testid="submit-situation-btn"
            className="inline-flex items-center gap-2 bg-moss hover:bg-moss-hover text-sand px-7 py-3.5 rounded-full font-sans tracking-wide shadow-sm disabled:opacity-60"
          >
            {loading ? (
              <>
                <Sparkles className="w-4 h-4 animate-pulse" strokeWidth={1.5} />
                Seeking wisdom…
              </>
            ) : (
              <>
                Reveal a verse
                <ArrowRight className="w-4 h-4" strokeWidth={1.8} />
              </>
            )}
          </button>
          <span className="text-xs text-lightStone">Private · No login needed</span>
        </div>
      </motion.form>

      {/* Loading state */}
      {loading && (
        <div className="py-16 text-center" data-testid="loading-state">
          <p className="breathe-text font-serif italic text-2xl md:text-3xl text-moss">
            seeking wisdom
          </p>
        </div>
      )}

      {/* Result */}
      {shloka && !loading && (
        <section className="mt-6" data-testid="shloka-result">
          {shloka.crisis ? (
            <div
              data-testid="crisis-card"
              className="rounded-3xl border-2 border-terracotta/60 bg-terracotta/5 p-8 md:p-10"
            >
              <p className="text-xs uppercase tracking-[0.25em] text-terracotta mb-3 font-sans">
                You are not alone
              </p>
              <p className="font-sans text-base md:text-lg leading-relaxed text-ink whitespace-pre-line">
                {shloka.practical_guidance}
              </p>
            </div>
          ) : (
            <ShlokaCard shloka={shloka} />
          )}
        </section>
      )}
    </div>
  );
}
