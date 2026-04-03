/**
 * User Profile Component
 *
 * Displays user avatar in top-right of header.
 * Settings (dark mode, sound) have moved to SettingsGear component.
 * Profile button now just shows the user icon — no dropdown.
 *
 * Spec 127: T039, T040, T041, T043
 */

export interface UserProfileProps {
  /** Optional username to display */
  username?: string;
  /** Optional avatar URL */
  avatarUrl?: string;
  /** Click handler for navigating to profile/progress */
  onClick?: () => void;
}

/**
 * Default User Icon - Profile silhouette SVG
 * Clean, minimal design following Apple HIG
 */
function DefaultUserIcon({ size = 24 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <circle cx="12" cy="8" r="4" fill="currentColor" opacity="0.7" />
      <path d="M4 20c0-4 4-6 8-6s8 2 8 6" fill="currentColor" opacity="0.7" />
    </svg>
  );
}

/**
 * User Profile — avatar button only (settings moved to SettingsGear).
 */
export function UserProfile({ username, avatarUrl, onClick }: UserProfileProps) {
  return (
    <button
      className="flex items-center justify-center rounded-full p-1 text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-secondary)]"
      aria-label={username ? `${username}'s profile` : 'User profile'}
      onClick={onClick}
    >
      {avatarUrl ? (
        <img src={avatarUrl} alt="" className="h-8 w-8 rounded-full" />
      ) : (
        <DefaultUserIcon size={20} />
      )}
    </button>
  );
}

export default UserProfile;
