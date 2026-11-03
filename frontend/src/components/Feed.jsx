import { useCallback, useEffect, useRef, useState } from "react";
import Composer from "./Composer.jsx";
import PostCard from "./PostCard.jsx";
import { RefreshIcon } from "./Icons.jsx";
import { fetchPosts, setLike } from "../api.js";

const PAGE_SIZE = 6;

export default function Feed({ authorName, onAuthorNameChange }) {
  const [posts, setPosts] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [hasMore, setHasMore] = useState(true);
  const [initialLoading, setInitialLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);

  const sentinel = useRef(null);
  const loadingRef = useRef(false);

  const loadPage = useCallback(async (before) => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    if (before == null) setInitialLoading(true);
    else setLoadingMore(true);
    setError(null);
    try {
      const data = await fetchPosts({ cursor: before, limit: PAGE_SIZE });
      setPosts((current) => (before == null ? data.posts : [...current, ...data.posts]));
      setCursor(data.nextCursor);
      setHasMore(Boolean(data.nextCursor));
    } catch (err) {
      setError(err.message);
    } finally {
      loadingRef.current = false;
      setInitialLoading(false);
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    loadPage(null);
  }, [loadPage]);

  useEffect(() => {
    const node = sentinel.current;
    if (!node || !hasMore || initialLoading) return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !loadingRef.current) loadPage(cursor);
      },
      { rootMargin: "700px 0px" }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [cursor, hasMore, initialLoading, loadPage]);

  const handleLike = async (post) => {
    const nextLiked = !post.likes.liked;
    const optimistic = {
      ...post,
      likes: { liked: nextLiked, count: Math.max(0, post.likes.count + (nextLiked ? 1 : -1)) },
    };
    setPosts((current) => current.map((item) => (item.id === post.id ? optimistic : item)));
    try {
      const result = await setLike(post.id, nextLiked);
      setPosts((current) =>
        current.map((item) =>
          item.id === post.id ? { ...item, likes: { liked: result.liked, count: result.count } } : item
        )
      );
    } catch {
      setPosts((current) => current.map((item) => (item.id === post.id ? post : item)));
    }
  };

  const handlePosted = (post) => {
    setPosts((current) => [post, ...current]);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="feed">
      <Composer authorName={authorName} onAuthorNameChange={onAuthorNameChange} onPosted={handlePosted} />

      <div className="feed__label">
        <span>latest</span>
        <span className="feed__line" aria-hidden="true" />
      </div>

      {initialLoading && (
        <div className="skeletons" aria-label="Loading posts">
          {[0, 1, 2].map((index) => (
            <div className="skeleton" key={index}>
              <div className="skeleton__row">
                <span className="skeleton__avatar" />
                <span className="skeleton__lines">
                  <span className="skeleton__line skeleton__line--short" />
                  <span className="skeleton__line skeleton__line--tiny" />
                </span>
              </div>
              <span className="skeleton__line" />
              <span className="skeleton__line skeleton__line--medium" />
              <span className="skeleton__block" />
            </div>
          ))}
        </div>
      )}

      {!initialLoading && posts.length === 0 && !error && (
        <div className="empty">
          <h2>It's quiet in here</h2>
          <p>Be the first to post a thought, a photo, or a video.</p>
        </div>
      )}

      {posts.map((post) => (
        <PostCard key={post.id} post={post} onLike={handleLike} />
      ))}

      {error && (
        <div className="errorbox" role="alert">
          <p>{error}</p>
          <button type="button" className="ghost" onClick={() => loadPage(posts.length ? cursor : null)}>
            <RefreshIcon width="16" height="16" />
            Try again
          </button>
        </div>
      )}

      {loadingMore && <div className="feed__more">Loading more…</div>}

      <div ref={sentinel} className="feed__sentinel" aria-hidden="true" />

      {!hasMore && posts.length > 0 && (
        <p className="feed__end">You're all caught up · {posts.length} posts</p>
      )}
    </div>
  );
}
