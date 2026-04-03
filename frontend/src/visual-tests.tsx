/** @jsxImportSource preact */
/**
 * Visual Test Fixtures Page
 * 
 * This page renders component fixtures for Playwright visual testing.
 * Each fixture is rendered in isolation with a unique ID for targeting.
 * 
 * Access via: http://localhost:5173/visual-tests.html
 */

import { render } from 'preact';
import { Board } from './components/Board';
import { LevelCard } from './components/Level/LevelCard';
import type { BoardSize, Stone } from './models/puzzle';
import type { SolutionMarker } from './components/Board/Board';
import { STREAK_MILESTONES } from './services/streakManager';
import './styles/app.css';

/** Helper to create an empty stone grid */
function createEmptyGrid(size: BoardSize): Stone[][] {
  return Array.from({ length: size }, () => 
    Array.from({ length: size }, () => null as unknown as Stone)
  );
}

/** Helper to create a stone grid with specific stones */
function createGridWithStones(
  size: BoardSize,
  stones: Array<{ x: number; y: number; color: 'black' | 'white' }>
): Stone[][] {
  const grid = createEmptyGrid(size);
  for (const { x, y, color } of stones) {
    const row = grid[y];
    if (row) {
      row[x] = { color } as unknown as Stone;
    }
  }
  return grid;
}

/** Fixture container styles */
const containerStyle = {
  display: 'inline-block',
  margin: '20px',
  padding: '10px',
  background: '#f5f5f5',
  borderRadius: '8px',
};

const fixtureStyle = {
  width: '400px',
  height: '400px',
};

const smallFixtureStyle = {
  width: '300px',
  height: '300px',
};

const largeFixtureStyle = {
  width: '600px',
  height: '600px',
};

/** Visual Test Fixtures App */
function VisualTestFixtures() {
  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: '20px' }}>
      <h1>Yen-Go Visual Test Fixtures</h1>
      <p>These fixtures are used by Playwright for visual regression testing.</p>
      
      <h2>Board Fixtures</h2>
      
      {/* Empty boards */}
      <section>
        <h3>Empty Boards</h3>
        
        <div id="board-empty-9x9" style={containerStyle}>
          <h4>9x9 Board</h4>
          <div style={fixtureStyle}>
            <Board boardSize={9} stones={createEmptyGrid(9)} interactive={false} />
          </div>
        </div>
        
        <div id="board-empty-13x13" style={containerStyle}>
          <h4>13x13 Board</h4>
          <div style={fixtureStyle}>
            <Board boardSize={13} stones={createEmptyGrid(13)} interactive={false} />
          </div>
        </div>
        
        <div id="board-empty-19x19" style={containerStyle}>
          <h4>19x19 Board</h4>
          <div style={fixtureStyle}>
            <Board boardSize={19} stones={createEmptyGrid(19)} interactive={false} />
          </div>
        </div>
      </section>
      
      {/* Boards with stones */}
      <section>
        <h3>Boards with Stones</h3>
        
        <div id="board-with-stones" style={containerStyle}>
          <h4>With Stones</h4>
          <div style={fixtureStyle}>
            <Board 
              boardSize={9} 
              stones={createGridWithStones(9, [
                { x: 2, y: 2, color: 'black' },
                { x: 3, y: 2, color: 'white' },
                { x: 2, y: 3, color: 'white' },
                { x: 3, y: 3, color: 'black' },
                { x: 4, y: 4, color: 'black' },
                { x: 6, y: 2, color: 'white' },
                { x: 6, y: 6, color: 'black' },
              ])} 
              interactive={false} 
            />
          </div>
        </div>
        
        <div id="board-with-last-move" style={containerStyle}>
          <h4>With Last Move Marker</h4>
          <div style={fixtureStyle}>
            <Board 
              boardSize={9} 
              stones={createGridWithStones(9, [
                { x: 2, y: 2, color: 'black' },
                { x: 3, y: 3, color: 'white' },
                { x: 4, y: 4, color: 'black' },
              ])}
              lastMove={{ x: 4, y: 4 }}
              interactive={false} 
            />
          </div>
        </div>
        
        <div id="board-corner-pattern" style={containerStyle}>
          <h4>Corner Pattern (Tsumego)</h4>
          <div style={fixtureStyle}>
            <Board 
              boardSize={9} 
              stones={createGridWithStones(9, [
                // Black corner group
                { x: 0, y: 0, color: 'black' },
                { x: 1, y: 0, color: 'black' },
                { x: 0, y: 1, color: 'black' },
                { x: 1, y: 1, color: 'black' },
                { x: 2, y: 1, color: 'black' },
                { x: 0, y: 2, color: 'black' },
                // White surrounding
                { x: 2, y: 0, color: 'white' },
                { x: 3, y: 0, color: 'white' },
                { x: 3, y: 1, color: 'white' },
                { x: 3, y: 2, color: 'white' },
                { x: 1, y: 2, color: 'white' },
                { x: 2, y: 2, color: 'white' },
                { x: 0, y: 3, color: 'white' },
                { x: 1, y: 3, color: 'white' },
              ])}
              interactive={false} 
            />
          </div>
        </div>
      </section>
      
      {/* Interactive states */}
      <section>
        <h3>Interactive States</h3>
        
        <div id="board-with-hover-stone" style={containerStyle}>
          <h4>With Ghost Stone Preview</h4>
          <div style={fixtureStyle}>
            <Board 
              boardSize={9} 
              stones={createGridWithStones(9, [
                { x: 2, y: 2, color: 'black' },
                { x: 3, y: 3, color: 'white' },
              ])}
              hoverStone={{ coord: { x: 5, y: 5 }, color: 'black' }}
              interactive={true} 
            />
          </div>
        </div>
        
        <div id="board-with-highlight" style={containerStyle}>
          <h4>With Highlighted Move (Hint)</h4>
          <div style={fixtureStyle}>
            <Board 
              boardSize={9} 
              stones={createGridWithStones(9, [
                { x: 2, y: 2, color: 'black' },
                { x: 3, y: 3, color: 'white' },
              ])}
              highlightedMove={{ x: 4, y: 4 }}
              interactive={false} 
            />
          </div>
        </div>
        
        <div id="board-with-solution-markers" style={containerStyle}>
          <h4>With Solution Markers</h4>
          <div style={fixtureStyle}>
            <Board 
              boardSize={9} 
              stones={createGridWithStones(9, [
                { x: 2, y: 2, color: 'black' },
                { x: 3, y: 3, color: 'white' },
              ])}
              solutionMarkers={[
                { coord: { x: 4, y: 4 }, type: 'correct' },
                { coord: { x: 5, y: 5 }, type: 'wrong' },
                { coord: { x: 6, y: 6 }, type: 'optimal' },
              ] as SolutionMarker[]}
              interactive={false} 
            />
          </div>
        </div>
      </section>
      
      {/* Size variations */}
      <section>
        <h3>Size Variations</h3>
        
        <div id="board-small" style={containerStyle}>
          <h4>Small (300x300)</h4>
          <div style={smallFixtureStyle}>
            <Board boardSize={9} stones={createEmptyGrid(9)} interactive={false} />
          </div>
        </div>
        
        <div id="board-large" style={containerStyle}>
          <h4>Large (600x600)</h4>
          <div style={largeFixtureStyle}>
            <Board boardSize={9} stones={createEmptyGrid(9)} interactive={false} />
          </div>
        </div>
      </section>
      
      {/* Rotation */}
      <section>
        <h3>Rotation</h3>
        
        <div id="board-rotated-90" style={containerStyle}>
          <h4>Rotated 90°</h4>
          <div style={fixtureStyle}>
            <Board 
              boardSize={9} 
              stones={createGridWithStones(9, [
                { x: 2, y: 2, color: 'black' },
                { x: 6, y: 2, color: 'white' },
              ])}
              rotation={90}
              interactive={false} 
            />
          </div>
        </div>
      </section>
      
      {/* LevelCard component fixtures */}
      <h2>LevelCard Component</h2>
      
      <section>
        <h3>Card States</h3>
        
        <div id="level-card-unlocked" style={containerStyle}>
          <h4>Unlocked Level</h4>
          <LevelCard
            level={{ id: 'beginner', name: 'Beginner', puzzleCount: 25 }}
            isUnlocked={true}
            isCompleted={false}
          />
        </div>
        
        <div id="level-card-completed" style={containerStyle}>
          <h4>Completed Level</h4>
          <LevelCard
            level={{ id: 'basic', name: 'Basic', puzzleCount: 50 }}
            isUnlocked={true}
            isCompleted={true}
          />
        </div>
        
        <div id="level-card-locked" style={containerStyle}>
          <h4>Locked Level</h4>
          <LevelCard
            level={{ id: 'intermediate', name: 'Intermediate', puzzleCount: 75 }}
            isUnlocked={false}
            isCompleted={false}
          />
        </div>
        
        <div id="level-card-advanced" style={containerStyle}>
          <h4>Advanced Level</h4>
          <LevelCard
            level={{ id: 'advanced', name: 'Advanced', puzzleCount: 100 }}
            isUnlocked={true}
            isCompleted={false}
          />
        </div>
        
        <div id="level-card-expert" style={containerStyle}>
          <h4>Expert Level</h4>
          <LevelCard
            level={{ id: 'expert', name: 'Expert', puzzleCount: 150 }}
            isUnlocked={true}
            isCompleted={false}
          />
        </div>
      </section>
      
      {/* StreakDisplay component fixtures */}
      <h2>StreakDisplay Component</h2>
      
      <section>
        <h3>Streak States</h3>
        
        {/* Static StreakDisplay - New User (no streak) */}
        <div id="streak-new-user" style={containerStyle}>
          <h4>New User (No Streak)</h4>
          <StaticStreakDisplay
            currentStreak={0}
            longestStreak={0}
            isActive={false}
            isAtRisk={false}
            nextMilestone={7}
            daysUntilNextMilestone={7}
          />
        </div>
        
        {/* Static StreakDisplay - Active Streak */}
        <div id="streak-active" style={containerStyle}>
          <h4>Active Streak (5 days)</h4>
          <StaticStreakDisplay
            currentStreak={5}
            longestStreak={5}
            isActive={true}
            isAtRisk={false}
            nextMilestone={7}
            daysUntilNextMilestone={2}
          />
        </div>
        
        {/* Static StreakDisplay - At Risk */}
        <div id="streak-at-risk" style={containerStyle}>
          <h4>Streak At Risk</h4>
          <StaticStreakDisplay
            currentStreak={12}
            longestStreak={12}
            isActive={false}
            isAtRisk={true}
            nextMilestone={14}
            daysUntilNextMilestone={2}
          />
        </div>
        
        {/* Static StreakDisplay - Long Streak */}
        <div id="streak-long" style={containerStyle}>
          <h4>Long Streak (30+ days)</h4>
          <StaticStreakDisplay
            currentStreak={45}
            longestStreak={45}
            isActive={true}
            isAtRisk={false}
            nextMilestone={60}
            daysUntilNextMilestone={15}
          />
        </div>
        
        {/* Static StreakDisplay - Compact Mode */}
        <div id="streak-compact" style={containerStyle}>
          <h4>Compact Mode</h4>
          <StaticStreakDisplay
            currentStreak={7}
            longestStreak={14}
            isActive={true}
            isAtRisk={false}
            compact={true}
          />
        </div>
        
        {/* Static StreakDisplay - Milestone Reached */}
        <div id="streak-milestone" style={containerStyle}>
          <h4>Milestone Just Reached</h4>
          <StaticStreakDisplay
            currentStreak={30}
            longestStreak={30}
            isActive={true}
            isAtRisk={false}
            nextMilestone={60}
            daysUntilNextMilestone={30}
            showCelebration={true}
            celebrationMilestone={30}
          />
        </div>
      </section>
    </div>
  );
}

/**
 * Static StreakDisplay for visual testing
 * This component doesn't use hooks - it receives all data as props
 */
interface StaticStreakDisplayProps {
  currentStreak: number;
  longestStreak: number;
  isActive: boolean;
  isAtRisk: boolean;
  nextMilestone?: number;
  daysUntilNextMilestone?: number;
  compact?: boolean;
  showCelebration?: boolean;
  celebrationMilestone?: number;
}

function StaticStreakDisplay({
  currentStreak,
  longestStreak,
  isActive,
  isAtRisk,
  nextMilestone,
  daysUntilNextMilestone,
  compact = false,
  showCelebration = false,
  celebrationMilestone,
}: StaticStreakDisplayProps) {
  const milestones = STREAK_MILESTONES;
  
  // Compact mode for small displays
  if (compact) {
    return (
      <div
        className="streak-display streak-compact"
        role="region"
        aria-label="Daily streak"
      >
        <span className="streak-icon" aria-hidden="true">
          {isActive ? '🔥' : isAtRisk ? '⚠️' : '💤'}
        </span>
        <span className="streak-count">{currentStreak}</span>
        <span className="streak-unit">day{currentStreak !== 1 ? 's' : ''}</span>
      </div>
    );
  }

  return (
    <div
      className="streak-display"
      role="region"
      aria-label="Streak information"
    >
      {/* Milestone celebration */}
      {showCelebration && celebrationMilestone && (
        <div className="streak-celebration" role="alert">
          <h4>🎉 Milestone Reached!</h4>
          <p>You've maintained a {celebrationMilestone}-day streak!</p>
          <button className="btn-acknowledge">
            Awesome!
          </button>
        </div>
      )}

      {/* Main streak display */}
      <div className="streak-main">
        <div className="streak-flame">
          <span className="flame-icon" aria-hidden="true">
            {isActive ? '🔥' : isAtRisk ? '⚠️' : '💤'}
          </span>
          <span className="streak-number">{currentStreak}</span>
        </div>
        <div className="streak-label">
          <span className="label-text">
            {currentStreak === 0 && !isAtRisk
              ? 'Start your streak!'
              : isAtRisk
                ? 'Play today to keep your streak!'
                : `Day${currentStreak !== 1 ? 's' : ''} in a row`}
          </span>
        </div>
      </div>

      {/* Best streak */}
      {longestStreak > 0 && (
        <div className="streak-best">
          <span className="best-label">Best:</span>
          <span className="best-value">{longestStreak} day{longestStreak !== 1 ? 's' : ''}</span>
        </div>
      )}

      {/* Progress to next milestone */}
      {nextMilestone && daysUntilNextMilestone !== undefined && (
        <div className="streak-progress">
          <div className="progress-label">
            {daysUntilNextMilestone} more day{daysUntilNextMilestone !== 1 ? 's' : ''} to {nextMilestone}-day milestone
          </div>
          <div className="progress-bar" role="progressbar" aria-valuenow={currentStreak} aria-valuemax={nextMilestone}>
            <div
              className="progress-fill"
              style={{
                width: `${Math.min(100, (currentStreak / nextMilestone) * 100)}%`,
              }}
            />
          </div>
        </div>
      )}

      {/* Milestones grid */}
      <div className="streak-milestones">
        <h4>Milestones</h4>
        <div className="milestone-grid">
          {milestones.map((milestone) => (
            <span
              key={milestone}
              className={longestStreak >= milestone ? 'milestone-badge achieved' : 'milestone-badge locked'}
              role="img"
              aria-label={`${milestone} day streak ${longestStreak >= milestone ? 'achieved' : 'locked'}`}
              title={`${milestone} days`}
            >
              {longestStreak >= milestone ? '🏆' : '🔒'} {milestone}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

// Render the fixtures page
const root = document.getElementById('app');
if (root) {
  render(<VisualTestFixtures />, root);
}
