import type { JSX } from 'preact';
import { useState, useCallback } from 'preact/hooks';
import { PageLayout } from '../components/Layout/PageLayout';
import { ChevronLeftIcon } from '../components/shared/icons';
import { SeedlingIcon } from '../components/shared/icons/SeedlingIcon';
import { LightningIcon } from '../components/shared/icons/LightningIcon';
import { TesujiIcon } from '../components/shared/icons/TesujiIcon';
import { TechniqueKeyIcon } from '../components/shared/icons/TechniqueKeyIcon';
import { GridIcon } from '../components/shared/icons/GridIcon';
import { getAccentPalette } from '../lib/accent-palette';
import {
  LEARNING_TOPICS,
  LEARNING_TIERS,
  type LearningTopic,
  type LearningSection,
  type TopicIcon,
  type LearningTier,
} from '../data/learning-topics';

export interface LearningPageProps {
  onNavigateHome: () => void;
}

const ACCENT = getAccentPalette('learning');

// ============================================================================
// Tier visual config — each tier gets a subtle icon and description
// ============================================================================

const TIER_CONFIG: Record<LearningTier, { emoji: string; description: string }> = {
  foundations: {
    emoji: '\u{1F331}',
    description: 'Build a solid foundation — capturing, eyes, territory, and basic reading.',
  },
  'building-strength': {
    emoji: '\u{1F4AA}',
    description: 'Deepen your skills — life & death patterns, tesuji, and advanced techniques.',
  },
  advancing: {
    emoji: '\u{1F3AF}',
    description: 'Sharpen for dan-level play — endgame precision, openings, and mastery.',
  },
};

// ============================================================================
// Icons
// ============================================================================

function getTopicIcon(icon: TopicIcon, size = 24): JSX.Element {
  const color = 'var(--color-mode-learning-border, #06b6d4)';
  switch (icon) {
    case 'seedling':
      return <SeedlingIcon size={size} color={color} />;
    case 'grid':
      return <GridIcon size={size} />;
    case 'lightning':
      return <LightningIcon size={size} color={color} />;
    case 'trendUp':
      return (
        <svg
          width={size}
          height={size}
          viewBox="0 0 24 24"
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
          <polyline points="16 7 22 7 22 13" />
        </svg>
      );
    case 'star':
      return (
        <svg
          width={size}
          height={size}
          viewBox="0 0 24 24"
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
        </svg>
      );
    case 'tesuji':
      return <TesujiIcon size={size} color={color} />;
    case 'techniqueKey':
      return <TechniqueKeyIcon size={size} color={color} />;
    case 'compass':
      return (
        <svg
          width={size}
          height={size}
          viewBox="0 0 24 24"
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="10" />
          <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
        </svg>
      );
    case 'hint':
      return <SeedlingIcon size={size} color={color} />;
  }
}

function ExternalLinkIcon(): JSX.Element {
  return (
    <svg
      width={14}
      height={14}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="inline-block shrink-0 opacity-0 transition-opacity group-hover/link:opacity-60"
    >
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  );
}

function ChevronDownIcon({ open }: { open: boolean }): JSX.Element {
  return (
    <svg
      width={18}
      height={18}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`shrink-0 text-[var(--color-text-muted)] transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
      aria-hidden="true"
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

// ============================================================================
// Helpers
// ============================================================================

function countLessons(topic: LearningTopic): number {
  return topic.sections.reduce((sum, s) => sum + s.lessons.length, 0);
}

function countLinks(topic: LearningTopic): number {
  return topic.sections.reduce((sum, s) => sum + s.lessons.filter((l) => l.url).length, 0);
}

// ============================================================================
// Subcomponents
// ============================================================================

// Strip "Part N: " prefix since the section circle already shows the number
function stripPartPrefix(title: string): string {
  return title.replace(/^Part\s+\d+:\s*/, '');
}

// Detect quiz/review items by title
function isQuizItem(title: string): boolean {
  return /^quiz\b|quiz\s*\d/i.test(title);
}

/** Single section — banner header + responsive 2-column grid with quiz checkpoints */
function SectionBlock({
  section,
  sectionIndex,
}: {
  section: LearningSection;
  sectionIndex: number;
}): JSX.Element {
  const displayTitle = stripPartPrefix(section.title);

  return (
    <div>
      {/* ── Section header — lightweight signpost: circle + bold label + thin top rule ── */}
      {sectionIndex > 0 && (
        <div className="mb-2 mt-1 border-t border-[var(--color-border-subtle,#334155)]" />
      )}
      <div className="mb-2 flex items-center gap-2.5 px-1 py-1.5">
        <span
          className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-extrabold"
          style={{ backgroundColor: ACCENT.border, color: '#fff' }}
        >
          {sectionIndex + 1}
        </span>
        <span className="flex-1 text-[13px] font-bold text-[var(--color-text-primary)]">
          {displayTitle}
        </span>
        <span className="shrink-0 text-[10px] font-medium text-[var(--color-text-muted)]">
          {section.lessons.length}
        </span>
      </div>

      {/* ── Lessons — responsive 2-col grid with full-width quiz checkpoints ── */}
      <ol className="grid grid-cols-1 gap-x-2 gap-y-px pl-0.5 sm:grid-cols-2">
        {section.lessons.map((lesson, i) => {
          const isQuiz = isQuizItem(lesson.title);

          // Quiz items span full width as checkpoint milestones
          if (isQuiz) {
            return (
              <li
                key={i}
                className={`col-span-1 sm:col-span-2 my-0.5 flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-semibold transition-colors ${
                  lesson.url ? 'group/link hover:brightness-110' : ''
                }`}
                style={{ backgroundColor: 'rgba(251, 191, 36, 0.08)' }}
              >
                {/* Amber star marker */}
                <span
                  className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px]"
                  style={{ backgroundColor: 'rgba(251, 191, 36, 0.2)', color: '#fbbf24' }}
                >
                  &#9733;
                </span>
                {lesson.url ? (
                  <a
                    href={lesson.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex min-w-0 flex-1 items-center gap-1.5 no-underline transition-colors"
                    style={{ color: '#fbbf24' }}
                    title={lesson.title}
                  >
                    <span className="truncate">Review</span>
                    <ExternalLinkIcon />
                  </a>
                ) : (
                  <span
                    className="flex-1 truncate text-[var(--color-text-muted)]"
                    title={lesson.title}
                  >
                    Review
                  </span>
                )}
              </li>
            );
          }

          // Regular lesson items
          return (
            <li
              key={i}
              className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-[13px] leading-tight transition-colors ${
                lesson.url ? 'group/link hover:bg-[var(--color-neutral-100)]' : ''
              }`}
            >
              {/* Ordinal pill */}
              <span
                className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md text-[10px] font-semibold tabular-nums ${
                  lesson.url ? '' : 'bg-[var(--color-neutral-100)] text-[var(--color-text-muted)]'
                }`}
                style={
                  lesson.url ? { backgroundColor: ACCENT.light, color: ACCENT.text } : undefined
                }
              >
                {i + 1}
              </span>

              {/* Title + link */}
              {lesson.url ? (
                <a
                  href={lesson.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex min-w-0 flex-1 items-center gap-1 text-[var(--color-text-primary)] no-underline transition-colors hover:text-[var(--color-mode-learning-border)]"
                  title={lesson.title}
                >
                  <span className="truncate">{lesson.title}</span>
                  <ExternalLinkIcon />
                </a>
              ) : (
                <span
                  className="flex-1 truncate text-[var(--color-text-muted)]"
                  title={lesson.title}
                >
                  {lesson.title}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

/** Expanded topic content — flat sections (no accordion) with scroll */
function TopicExpanded({ topic }: { topic: LearningTopic }): JSX.Element {
  return (
    <div className="mt-4 border-t border-[var(--color-border-subtle,#e5e7eb)] pt-4">
      {/* Description */}
      <p className="mb-4 text-sm leading-relaxed text-[var(--color-text-secondary)]">
        {topic.description}
      </p>

      {/* All sections — scrollable if content is long */}
      <div className="max-h-[520px] space-y-5 overflow-y-auto pr-1">
        {topic.sections.map((section, i) => (
          <SectionBlock key={i} section={section} sectionIndex={i} />
        ))}
      </div>
    </div>
  );
}

/** Topic card — HomeTile DNA: rounded-3xl, shadow, accent bottom border, hover lift */
function TopicCard({
  topic,
  isExpanded,
  onToggle,
}: {
  topic: LearningTopic;
  isExpanded: boolean;
  onToggle: () => void;
}): JSX.Element {
  const lessonCount = countLessons(topic);
  const linkCount = countLinks(topic);

  return (
    <div
      className={`
        rounded-3xl bg-[var(--color-bg-panel,white)] shadow-md
        border-b-[6px] border-l-0 border-r-0 border-t-0
        transition-all duration-300 ease-out
        ${isExpanded ? 'shadow-lg' : 'hover:shadow-xl'}
      `}
      style={{ borderBottomColor: ACCENT.border }}
    >
      {/* Card header — clickable */}
      <button
        type="button"
        onClick={onToggle}
        className={`
          flex w-full items-center gap-4 p-6 text-left
          transition-colors duration-200
          ${isExpanded ? '' : 'hover:-translate-y-0.5'}
          cursor-pointer rounded-t-3xl
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]
        `}
        aria-expanded={isExpanded}
      >
        {/* Icon circle — 56px, matching HomeTile proportions */}
        <div
          className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full"
          style={{ backgroundColor: ACCENT.bg }}
        >
          {getTopicIcon(topic.icon, 28)}
        </div>

        {/* Text content */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="m-0 truncate text-lg font-bold text-[var(--color-text-primary)]">
              {topic.title}
            </h3>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            {/* Difficulty badge */}
            <span
              className="inline-flex items-center rounded-lg px-2 py-0.5 text-xs font-bold"
              style={{ backgroundColor: ACCENT.light, color: ACCENT.text }}
            >
              {topic.difficultyRange}
            </span>
            {/* Section count */}
            <span className="text-xs text-[var(--color-text-muted)]">
              {topic.sections.length} {topic.sections.length === 1 ? 'section' : 'sections'}
            </span>
            {/* Lesson count */}
            <span className="text-xs text-[var(--color-text-muted)]">{lessonCount} lessons</span>
            {/* Puzzle link count (if different from total) */}
            {linkCount > 0 && linkCount < lessonCount && (
              <span className="text-xs text-[var(--color-text-muted)]">{linkCount} puzzles</span>
            )}
          </div>
        </div>

        {/* Expand chevron */}
        <ChevronDownIcon open={isExpanded} />
      </button>

      {/* Expanded content — inside the card */}
      {isExpanded && (
        <div className="px-6 pb-6">
          <TopicExpanded topic={topic} />
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Main Page
// ============================================================================

export function LearningPage({ onNavigateHome }: LearningPageProps): JSX.Element {
  const [expandedTopics, setExpandedTopics] = useState<Set<string>>(new Set());

  const toggleTopic = useCallback((slug: string) => {
    setExpandedTopics((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  }, []);

  const activeTopics = LEARNING_TOPICS.filter((t) => t.status === 'active');
  const totalLessons = activeTopics.reduce((sum, t) => sum + countLessons(t), 0);
  const totalLinks = activeTopics.reduce((sum, t) => sum + countLinks(t), 0);

  return (
    <PageLayout variant="single-column" mode="learning">
      <PageLayout.Content>
        {/* ================================================================
            Hero Header — TechniqueBrowsePage DNA: accent-light bg, icon,
            stat badges, bold typography
        ================================================================ */}
        <div className="px-4 pb-5 pt-4" style={{ backgroundColor: ACCENT.light }}>
          <div className="mx-auto max-w-5xl">
            {/* Back button */}
            <button
              type="button"
              onClick={onNavigateHome}
              className="mb-3 inline-flex cursor-pointer items-center gap-1 rounded-lg border-none bg-transparent px-2 py-1.5 text-sm font-medium text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-elevated)] hover:text-[var(--color-text-primary)]"
              aria-label="Go back home"
            >
              <ChevronLeftIcon size={14} /> Back
            </button>

            {/* Title row: icon + title + subtitle */}
            <div className="flex items-center gap-4">
              <div
                className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full md:h-[72px] md:w-[72px]"
                style={{ backgroundColor: ACCENT.bg }}
              >
                <SeedlingIcon size={28} />
              </div>
              <div>
                <h1
                  className="m-0 text-3xl tracking-tight sm:text-4xl lg:text-5xl text-[var(--color-text-primary)]"
                  style={{ fontWeight: 800, lineHeight: 1.1 }}
                >
                  Learn Go
                </h1>
                <p
                  className="m-0 mt-1.5 text-sm text-[var(--color-text-muted)] sm:text-base"
                  style={{ fontWeight: 500 }}
                >
                  Interactive puzzles from beginner to dan
                </p>
              </div>
            </div>

            {/* Stat trio — big numbers with small labels */}
            <div className="mt-5 flex gap-6 sm:gap-8">
              <div className="flex flex-col">
                <span className="text-2xl font-bold tabular-nums text-[var(--color-text-primary)] sm:text-3xl">
                  {activeTopics.length}
                </span>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                  Topics
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-2xl font-bold tabular-nums text-[var(--color-text-primary)] sm:text-3xl">
                  {totalLessons}
                </span>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                  Lessons
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-2xl font-bold tabular-nums text-[var(--color-text-primary)] sm:text-3xl">
                  {totalLinks}
                </span>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                  Puzzles
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ================================================================
            Content — Tier sections with topic cards
        ================================================================ */}
        <div className="mx-auto max-w-5xl px-4 py-6">
          {LEARNING_TIERS.map((tier) => {
            const tierTopics = activeTopics.filter((t) => t.tier === tier.id);
            if (tierTopics.length === 0) return null;

            const tierConfig = TIER_CONFIG[tier.id];
            const tierLessons = tierTopics.reduce((s, t) => s + countLessons(t), 0);

            return (
              <section key={tier.id} className="mb-10">
                {/* Tier header */}
                <div className="mb-4">
                  <div className="flex items-baseline gap-2">
                    <h2 className="m-0 text-2xl font-bold tracking-tight sm:text-3xl text-[var(--color-text-primary)]">
                      {tier.title}
                    </h2>
                    <span className="text-sm font-medium text-[var(--color-text-muted)]">
                      {tier.subtitle}
                    </span>
                    <span className="text-xs text-[var(--color-text-muted)]">
                      {tierLessons} lessons
                    </span>
                  </div>
                  <p className="m-0 mt-1 text-sm text-[var(--color-text-muted)]">
                    {tierConfig.description}
                  </p>
                </div>

                {/* Topic cards — single column for clean expansion */}
                <div className="space-y-4">
                  {tierTopics.map((topic) => (
                    <TopicCard
                      key={topic.slug}
                      topic={topic}
                      isExpanded={expandedTopics.has(topic.slug)}
                      onToggle={() => toggleTopic(topic.slug)}
                    />
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      </PageLayout.Content>
    </PageLayout>
  );
}
