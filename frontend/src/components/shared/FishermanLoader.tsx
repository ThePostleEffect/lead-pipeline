import { useEffect, useState } from 'react'

// Phase 1 (0-2s): cast the line
// Phase 2 (2s+):  bobber bobs while waiting
// Phase 3:        triggered by parent when run completes — reel in + fish appears

type Phase = 'casting' | 'waiting' | 'reeling'

const MESSAGES = [
  'Casting the line...',
  'Scanning public records...',
  'Checking bankruptcy filings...',
  'Sifting through CFPB data...',
  'Enriching company data...',
  'Verifying entities...',
  'Scoring leads...',
  'Almost there...',
]

export function FishermanLoader({ reeling }: { reeling: boolean }) {
  const [phase, setPhase] = useState<Phase>('casting')
  const [msgIdx, setMsgIdx] = useState(0)
  const [visible, setVisible] = useState(true)

  // Advance from casting → waiting
  useEffect(() => {
    const t = setTimeout(() => setPhase('waiting'), 2200)
    return () => clearTimeout(t)
  }, [])

  // Cycle status messages
  useEffect(() => {
    const t = setInterval(() => {
      setMsgIdx((i) => (i + 1) % MESSAGES.length)
    }, 3200)
    return () => clearInterval(t)
  }, [])

  // When reeling prop flips, play reel animation then hide
  useEffect(() => {
    if (reeling) {
      setPhase('reeling')
      const t = setTimeout(() => setVisible(false), 1800)
      return () => clearTimeout(t)
    }
  }, [reeling])

  if (!visible) return null

  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 select-none">
      <div className="relative w-64 h-48">
        {/* Water */}
        <div className="absolute bottom-0 left-0 right-0 h-16 rounded-xl overflow-hidden">
          <div className="water-surface" />
        </div>

        {/* Fisherman SVG */}
        <svg
          viewBox="0 0 120 130"
          className="absolute bottom-12 left-6 w-28 h-28"
          style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))' }}
        >
          {/* Body */}
          <ellipse cx="42" cy="90" rx="14" ry="18" fill="var(--color-accent)" opacity="0.9" />
          {/* Head */}
          <circle cx="42" cy="62" r="11" fill="#f5c5a0" />
          {/* Hat */}
          <ellipse cx="42" cy="53" rx="14" ry="4" fill="#7c5c3a" />
          <rect x="36" y="40" width="12" height="14" rx="2" fill="#7c5c3a" />
          {/* Legs */}
          <rect x="34" y="105" width="6" height="14" rx="3" fill="#4a3a2a" />
          <rect x="44" y="105" width="6" height="14" rx="3" fill="#4a3a2a" />
          {/* Arm + rod */}
          <line x1="53" y1="78" x2="105" y2="40" stroke="#7c5c3a" strokeWidth="3" strokeLinecap="round" />
          {/* Fishing line */}
          <line
            x1="105"
            y1="40"
            x2="108"
            y2="95"
            stroke="rgba(255,255,255,0.5)"
            strokeWidth="1.2"
            strokeDasharray={phase === 'casting' ? '4 4' : 'none'}
            className={phase === 'casting' ? 'line-extend' : ''}
          />
          {/* Bobber */}
          {phase !== 'casting' && (
            <g className={phase === 'reeling' ? 'bobber-reel' : 'bobber-bob'}>
              <circle cx="108" cy="97" r="4" fill="#ef4444" />
              <circle cx="108" cy="94" r="4" fill="white" />
            </g>
          )}
          {/* Fish — only visible when reeling */}
          {phase === 'reeling' && (
            <g className="fish-catch">
              <ellipse cx="108" cy="80" rx="8" ry="5" fill="#60a5fa" />
              <polygon points="116,80 122,74 122,86" fill="#3b82f6" />
              <circle cx="104" cy="78" r="1.2" fill="white" />
            </g>
          )}
        </svg>

        {/* Ripple on water */}
        {phase === 'waiting' && (
          <div className="absolute bottom-10 right-12 flex flex-col gap-0.5 items-center">
            <div className="ripple ripple-1" />
            <div className="ripple ripple-2" />
          </div>
        )}
      </div>

      {/* Status message */}
      <div className="flex flex-col items-center gap-2">
        <p
          key={msgIdx}
          className="text-sm text-[var(--color-text-muted)] animate-fade-in"
        >
          {reeling ? '🎣 Got one! Pulling in leads...' : MESSAGES[msgIdx]}
        </p>
        {/* Dot pulse */}
        {!reeling && (
          <div className="flex gap-1.5">
            <span className="dot-pulse dot-1" />
            <span className="dot-pulse dot-2" />
            <span className="dot-pulse dot-3" />
          </div>
        )}
      </div>

      <style>{`
        .water-surface {
          width: 100%;
          height: 100%;
          background: linear-gradient(
            180deg,
            color-mix(in srgb, var(--color-accent) 20%, transparent) 0%,
            color-mix(in srgb, var(--color-accent) 10%, transparent) 100%
          );
          border-radius: 12px;
          position: relative;
          overflow: hidden;
        }
        .water-surface::after {
          content: '';
          position: absolute;
          inset: 0;
          background: repeating-linear-gradient(
            90deg,
            transparent,
            transparent 20px,
            rgba(255,255,255,0.04) 20px,
            rgba(255,255,255,0.04) 40px
          );
          animation: water-shift 3s linear infinite;
        }
        @keyframes water-shift {
          from { transform: translateX(0); }
          to   { transform: translateX(40px); }
        }

        .bobber-bob {
          animation: bob 1.4s ease-in-out infinite;
          transform-origin: 108px 97px;
        }
        @keyframes bob {
          0%, 100% { transform: translateY(0); }
          50%       { transform: translateY(3px); }
        }

        .bobber-reel {
          animation: reel-in 1.6s ease-in forwards;
          transform-origin: 105px 40px;
        }
        @keyframes reel-in {
          from { transform: translate(0, 0); opacity: 1; }
          to   { transform: translate(-60px, -50px); opacity: 0; }
        }

        .fish-catch {
          animation: fish-in 1.6s ease-in forwards;
        }
        @keyframes fish-in {
          0%   { transform: translate(0, 0) rotate(0deg); opacity: 0; }
          20%  { opacity: 1; }
          100% { transform: translate(-55px, -48px) rotate(-30deg); opacity: 0; }
        }

        .line-extend {
          animation: extend 2s ease-out forwards;
          stroke-dashoffset: 80;
          stroke-dasharray: 80;
        }
        @keyframes extend {
          from { stroke-dashoffset: 80; }
          to   { stroke-dashoffset: 0; }
        }

        .ripple {
          border-radius: 50%;
          border: 1px solid color-mix(in srgb, var(--color-accent) 40%, transparent);
          animation: ripple-out 2s ease-out infinite;
        }
        .ripple-1 { width: 12px; height: 6px; animation-delay: 0s; }
        .ripple-2 { width: 20px; height: 8px; animation-delay: 0.6s; }
        @keyframes ripple-out {
          0%   { opacity: 0.8; transform: scale(0.8); }
          100% { opacity: 0;   transform: scale(1.6); }
        }

        .dot-pulse {
          display: inline-block;
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: var(--color-accent);
          opacity: 0.4;
          animation: pulse 1.2s ease-in-out infinite;
        }
        .dot-1 { animation-delay: 0s; }
        .dot-2 { animation-delay: 0.2s; }
        .dot-3 { animation-delay: 0.4s; }
        @keyframes pulse {
          0%, 100% { opacity: 0.2; transform: scale(0.8); }
          50%       { opacity: 1;   transform: scale(1.2); }
        }

        .animate-fade-in {
          animation: fade-in 0.5s ease-out;
        }
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
