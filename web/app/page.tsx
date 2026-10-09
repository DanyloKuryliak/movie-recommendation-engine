"use client";

import { useEffect, useMemo, useState } from "react";

type Movie = { movie_id: number; title: string; genres: string[] };
type MoviePage = { items: Movie[]; total: number };
type Recommendation = Movie & { estimated_rating: number; reason: string };

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const RATING_LABELS = ["Didn't like it", "Not for me", "It was okay", "Liked it", "Loved it"];

export default function Home() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [genres, setGenres] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [genre, setGenre] = useState("");
  const [ratings, setRatings] = useState<Record<number, number>>({});
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [status, setStatus] = useState("Loading the movie collection…");
  const [busy, setBusy] = useState(false);
  const [activeView, setActiveView] = useState<"discover" | "recommendations">("discover");
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    fetch(`${API}/api/v1/genres`)
      .then((response) => response.json())
      .then(setGenres)
      .catch(() => setStatus("Could not reach the recommendation API."));
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      const params = new URLSearchParams({ limit: "48", offset: String(offset) });
      if (query.trim()) params.set("q", query.trim());
      if (genre) params.set("genre", genre);
      try {
        const response = await fetch(`${API}/api/v1/movies?${params}`);
        if (!response.ok) throw new Error("Catalog request failed");
        const page: MoviePage = await response.json();
        setMovies((current) => offset === 0 ? page.items : [...current, ...page.items]);
        setTotal(page.total);
        setStatus("");
      } catch {
        setStatus("Could not reach the movie catalog. Please try again in a moment.");
      }
    }, 180);
    return () => window.clearTimeout(timer);
  }, [query, genre, offset]);

  const ratedMovies = useMemo(
    () => Object.entries(ratings).map(([movieId, rating]) => ({ movie_id: Number(movieId), rating })),
    [ratings],
  );

  async function getRecommendations() {
    setBusy(true);
    setStatus("");
    try {
      const response = await fetch(`${API}/api/v1/recommendations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ratings: ratedMovies, limit: 10 }),
      });
      if (!response.ok) throw new Error("Recommendation request failed");
      setRecommendations(await response.json());
      setActiveView("recommendations");
    } catch {
      setStatus("Could not build recommendations. Check that the API is running and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="site-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Reel Good home"><span className="brand-mark">r.</span> reel good</a>
        <div className="model-pill"><span className="pulse-dot" /> SPARK ALS <span className="pill-divider">/</span> v1</div>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="eyebrow"><span>✳</span> A little science for your next movie night</p>
          <h1>Your taste.<br /><em>Your next favorite.</em></h1>
          <p className="hero-description">Rate a few films you know. We’ll look for patterns in your taste and find something new to watch.</p>
          <div className="hero-actions">
            <button className="button button-primary" onClick={getRecommendations} disabled={busy}>
              {busy ? "Finding your next film…" : "Find my next film"}<span aria-hidden="true"> ↗</span>
            </button>
            <span className="rating-count">{ratedMovies.length} rated <span>·</span> {total.toLocaleString()} films to explore</span>
          </div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="orbit orbit-one" /><div className="orbit orbit-two" />
          <div className="poster poster-back"><span>02</span><strong>THE<br />UNKNOWN</strong><small>A NEW FAVORITE</small></div>
          <div className="poster poster-front"><span>01</span><strong>YOUR<br />NEXT<br /><i>STORY</i></strong><small>RECOMMENDED FOR YOU</small></div>
          <span className="spark spark-one">✳</span><span className="spark spark-two">✦</span>
        </div>
      </section>

      <section className="how-row" aria-label="How recommendations work">
        <div><span className="step-number">01</span><p><strong>Tell us your taste</strong><br />Rate a few you’ve seen</p></div>
        <span className="step-arrow">→</span>
        <div><span className="step-number">02</span><p><strong>We find the pattern</strong><br />ALS learns from ratings</p></div>
        <span className="step-arrow">→</span>
        <div><span className="step-number">03</span><p><strong>Meet something new</strong><br />Get a ranked watchlist</p></div>
      </section>

      <section className="discovery-section" aria-labelledby="discover-title">
        <div className="section-heading">
          <div><p className="eyebrow">YOUR MOVIE NIGHT STARTS HERE</p><h2 id="discover-title">Pick a few you love.</h2></div>
          <nav className="view-tabs" aria-label="Movie views">
            <button className={activeView === "discover" ? "tab active" : "tab"} onClick={() => setActiveView("discover")}>Discover</button>
            <button className={activeView === "recommendations" ? "tab active" : "tab"} onClick={() => setActiveView("recommendations")}>Your picks {recommendations.length > 0 && <span>{recommendations.length}</span>}</button>
          </nav>
        </div>

        {activeView === "discover" ? (
          <>
            <div className="catalog-tools">
              <label className="search-box"><span aria-hidden="true">⌕</span><input value={query} onChange={(event) => { setOffset(0); setQuery(event.target.value); }} placeholder="Search movies…" aria-label="Search movies" /></label>
              <label className="genre-select"><span className="sr-only">Filter by genre</span><select value={genre} onChange={(event) => { setOffset(0); setGenre(event.target.value); }}><option value="">All genres</option>{genres.map((item) => <option key={item}>{item}</option>)}</select><span aria-hidden="true">⌄</span></label>
            </div>
            <p className="results-label">{total.toLocaleString()} MOVIES <span>·</span> RATE A FILM TO ADD IT TO YOUR TASTE PROFILE</p>
            {status && <p className="status-message" role="status">{status}</p>}
            <div className="movie-grid">
              {movies.map((movie, index) => (
                <article className={`movie-card poster-tone-${index % 6}`} key={movie.movie_id}>
                  <div className="mini-poster"><span className="poster-kicker">REEL GOOD · {String(index + 1).padStart(2, "0")}</span><strong>{movie.title}</strong><span className="mini-poster-glyph">✳</span><span className="mini-poster-year">A GOOD STORY IS ALWAYS IN SEASON</span></div>
                  <div className="movie-card-info"><h3>{movie.title}</h3><p>{movie.genres.length ? movie.genres.join(" · ") : "Genre unknown"}</p><div className="rate-row" aria-label={`Rate ${movie.title}`}>
                    <span className="rate-label">YOUR RATING</span>
                    <div className="rating-buttons">{[1, 2, 3, 4, 5].map((value) => <button key={value} className={ratings[movie.movie_id] === value ? "rating-button selected" : "rating-button"} onClick={() => setRatings((current) => ({ ...current, [movie.movie_id]: value }))} aria-label={`${value} out of 5: ${RATING_LABELS[value - 1]}`} aria-pressed={ratings[movie.movie_id] === value}>{value}</button>)}</div>
                  </div></div>
                </article>
              ))}
            </div>
            {movies.length < total && <button className="button button-more" onClick={() => setOffset((current) => current + 48)}>Show more films <span>↓</span></button>}
            {movies.length === 0 && !status && <p className="empty-state">No films match that search. Try another title or genre.</p>}
          </>
        ) : (
          <div className="recommendation-view">
            {status && <p className="status-message" role="status">{status}</p>}
            {recommendations.length === 0 ? <div className="empty-state"><span className="empty-star">✳</span><h3>Your watchlist is waiting.</h3><p>Rate a few movies in Discover, then let the model find your next favorite.</p><button className="button button-primary" onClick={() => setActiveView("discover")}>Explore movies <span>↗</span></button></div> : <div className="recommendation-grid">{recommendations.map((movie, index) => <article className="recommendation-card" key={movie.movie_id}><div className={`rec-art poster-tone-${index % 6}`}><span>YOUR NEXT WATCH · {String(index + 1).padStart(2, "0")}</span><strong>{movie.title}</strong><i>✳</i></div><div className="rec-content"><div className="rec-topline"><span>#{String(index + 1).padStart(2, "0")} FOR YOUR LIST</span><span>EST. {movie.estimated_rating.toFixed(1)} / 5</span></div><h3>{movie.title}</h3><p className="rec-genres">{movie.genres.join(" · ")}</p><p className="rec-reason">{movie.reason}</p></div></article>)}</div>}
          </div>
        )}
      </section>

      <footer className="footer"><span>Made for curious movie people.</span><span>MovieLens · Spark ALS · MLflow</span><span>No account · ratings aren't saved.</span><a href="https://grouplens.org/datasets/movielens/latest/" target="_blank" rel="noreferrer">MovieLens Latest Small · GroupLens</a></footer>
    </main>
  );
}
