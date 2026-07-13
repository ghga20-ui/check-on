import { useId } from "react";

/**
 * 체크온 brand glyph: white school bell with the check knocked out, for use
 * on the blue brand containers (.login-mark / .splash-mark). Mirrors
 * public/icon.svg — keep the two in sync when the mark changes.
 */
export default function BrandMark({ size = 36 }: { size?: number }) {
  const maskId = useId();
  return (
    <svg width={size} height={size} viewBox="0 0 512 512" aria-hidden="true">
      <mask id={maskId}>
        <rect width="512" height="512" fill="#fff" />
        <path
          d="M204 244 L242 282 L314 198"
          fill="none"
          stroke="#000"
          strokeWidth="42"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </mask>
      <path
        d="M256 88 C170 88 138 158 138 244 V328 L100 384 H412 L374 328 V244 C374 158 342 88 256 88 Z"
        fill="currentColor"
        mask={`url(#${maskId})`}
      />
      <circle cx="256" cy="428" r="26" fill="currentColor" />
    </svg>
  );
}
