import { useEffect, useState } from "react";
import Feed from "./components/Feed.jsx";
import { SparkleIcon } from "./components/Icons.jsx";

const NAME_KEY = "drift.displayName";

export default function App() {
  const [authorName, setAuthorName] = useState(() => {
    try {
      return localStorage.getItem(NAME_KEY) || "You";
    } catch {
      return "You";
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(NAME_KEY, authorName);
    } catch {
      /* private mode — name just won't persist */
    }
  }, [authorName]);

  return (
    <div className="app">
      <div className="app__glow" aria-hidden="true" />

      <header className="topbar">
        <div className="topbar__inner">
          <a className="brand" href="/">
            <span className="brand__mark" aria-hidden="true">
              <SparkleIcon />
            </span>
            <span className="brand__text">
              drift
              <span className="brand__tag">a quiet feed</span>
            </span>
          </a>
          <span className="topbar__hint">
            <span className="topbar__dot" aria-hidden="true" />
            {authorName === "You" ? "posting as you" : `posting as ${authorName}`}
          </span>
        </div>
      </header>

      <main className="main">
        <Feed authorName={authorName} onAuthorNameChange={setAuthorName} />
      </main>

      <footer className="footer">
        <p>drift · text, photos &amp; video · built with React and Flask</p>
      </footer>
    </div>
  );
}
