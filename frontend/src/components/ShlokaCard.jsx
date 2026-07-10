import { useState, useRef } from "react";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";
import { Heart, Play, Pause, Loader2, Quote, Share2 } from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const FAV_KEY = "gita_favorites";

const isFav = (id) => {
  try {
    const favs = JSON.parse(localStorage.getItem(FAV_KEY) || "[]");
    return favs.some((f) => f.id === id);
  } catch {
    return false;
  }
};

const toggleFav = (shloka) => {
  try {
    const favs = JSON.parse(localStorage.getItem(FAV_KEY) || "[]");
    const exists = favs.find((f) => f.id === shloka.id);
    let next;
    if (exists) {
      next = favs.filter((f) => f.id !== shloka.id);
    } else {
      next = [{ ...shloka, saved_at: new Date().toISOString() }, ...favs];
    }
    localStorage.setItem(FAV_KEY, JSON.stringify(next));
    return !exists;
  } catch {
    return false;
  }
};

export default function ShlokaCard({ shloka, defaultOpen = true }) {
  const [saved, setSaved] = useState(isFav(shloka.id));
  const [loadingAudio, setLoadingAudio] = useState(false);
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef(null);
  const cachedAudioRef = useRef(null);

  const handleSave = () => {
    const nowSaved = toggleFav(shloka);
    setSaved(nowSaved);
    toast(nowSaved ? "Saved to your collection" : "Removed from saved", {
      duration: 1800,
    });
  };

  const handlePlay = async () => {
    if (audioRef.current && cachedAudioRef.current) {
      if (playing) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      return;
    }
    setLoadingAudio(true);
    try {
      const { data } = await axios.post(`${API}/tts/narrate`, {
        text: shloka.sanskrit,
      });
      const audioSrc = `data:${data.mime_type};base64,${data.audio_base64}`;
      cachedAudioRef.current = audioSrc;
      const audio = new Audio(audioSrc);
      audioRef.current = audio;
      audio.onplay = () => setPlaying(true);
      audio.onpause = () => setPlaying(false);
      audio.onended = () => setPlaying(false);
      audio.play();
    } catch (e) {
      toast.error("Could not generate audio. Try again.");
    } finally {
      setLoadingAudio(false);
    }
  };

  const handleShare = async () => {
    const shareText = `${shloka.sanskrit}\n\n— ${shloka.reference}\n\n"${shloka.english_translation}"`;
    try {
      if (navigator.share) {
        await navigator.share({ title: "Gita Wisdom", text: shareText });
      } else {
        await navigator.clipboard.writeText(shareText);
        toast.success("Copied to clipboard");
      }
    } catch {
      /* user cancelled */
    }
  };

  const stagger = (delay) => ({
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.55, ease: "easeOut", delay },
  });

  return (
    <AnimatePresence>
      <motion.article
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="shloka-card paper-grain rounded-3xl border border-border-soft/70 p-8 md:p-12 shadow-[0_12px_40px_rgba(44,42,40,0.06)]"
        data-testid="shloka-card"
      >
        {/* Reference + actions */}
        <div className="flex items-start justify-between mb-8 gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-stone font-sans">
              {shloka.reference || `Chapter ${shloka.chapter}, Verse ${shloka.verse}`}
            </p>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={handleShare}
              data-testid="share-btn"
              aria-label="Share"
              className="p-2 rounded-full text-stone hover:text-moss hover:bg-subtle/60"
            >
              <Share2 className="w-4 h-4" strokeWidth={1.5} />
            </button>
            <button
              onClick={handleSave}
              data-testid="save-favorite-btn"
              aria-label="Save to favorites"
              className={`p-2 rounded-full hover:bg-subtle/60 ${
                saved ? "text-terracotta" : "text-stone hover:text-terracotta"
              }`}
            >
              <Heart
                className="w-4 h-4"
                strokeWidth={1.5}
                fill={saved ? "currentColor" : "none"}
              />
            </button>
          </div>
        </div>

        {/* Sanskrit */}
        <motion.div {...stagger(0)} className="mb-6 relative">
          <Quote className="absolute -top-2 -left-2 w-8 h-8 text-border-soft" strokeWidth={1} />
          <p
            data-testid="shloka-sanskrit"
            className="font-sanskrit text-2xl sm:text-3xl md:text-4xl leading-[1.7] text-moss tracking-normal pl-2"
            style={{ whiteSpace: "pre-line" }}
          >
            {shloka.sanskrit}
          </p>
        </motion.div>

        {/* Transliteration */}
        {shloka.transliteration && (
          <motion.p
            {...stagger(0.1)}
            className="font-serif italic text-base md:text-lg text-stone leading-relaxed mb-8 pl-2"
            data-testid="shloka-transliteration"
          >
            {shloka.transliteration}
          </motion.p>
        )}

        {/* Audio control */}
        <motion.div {...stagger(0.15)} className="mb-10">
          <button
            onClick={handlePlay}
            disabled={loadingAudio}
            data-testid="play-audio-btn"
            className="inline-flex items-center gap-3 bg-subtle/70 hover:bg-subtle rounded-full py-2.5 px-5 text-sm font-sans tracking-wide text-ink disabled:opacity-60"
          >
            {loadingAudio ? (
              <>
                <Loader2 className="w-4 h-4 text-moss animate-spin" strokeWidth={1.5} />
                <span>Preparing recitation…</span>
              </>
            ) : playing ? (
              <>
                <Pause className="w-4 h-4 text-moss" strokeWidth={1.5} fill="currentColor" />
                <span>Pause recitation</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 text-moss" strokeWidth={1.5} fill="currentColor" />
                <span>Listen in Sanskrit</span>
              </>
            )}
          </button>
        </motion.div>

        <div className="space-y-8 border-t border-border-soft/60 pt-8">
          {/* Hindi */}
          <motion.div {...stagger(0.2)}>
            <p className="text-xs uppercase tracking-[0.25em] text-stone mb-2 font-sans">
              हिन्दी अनुवाद · Hindi
            </p>
            <p
              data-testid="shloka-hindi"
              className="font-sanskrit text-lg md:text-xl leading-relaxed text-ink"
            >
              {shloka.hindi_translation}
            </p>
          </motion.div>

          {/* English */}
          <motion.div {...stagger(0.3)}>
            <p className="text-xs uppercase tracking-[0.25em] text-stone mb-2 font-sans">
              English Translation
            </p>
            <p
              data-testid="shloka-english"
              className="font-serif text-lg md:text-xl leading-relaxed text-ink italic"
            >
              "{shloka.english_translation}"
            </p>
          </motion.div>

          {/* Guidance */}
          <motion.div {...stagger(0.4)} className="bg-subtle/40 -mx-4 md:-mx-6 px-4 md:px-6 py-6 rounded-2xl">
            <p className="text-xs uppercase tracking-[0.25em] text-moss mb-3 font-sans">
              Wisdom for you
            </p>
            <p
              data-testid="shloka-guidance"
              className="font-sans text-base md:text-lg leading-relaxed text-ink"
            >
              {shloka.practical_guidance}
            </p>
          </motion.div>
        </div>
      </motion.article>
    </AnimatePresence>
  );
}
