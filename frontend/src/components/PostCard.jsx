import { useEffect, useRef, useState } from "react";
import Avatar from "./Avatar.jsx";
import MediaGrid from "./MediaGrid.jsx";
import Lightbox from "./Lightbox.jsx";
import { HeartIcon } from "./Icons.jsx";
import { formatCount, timeAgo } from "../utils.js";

export default function PostCard({ post, onLike }) {
  const [lightbox, setLightbox] = useState(null);
  const [pop, setPop] = useState(false);
  const popTimeout = useRef(null);

  useEffect(() => () => clearTimeout(popTimeout.current), []);

  const handleLike = () => {
    onLike(post);
    if (!post.likes.liked) {
      setPop(true);
      clearTimeout(popTimeout.current);
      popTimeout.current = setTimeout(() => setPop(false), 420);
    }
  };

  const liked = post.likes.liked;

  return (
    <article className="post">
      <header className="post__head">
        <Avatar name={post.author.name} handle={post.author.handle} />
        <div className="post__who">
          <span className="post__name">{post.author.name}</span>
          <span className="post__meta">
            @{post.author.handle}
            <span className="post__sep" aria-hidden="true">·</span>
            <time dateTime={post.createdAt} title={new Date(post.createdAt).toLocaleString()}>
              {timeAgo(post.createdAt)}
            </time>
          </span>
        </div>
      </header>

      {post.text && <p className="post__text">{post.text}</p>}

      <MediaGrid media={post.media} onOpen={(index) => setLightbox(index)} />

      <footer className="post__foot">
        <button
          type="button"
          className={`like${liked ? " like--on" : ""}${pop ? " like--pop" : ""}`}
          onClick={handleLike}
          aria-pressed={liked}
          aria-label={liked ? "Unlike this post" : "Like this post"}
        >
          <HeartIcon filled={liked} width="18" height="18" />
          <span>{post.likes.count > 0 ? formatCount(post.likes.count) : "Like"}</span>
        </button>
        {post.media.length > 0 && (
          <span className="post__type">
            {post.media.some((item) => item.kind === "video") ? "video" : "photo"}
            {post.media.length > 1 ? ` × ${post.media.length}` : ""}
          </span>
        )}
      </footer>

      {lightbox !== null && (
        <Lightbox media={post.media} index={lightbox} onClose={() => setLightbox(null)} />
      )}
    </article>
  );
}
