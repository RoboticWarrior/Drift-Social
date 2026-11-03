const base = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

export function HeartIcon({ filled = false, ...props }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" {...props}>
      <path
        {...base}
        fill={filled ? "currentColor" : "none"}
        d="M12 20.5s-7.6-4.7-7.6-10A4.4 4.4 0 0 1 12 7.3a4.4 4.4 0 0 1 7.6 3.2c0 5.3-7.6 10-7.6 10Z"
      />
    </svg>
  );
}

export function ImageIcon(props) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" {...props}>
      <rect {...base} x="3" y="4.5" width="18" height="15" rx="3" />
      <circle {...base} cx="8.5" cy="9.5" r="1.6" />
      <path {...base} d="m4 16.5 4.7-4.2a2 2 0 0 1 2.7 0l3 2.7 1.8-1.5a2 2 0 0 1 2.6.1L20 15" />
    </svg>
  );
}

export function VideoIcon(props) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" {...props}>
      <rect {...base} x="2.8" y="5.5" width="13.2" height="13" rx="3" />
      <path {...base} d="m16 11.2 4-2.4a.9.9 0 0 1 1.4.8v4.8a.9.9 0 0 1-1.4.8l-4-2.4Z" />
    </svg>
  );
}

export function CloseIcon(props) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" {...props}>
      <path {...base} d="M6 6l12 12M18 6 6 18" />
    </svg>
  );
}

export function SparkleIcon(props) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" {...props}>
      <path
        d="M12 2.6c.5 4.4 2.5 6.4 6.9 6.9-4.4.5-6.4 2.5-6.9 6.9-.5-4.4-2.5-6.4-6.9-6.9 4.4-.5 6.4-2.5 6.9-6.9Z"
        fill="currentColor"
      />
      <path d="M18.4 15.2c.3 2.2 1.2 3.1 3.4 3.4-2.2.3-3.1 1.2-3.4 3.4-.3-2.2-1.2-3.1-3.4-3.4 2.2-.3 3.1-1.2 3.4-3.4Z" fill="currentColor" opacity=".7" />
    </svg>
  );
}

export function SendIcon(props) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" {...props}>
      <path {...base} d="M4.2 11.4 20 4.5l-6.9 15.8-2-6.9-6.9-2Z" />
    </svg>
  );
}

export function RefreshIcon(props) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" {...props}>
      <path {...base} d="M20 12a8 8 0 1 1-2.5-5.8M20 4v5h-5" />
    </svg>
  );
}
