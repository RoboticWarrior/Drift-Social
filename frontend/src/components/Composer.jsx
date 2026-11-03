import { useEffect, useMemo, useRef, useState } from "react";
import Avatar from "./Avatar.jsx";
import { CloseIcon, ImageIcon, SendIcon, VideoIcon } from "./Icons.jsx";
import { createPost } from "../api.js";
import { isVideoFile } from "../utils.js";

const MAX_FILES = 6;
const MAX_CHARS = 2000;

export default function Composer({ authorName, onAuthorNameChange, onPosted }) {
  const [text, setText] = useState("");
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  const imageInput = useRef(null);
  const videoInput = useRef(null);
  const textarea = useRef(null);

  const previews = useMemo(
    () => files.map((file) => ({ file, url: URL.createObjectURL(file), video: isVideoFile(file) })),
    [files]
  );

  useEffect(() => () => previews.forEach((preview) => URL.revokeObjectURL(preview.url)), [previews]);

  const addFiles = (incoming) => {
    const list = Array.from(incoming || []);
    if (list.length === 0) return;
    setError(null);
    setFiles((current) => {
      const room = MAX_FILES - current.length;
      if (room <= 0) {
        setError(`Up to ${MAX_FILES} files per post.`);
        return current;
      }
      if (list.length > room) setError(`Only ${MAX_FILES} files per post — added the first ${room}.`);
      return [...current, ...list.slice(0, room)];
    });
  };

  const removeFile = (index) => setFiles((current) => current.filter((_, i) => i !== index));

  const canPost = !busy && (text.trim().length > 0 || files.length > 0);

  const submit = async (event) => {
    event.preventDefault();
    if (!canPost) return;

    setBusy(true);
    setError(null);
    setProgress(0);
    try {
      const data = await createPost({
        text: text.trim(),
        authorName: authorName.trim() || "You",
        files,
        onProgress: setProgress,
      });
      onPosted(data.post);
      setText("");
      setFiles([]);
      setProgress(0);
      textarea.current?.focus();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const remaining = MAX_CHARS - text.length;
  const authorHandle = (authorName.trim() || "You").toLowerCase().replace(/[^a-z0-9_]+/g, "") || "you";

  return (
    <form className="composer" onSubmit={submit}>
      <div className="composer__top">
        <Avatar name={authorName.trim() || "You"} handle={authorHandle} size={40} />
        <div className="composer__field">
          <label className="sr-only" htmlFor="composer-name">
            Your display name
          </label>
          <input
            id="composer-name"
            className="composer__name"
            value={authorName}
            onChange={(event) => onAuthorNameChange(event.target.value.slice(0, 40))}
            placeholder="Your name"
            maxLength={40}
            spellCheck="false"
          />
          <label className="sr-only" htmlFor="composer-text">
            Write a post
          </label>
          <textarea
            id="composer-text"
            ref={textarea}
            className="composer__text"
            placeholder="What's on your mind?"
            value={text}
            onChange={(event) => setText(event.target.value.slice(0, MAX_CHARS))}
            rows={text.length > 90 ? 4 : 2}
            onKeyDown={(event) => {
              if ((event.metaKey || event.ctrlKey) && event.key === "Enter") submit(event);
            }}
          />
        </div>
      </div>

      {previews.length > 0 && (
        <div className="composer__previews">
          {previews.map((preview, index) => (
            <figure className="preview" key={`${preview.file.name}-${index}`}>
              {preview.video ? (
                <video className="preview__media" src={preview.url} muted playsInline preload="metadata" />
              ) : (
                <img className="preview__media" src={preview.url} alt="" />
              )}
              <span className="preview__kind">{preview.video ? "video" : "photo"}</span>
              <button
                type="button"
                className="preview__remove"
                onClick={() => removeFile(index)}
                aria-label={`Remove ${preview.file.name}`}
              >
                <CloseIcon width="14" height="14" />
              </button>
            </figure>
          ))}
        </div>
      )}

      {error && <p className="composer__error" role="alert">{error}</p>}

      {busy && (
        <div className="composer__progress" role="status" aria-live="polite">
          <span style={{ width: `${Math.max(progress, 6)}%` }} />
          <em>{progress < 100 ? `Uploading… ${progress}%` : "Posting…"}</em>
        </div>
      )}

      <div className="composer__bar">
        <div className="composer__tools">
          <input
            ref={imageInput}
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            multiple
            hidden
            onChange={(event) => {
              addFiles(event.target.files);
              event.target.value = "";
            }}
          />
          <input
            ref={videoInput}
            type="file"
            accept="video/mp4,video/webm,video/quicktime"
            multiple
            hidden
            onChange={(event) => {
              addFiles(event.target.files);
              event.target.value = "";
            }}
          />
          <button type="button" className="tool" onClick={() => imageInput.current?.click()} disabled={busy}>
            <ImageIcon width="18" height="18" />
            Photo
          </button>
          <button type="button" className="tool" onClick={() => videoInput.current?.click()} disabled={busy}>
            <VideoIcon width="18" height="18" />
            Video
          </button>
        </div>

        <div className="composer__actions">
          {text.length > MAX_CHARS - 200 && (
            <span className={`composer__count${remaining < 0 ? " composer__count--over" : ""}`}>{remaining}</span>
          )}
          <button type="submit" className="postbutton" disabled={!canPost}>
            <SendIcon width="16" height="16" />
            {busy ? "Posting…" : "Post"}
          </button>
        </div>
      </div>
    </form>
  );
}
