// Brand mark: a wave in a rounded square. Plain SVG, no image file needed.
export default function Logo({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#1f9aa8" />
      <path d="M5 19c3-4 6-4 9 0s6 4 9 0 4-3 4-3" stroke="#ffffff" strokeWidth="3" fill="none" strokeLinecap="round" />
      <path d="M5 12c3-3 6-3 9 0s6 3 9 0" stroke="#ffffff" strokeOpacity="0.55" strokeWidth="2" fill="none" strokeLinecap="round" />
    </svg>
  );
}