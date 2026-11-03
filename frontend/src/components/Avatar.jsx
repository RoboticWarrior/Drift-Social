import { hueFor, initials } from "../utils.js";

export default function Avatar({ name, handle, size = 42 }) {
  const hue = hueFor(handle || name);
  return (
    <span
      className="avatar"
      style={{
        "--avatar-size": `${size}px`,
        background: `linear-gradient(140deg, hsl(${hue} 75% 60%), hsl(${(hue + 58) % 360} 72% 46%))`,
      }}
      aria-hidden="true"
    >
      {initials(name)}
    </span>
  );
}
