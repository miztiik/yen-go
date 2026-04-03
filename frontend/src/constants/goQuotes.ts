/**
 * Go Quotes for empty states and inspirational messages
 * @module constants/goQuotes
 *
 * Covers: FR-047 (Empty states with Go quotes)
 */

/**
 * Single Go quote with attribution
 */
export interface GoQuote {
  readonly text: string;
  readonly author: string;
  readonly source?: string;
}

/**
 * Curated collection of Go proverbs and wisdom
 */
export const GO_QUOTES: readonly GoQuote[] = [
  {
    text: 'A journey of a thousand games begins with a single stone.',
    author: 'Go Proverb',
  },
  {
    text: 'The stone that captures may itself be captured.',
    author: 'Go Proverb',
  },
  {
    text: 'If you want to learn to swim, first get into the water.',
    author: 'Go Proverb',
  },
  {
    text: 'In Go, every point counts.',
    author: 'Go Proverb',
  },
  {
    text: 'Lose your first 50 games as quickly as possible.',
    author: 'Go Proverb',
  },
  {
    text: 'Play at the vital point, and your stones will come alive.',
    author: 'Go Proverb',
  },
  {
    text: "Don't peep at a cutting point.",
    author: 'Go Proverb',
  },
  {
    text: 'A ponnuki is worth 30 points.',
    author: 'Go Proverb',
  },
  {
    text: 'Strange things happen at the 1-2 point.',
    author: 'Go Proverb',
  },
  {
    text: 'The hand that plays first guides the game.',
    author: 'Go Proverb',
  },
  {
    text: 'Beginners play atari; masters play to live.',
    author: 'Go Proverb',
  },
  {
    text: 'A captured group at the edge is worth more than influence.',
    author: 'Go Proverb',
  },
  {
    text: 'Your weakest group determines the outcome.',
    author: 'Go Proverb',
  },
  {
    text: 'Read seven times, play once.',
    author: 'Go Proverb',
  },
  {
    text: 'Patience in Go leads to victory.',
    author: 'Go Proverb',
  },
  {
    text: 'Learn from your mistakes; every loss is a lesson.',
    author: 'Go Wisdom',
  },
  {
    text: 'The corner is gold, the side is silver, the center is grass.',
    author: 'Go Proverb',
  },
  {
    text: 'When in doubt, tenuki.',
    author: 'Go Proverb',
  },
  {
    text: 'Urgent points before big points.',
    author: 'Go Proverb',
  },
  {
    text: 'Even a monkey can read seven moves ahead.',
    author: 'Go Proverb',
  },
  {
    text: "The knight's move is never bad.",
    author: 'Go Proverb',
  },
  {
    text: "Don't go fishing while your house is burning.",
    author: 'Go Proverb',
  },
  {
    text: 'One move at a time, one stone at a time.',
    author: 'Go Wisdom',
  },
  {
    text: 'Ko fights reveal the soul of Go.',
    author: 'Go Wisdom',
  },
  {
    text: 'The path to dan is paved with tsumego.',
    author: 'Go Wisdom',
  },
] as const;

/**
 * Get a random Go quote
 */
export function getRandomQuote(): GoQuote {
  const index = Math.floor(Math.random() * GO_QUOTES.length);
  return GO_QUOTES[index] as GoQuote;
}

/**
 * Get a deterministic quote based on a seed (useful for daily quotes)
 */
export function getQuoteByDate(dateStr: string): GoQuote {
  // Simple hash of date string
  let hash = 0;
  for (let i = 0; i < dateStr.length; i++) {
    const char = dateStr.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  const index = Math.abs(hash) % GO_QUOTES.length;
  return GO_QUOTES[index] as GoQuote;
}

/**
 * Get quote of the day (based on current date)
 */
export function getTodayQuote(): GoQuote {
  const today = new Date().toISOString().split('T')[0] as string;
  return getQuoteByDate(today);
}
