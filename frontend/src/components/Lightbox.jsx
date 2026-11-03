import { useEffect } from "react";
import { CloseIcon } from "./Icons.jsx";

export default function Lightbox({ media, index, onClose }) {
  const item = media[index];

  useEffect(() => {
    const onKey = (event) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [onClose]);

  if (!item) return null;

  return (
    <div className="lightbox" role="dialog" aria-modal="true" aria-label="Media viewer" onClick={onClose}>
      <button type="button" className="lightbox__close" onClick={onClose} aria-label="Close viewer">
        <CloseIcon width="20" height="20" />
      </button>
      <div className="lightbox__stage" onClick={(event) => event.stopPropagation()}>
        {item.kind === "video" ? (
          <video className="lightbox__media" src={item.url} controls autoPlay playsInline />
        ) : (
          <img className="lightbox__media" src={item.url} alt={item.alt || "Post attachment"} />
        )}
      </div>
    </div>
  );
}
