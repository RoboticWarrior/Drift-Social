export default function MediaGrid({ media, onOpen }) {
  if (!media?.length) return null;

  const count = media.length;
  const layout = count === 1 ? "single" : count === 2 ? "pair" : "grid";

  return (
    <div className={`media media--${layout}`}>
      {media.map((item, index) => {
        const isVideo = item.kind === "video";
        const wide = layout === "grid" && count % 2 === 1 && index === 0;
        const tileClass = `media__tile${wide ? " media__tile--wide" : ""}`;

        return (
          <div className={tileClass} key={item.id}>
            {isVideo ? (
              <video className="media__video" src={item.url} controls playsInline preload="metadata" />
            ) : (
              <button
                type="button"
                className="media__open"
                onClick={() => onOpen(index)}
                aria-label="Enlarge photo"
              >
                <img
                  className="media__image"
                  src={item.url}
                  alt={item.alt || "Post attachment"}
                  loading={index === 0 ? "eager" : "lazy"}
                  decoding="async"
                />
              </button>
            )}
            {count > 1 && <span className="media__badge">{index + 1}/{count}</span>}
          </div>
        );
      })}
    </div>
  );
}
