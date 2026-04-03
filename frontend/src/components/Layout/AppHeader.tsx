/**
 * App Header Component
 * 
 * Global header for all pages:
 * - Left: Yen-Go logo and app name
 * - Right: Streak display, gear (settings), user profile
 * 
 * Spec 127: US2, FR-001 — consistent header across all pages.
 * Tailwind utility classes only, no CSS file.
 */

import { YenGoLogo, YenGoLogoWithText } from './YenGoLogo';
import { UserProfile } from './UserProfile';
import { SettingsGear } from './SettingsGear';
import { StreakBadge } from '../Streak/StreakDisplay';

export interface AppHeaderProps {
  /** Show streak display (default: true) */
  showStreak?: boolean;
  /** Current streak count */
  streak?: number;
  /** Compact mode: icon-only logo for puzzle player pages. */
  compact?: boolean;
  /** Optional additional right-side content */
  rightContent?: preact.ComponentChildren;
  /** Click handler for profile icon — navigates to progress page */
  onClickProfile?: () => void;
}

/**
 * App Header — consistent header across all pages.
 * Height: 56px. Uses Tailwind classes only.
 */
export function AppHeader({ 
  showStreak = true,
  streak = 0,
  compact = false,
  rightContent,
  onClickProfile 
}: AppHeaderProps) {
  return (
    <header
      className={`relative z-30 flex items-center border-b border-[var(--color-border)] bg-[var(--color-bg-panel)] px-4 ${compact ? 'h-11' : 'h-14'}`}
      role="banner"
    >
      {/* Left: Logo — compact mode shows icon only for puzzle pages */}
      <a
        href={import.meta.env.BASE_URL}
        className="flex items-center"
        aria-label="Go to home page"
        onClick={(e: MouseEvent) => {
          e.preventDefault();
          window.history.pushState(null, '', import.meta.env.BASE_URL);
          window.dispatchEvent(new PopStateEvent('popstate'));
        }}
      >
        {compact ? <YenGoLogo size={24} /> : <YenGoLogoWithText size={28} />}
      </a>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Right: Streak + Gear + Profile */}
      <div className="flex items-center gap-3">
        {rightContent}
        
        {showStreak && streak > 0 && (
          <StreakBadge streak={streak} />
        )}
        
        <SettingsGear />
        <UserProfile {...(onClickProfile ? { onClick: onClickProfile } : {})} />
      </div>
    </header>
  );
}

export default AppHeader;
