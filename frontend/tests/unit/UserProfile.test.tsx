/**
 * Unit tests for UserProfile component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/preact';
import { UserProfile } from '@/components/Layout/UserProfile';

describe('UserProfile', () => {
  it('renders without onClick (no crash)', () => {
    const { getByRole } = render(<UserProfile />);
    const btn = getByRole('button');
    expect(btn).toBeTruthy();
    // clicking should not throw
    fireEvent.click(btn);
  });

  it('calls onClick when button is clicked', () => {
    const onClick = vi.fn();
    const { getByRole } = render(<UserProfile onClick={onClick} />);
    fireEvent.click(getByRole('button'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('renders with username', () => {
    const { getByRole } = render(<UserProfile username="Alice" />);
    const btn = getByRole('button');
    expect(btn.getAttribute('aria-label')).toBe("Alice's profile");
  });

  it('renders default icon when no avatarUrl', () => {
    const { container } = render(<UserProfile />);
    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
  });

  it('renders avatar image when avatarUrl provided', () => {
    const { container } = render(<UserProfile avatarUrl="https://example.com/avatar.png" />);
    const img = container.querySelector('img');
    expect(img).toBeTruthy();
    expect(img?.getAttribute('src')).toBe('https://example.com/avatar.png');
  });
});
