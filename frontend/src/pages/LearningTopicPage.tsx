import type { JSX } from 'preact';
import { useState } from 'preact/hooks';
import { PageLayout } from '../components/Layout/PageLayout';
import { ChevronLeftIcon } from '../components/shared/icons';
import { SeedlingIcon } from '../components/shared/icons/SeedlingIcon';
import { getAccentPalette } from '../lib/accent-palette';
import { LEARNING_TOPICS, type LearningSection } from '../data/learning-topics';

export interface LearningTopicPageProps {
  slug: string;
  onBack: () => void;
}

const ACCENT = getAccentPalette('learning');

function ExternalLinkIcon(): JSX.Element {
  return (
    <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
      className="inline-block shrink-0 opacity-50 group-hover/link:opacity-100">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  );
}

function SectionAccordion({ section, index, isOpen, onToggle }: {
  section: LearningSection;
  index: number;
  isOpen: boolean;
  onToggle: () => void;
}): JSX.Element {
  return (
    <div className="overflow-hidden rounded-2xl border border-[var(--color-border-subtle,#e5e7eb)] bg-[var(--color-bg-surface,white)]">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between px-5 py-4 text-left transition-colors hover:bg-[var(--color-neutral-50)]"
      >
        <div className="flex items-center gap-3">
          <span
            className="flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold"
            style={{ backgroundColor: ACCENT.light, color: ACCENT.text }}
          >
            {index + 1}
          </span>
          <span className="text-base font-semibold text-[var(--color-text-primary)]">
            {section.title}
          </span>
          <span className="text-xs text-[var(--color-text-muted)]">
            ({section.lessons.length})
          </span>
        </div>
        <svg
          width={20} height={20} viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          className={`shrink-0 text-[var(--color-text-muted)] transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          aria-hidden="true"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {isOpen && (
        <div className="border-t border-[var(--color-border-subtle,#e5e7eb)] px-5 py-3">
          <ol className="space-y-1">
            {section.lessons.map((lesson, i) => (
              <li key={i} className="group/link flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-[var(--color-neutral-50)]">
                <span className="w-6 shrink-0 text-right text-xs font-medium text-[var(--color-text-muted)]">
                  {i + 1}.
                </span>
                {lesson.url ? (
                  <a
                    href={lesson.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex flex-1 items-center gap-1.5 text-[var(--color-text-primary)] hover:text-[var(--color-mode-learning-border)]"
                  >
                    {lesson.title}
                    <ExternalLinkIcon />
                  </a>
                ) : (
                  <span className="flex-1 text-[var(--color-text-secondary)]">
                    {lesson.title}
                  </span>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

export function LearningTopicPage({ slug, onBack }: LearningTopicPageProps): JSX.Element {
  const topic = LEARNING_TOPICS.find(t => t.slug === slug);
  const [openSections, setOpenSections] = useState<Set<number>>(() => new Set([0]));

  if (!topic) {
    return (
      <PageLayout variant="single-column" mode="learning">
        <PageLayout.Content className="mx-auto w-full max-w-3xl px-4 py-6 md:px-8">
          <button
            type="button"
            onClick={onBack}
            className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
          >
            <ChevronLeftIcon size={16} />
            Back to Learn Go
          </button>
          <p className="text-[var(--color-text-secondary)]">Topic not found.</p>
        </PageLayout.Content>
      </PageLayout>
    );
  }

  const totalLessons = topic.sections.reduce((sum, s) => sum + s.lessons.length, 0);
  const lessonsWithLinks = topic.sections.reduce(
    (sum, s) => sum + s.lessons.filter(l => l.url).length, 0
  );

  const toggleSection = (index: number): void => {
    setOpenSections(prev => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const expandAll = (): void => {
    setOpenSections(new Set(topic.sections.map((_, i) => i)));
  };

  const collapseAll = (): void => {
    setOpenSections(new Set());
  };

  return (
    <PageLayout variant="single-column" mode="learning">
      <PageLayout.Content className="mx-auto w-full max-w-3xl px-4 py-6 md:px-8">
          {/* Back button */}
          <button
            type="button"
            onClick={onBack}
            className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
          >
            <ChevronLeftIcon size={16} />
            Back to Learn Go
          </button>

          {/* Header */}
          <div className="mb-6 flex items-start gap-4">
            <div
              className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full"
              style={{ backgroundColor: ACCENT.light }}
            >
              <SeedlingIcon size={28} />
            </div>
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">{topic.title}</h1>
              <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{topic.description}</p>
              <div className="mt-2 flex flex-wrap gap-2 text-xs font-semibold text-[var(--color-text-muted)]">
                <span
                  className="rounded-md px-2 py-0.5"
                  style={{ backgroundColor: ACCENT.light, color: ACCENT.text }}
                >
                  {topic.sections.length} {topic.sections.length === 1 ? 'section' : 'sections'}
                </span>
                <span>{totalLessons} lessons</span>
                {lessonsWithLinks > 0 && (
                  <span>{lessonsWithLinks} interactive puzzles</span>
                )}
              </div>
            </div>
          </div>

          {/* Expand/collapse controls */}
          {topic.sections.length > 1 && (
            <div className="mb-4 flex gap-2">
              <button
                type="button"
                onClick={expandAll}
                className="rounded-lg px-3 py-1.5 text-xs font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-neutral-100)] hover:text-[var(--color-text-primary)]"
              >
                Expand All
              </button>
              <button
                type="button"
                onClick={collapseAll}
                className="rounded-lg px-3 py-1.5 text-xs font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-neutral-100)] hover:text-[var(--color-text-primary)]"
              >
                Collapse All
              </button>
            </div>
          )}

          {/* Section accordions */}
          <div className="space-y-3">
            {topic.sections.map((section, i) => (
              <SectionAccordion
                key={i}
                section={section}
                index={i}
                isOpen={openSections.has(i)}
                onToggle={() => toggleSection(i)}
              />
            ))}
          </div>
      </PageLayout.Content>
    </PageLayout>
  );
}
