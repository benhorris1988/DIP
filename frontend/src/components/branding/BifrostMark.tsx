export function BifrostMark({ size = 28 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="bifrost-arc-1" x1="0" y1="0" x2="40" y2="40">
          <stop offset="0%" stopColor="#2563eb" />
          <stop offset="100%" stopColor="#7c3aed" />
        </linearGradient>
        <linearGradient id="bifrost-arc-2" x1="0" y1="0" x2="40" y2="40">
          <stop offset="0%" stopColor="#7c3aed" />
          <stop offset="100%" stopColor="#ec4899" />
        </linearGradient>
        <linearGradient id="bifrost-arc-3" x1="0" y1="0" x2="40" y2="40">
          <stop offset="0%" stopColor="#ec4899" />
          <stop offset="100%" stopColor="#f59e0b" />
        </linearGradient>
      </defs>
      <path d="M4 30 Q 20 6 36 30" stroke="url(#bifrost-arc-1)" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M8 32 Q 20 14 32 32" stroke="url(#bifrost-arc-2)" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M12 34 Q 20 22 28 34" stroke="url(#bifrost-arc-3)" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}
