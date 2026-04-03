export interface LearningLesson {
  readonly title: string;
  readonly url?: string;
}

export interface LearningSection {
  readonly title: string;
  readonly lessons: readonly LearningLesson[];
}

export type TopicIcon = 'seedling' | 'grid' | 'lightning' | 'trendUp' | 'star' | 'tesuji' | 'techniqueKey' | 'compass' | 'hint';

export type LearningTier = 'foundations' | 'building-strength' | 'advancing';

export interface TierInfo {
  readonly id: LearningTier;
  readonly title: string;
  readonly subtitle: string;
}

export const LEARNING_TIERS: readonly TierInfo[] = [
  { id: 'foundations', title: 'Foundations', subtitle: '20k \u2192 12k' },
  { id: 'building-strength', title: 'Building Strength', subtitle: '12k \u2192 5k' },
  { id: 'advancing', title: 'Advancing to Dan', subtitle: '5k \u2192 1d+' },
];

export interface LearningTopic {
  readonly slug: string;
  readonly title: string;
  readonly description: string;
  readonly icon: TopicIcon;
  readonly sections: readonly LearningSection[];
  readonly status: 'active' | 'coming-soon';
  readonly tier: LearningTier;
  readonly difficultyRange: string;
}

export const LEARNING_TOPICS: readonly LearningTopic[] = [
  {
    slug: 'beginner-fundamentals',
    title: 'Beginner Fundamentals',
    description: 'Learn capturing, escaping, ko rule, eyes, and basic scoring \u2014 the essential building blocks of Go.',
    icon: 'seedling',
    status: 'active',
    tier: 'foundations',
    difficultyRange: '30k\u201320k',
    sections: [
      {
        title: 'Part 1: Capturing & Escaping',
        lessons: [
          { title: 'Capture 1', url: 'https://online-go.com/puzzle/46530' },
          { title: 'Capture 2', url: 'https://online-go.com/puzzle/46574' },
          { title: 'Escape 1', url: 'https://online-go.com/puzzle/46587' },
          { title: 'Escape 2', url: 'https://online-go.com/puzzle/46600' },
          { title: 'Quiz 1', url: 'https://online-go.com/puzzle/46639' },
          { title: 'Capture towards the first line', url: 'https://online-go.com/puzzle/46654' },
          { title: 'Capture towards own stone', url: 'https://online-go.com/puzzle/46669' },
          { title: 'Capture by divide', url: 'https://online-go.com/puzzle/46690' },
          { title: 'Double atari', url: 'https://online-go.com/puzzle/46703' },
          { title: 'Quiz 2', url: 'https://online-go.com/puzzle/46717' },
        ],
      },
      {
        title: 'Part 2: Rules & Life/Death Basics',
        lessons: [
          { title: 'Suicide', url: 'https://online-go.com/puzzle/46729' },
          { title: 'Ko rule', url: 'https://online-go.com/puzzle/46744' },
          { title: 'Introduction of life and death', url: 'https://online-go.com/puzzle/46762' },
          { title: 'Two eyes to live', url: 'https://online-go.com/puzzle/46822' },
          { title: 'Quiz 3', url: 'https://online-go.com/puzzle/46837' },
          { title: 'Cut', url: 'https://online-go.com/puzzle/46790' },
          { title: 'Capturing race 1', url: 'https://online-go.com/puzzle/46907' },
          { title: 'Connect', url: 'https://online-go.com/puzzle/46803' },
          { title: 'Capturing race 2', url: 'https://online-go.com/puzzle/46921' },
          { title: 'Quiz 4', url: 'https://online-go.com/puzzle/47599' },
        ],
      },
      {
        title: 'Part 3: Tactical Techniques',
        lessons: [
          { title: 'Closes the door', url: 'https://online-go.com/puzzle/47319' },
          { title: 'Ladder', url: 'https://online-go.com/puzzle/47332' },
          { title: 'Hugging', url: 'https://online-go.com/puzzle/47611' },
          { title: 'Net', url: 'https://online-go.com/puzzle/47630' },
          { title: 'Quiz 5', url: 'https://online-go.com/puzzle/48064' },
          { title: 'Oiotoshi', url: 'https://online-go.com/puzzle/47678' },
          { title: 'Snapback', url: 'https://online-go.com/puzzle/47691' },
          { title: 'Oiotoshi and snapback', url: 'https://online-go.com/puzzle/47833' },
          { title: 'Squeeze', url: 'https://online-go.com/puzzle/47945' },
          { title: 'Quiz 6', url: 'https://online-go.com/puzzle/48077' },
        ],
      },
      {
        title: 'Part 4: Eye Shapes & Seki',
        lessons: [
          { title: 'Destroy an eye', url: 'https://online-go.com/puzzle/48222' },
          { title: 'Killable eye shapes', url: 'https://online-go.com/puzzle/48261' },
          { title: 'Living eye shapes', url: 'https://online-go.com/puzzle/48275' },
          { title: 'Dead eye shapes', url: 'https://online-go.com/puzzle/48288' },
          { title: 'Quiz 7', url: 'https://online-go.com/puzzle/48301' },
          { title: 'Makes eyes', url: 'https://online-go.com/puzzle/48313' },
          { title: 'Seki without eye', url: 'https://online-go.com/puzzle/48353' },
          { title: 'Seki with one eye each', url: 'https://online-go.com/puzzle/48391' },
          { title: 'Seki with partly filled eye space', url: 'https://online-go.com/puzzle/51885' },
          { title: 'Quiz 8', url: 'https://online-go.com/puzzle/51912' },
        ],
      },
      {
        title: 'Part 5: Scoring & Assessment',
        lessons: [
          { title: 'False eye', url: 'https://online-go.com/puzzle/51924' },
          { title: 'Snap back to kill', url: 'https://online-go.com/puzzle/51938' },
          { title: 'Life and Death training 1', url: 'https://online-go.com/puzzle/51952' },
          { title: 'Life and Death training 2', url: 'https://online-go.com/puzzle/51964' },
          { title: 'Quiz 9', url: 'https://online-go.com/puzzle/51976' },
          { title: 'Territory and Area Scoring 1', url: 'https://online-go.com/puzzle/52229' },
          { title: 'Territory and Area Scoring 2', url: 'https://online-go.com/puzzle/52249' },
          { title: 'Determine who wins 1', url: 'https://online-go.com/puzzle/52261' },
          { title: 'Determine who wins 2', url: 'https://online-go.com/puzzle/52286' },
          { title: 'Quiz 10', url: 'https://online-go.com/puzzle/52335' },
        ],
      },
    ],
  },
  {
    slug: 'strategy-territory',
    title: 'Strategy & Territory',
    description: 'Master territory control, endgame timing, and powerful tesuji for the middle game.',
    icon: 'grid',
    status: 'active',
    tier: 'foundations',
    difficultyRange: '20k\u201312k',
    sections: [
      {
        title: 'Part 6: Territory & Corner Control',
        lessons: [
          { title: 'Reducing opponent\'s territory', url: 'https://online-go.com/puzzle/52433' },
          { title: 'Enlarging one\'s own territory', url: 'https://online-go.com/puzzle/52446' },
          { title: 'Dame (neutral points)', url: 'https://online-go.com/puzzle/52562' },
          { title: 'Yose 1', url: 'https://online-go.com/puzzle/52575' },
          { title: 'Quiz 11', url: 'https://online-go.com/puzzle/52588' },
          { title: 'Control the corner', url: 'https://online-go.com/puzzle/52628' },
          { title: 'Third line and Fourth line', url: 'https://online-go.com/puzzle/52649' },
          { title: 'Corner enclosure', url: 'https://online-go.com/puzzle/52729' },
          { title: 'Approach the corner', url: 'https://online-go.com/puzzle/52779' },
          { title: 'Quiz 12', url: 'https://online-go.com/puzzle/52793' },
        ],
      },
      {
        title: 'Part 7: Extensions & Atari Responses',
        lessons: [
          { title: 'Extend on the side', url: 'https://online-go.com/puzzle/52796' },
          { title: 'Double extension', url: 'https://online-go.com/puzzle/52810' },
          { title: 'Connect the edge', url: 'https://online-go.com/puzzle/52837' },
          { title: 'Cooperation of third and fourth line', url: 'https://online-go.com/puzzle/52857' },
          { title: 'Quiz 13', url: 'https://online-go.com/puzzle/52872' },
          { title: 'Escape after atari', url: 'https://online-go.com/puzzle/48601' },
          { title: 'Ladder after atari', url: 'https://online-go.com/puzzle/48699' },
          { title: 'Net after atari', url: 'https://online-go.com/puzzle/48712' },
          { title: 'Snapback after atari', url: 'https://online-go.com/puzzle/48732' },
          { title: 'Quiz 14', url: 'https://online-go.com/puzzle/48790' },
        ],
      },
      {
        title: 'Part 8: Advanced Tesuji Techniques',
        lessons: [
          { title: 'Oshi-Tsubushi (bloated bullock)', url: 'https://online-go.com/puzzle/52086' },
          { title: 'Golden Chicken Standing on One Leg', url: 'https://online-go.com/puzzle/52099' },
          { title: 'Capture two, recapture one', url: 'https://online-go.com/puzzle/52112' },
          { title: 'Live after atari', url: 'https://online-go.com/puzzle/52125' },
          { title: 'Quiz 15', url: 'https://online-go.com/puzzle/52138' },
          { title: 'Protect the territory', url: 'https://online-go.com/puzzle/52884' },
          { title: 'Block and connect', url: 'https://online-go.com/puzzle/52899' },
          { title: 'Hane and connect', url: 'https://online-go.com/puzzle/52913' },
          { title: 'Value of Yose', url: 'https://online-go.com/puzzle/52957' },
          { title: 'Quiz 16', url: 'https://online-go.com/puzzle/52971' },
        ],
      },
    ],
  },
  {
    slug: 'capturing-races',
    title: 'Capturing Races & Reading',
    description: 'Sharpen your reading with capturing races, key stones, and middle-game fundamentals.',
    icon: 'lightning',
    status: 'active',
    tier: 'foundations',
    difficultyRange: '15k\u201310k',
    sections: [
      {
        title: 'Part 9: Capturing Races & Key Stones',
        lessons: [
          { title: 'Capturing race 3', url: 'https://online-go.com/puzzle/53213' },
          { title: 'Capturing race 4', url: 'https://online-go.com/puzzle/53226' },
          { title: 'Capturing race 5', url: 'https://online-go.com/puzzle/53239' },
          { title: 'Capturing race 6', url: 'https://online-go.com/puzzle/53256' },
          { title: 'Quiz 17', url: 'https://online-go.com/puzzle/53296' },
          { title: 'Key stones', url: 'https://online-go.com/puzzle/53374' },
          { title: 'Snap back for twice', url: 'https://online-go.com/puzzle/53397' },
          { title: 'Life and Death training 3', url: 'https://online-go.com/puzzle/53410' },
          { title: 'Life and Death training 4', url: 'https://online-go.com/puzzle/53424' },
          { title: 'Quiz 18', url: 'https://online-go.com/puzzle/53436' },
        ],
      },
      {
        title: 'Part 10: Middle Game Fundamentals',
        lessons: [
          { title: 'One-point jump to the center', url: 'https://online-go.com/puzzle/53124' },
          { title: 'Get a base', url: 'https://online-go.com/puzzle/53143' },
          { title: 'Splitting move', url: 'https://online-go.com/puzzle/53156' },
          { title: 'Block', url: 'https://online-go.com/puzzle/53185' },
          { title: 'Quiz 19', url: 'https://online-go.com/puzzle/53211' },
          { title: 'Crane\'s Nest Tesuji', url: 'https://online-go.com/puzzle/53449' },
          { title: 'Two-stone edge squeeze', url: 'https://online-go.com/puzzle/53462' },
          { title: 'Life and Death training 5', url: 'https://online-go.com/puzzle/53477' },
          { title: 'Life and Death training 6', url: 'https://online-go.com/puzzle/53495' },
          { title: 'Quiz 20', url: 'https://online-go.com/puzzle/53509' },
        ],
      },
    ],
  },
  {
    slug: 'kyu-to-dan',
    title: 'From Kyu to Dan',
    description: 'Step up from kyu to dan with advanced techniques, cutting methods, and group shapes.',
    icon: 'trendUp',
    status: 'active',
    tier: 'building-strength',
    difficultyRange: '10k\u20131d',
    sections: [
      {
        title: 'Part 1: Advanced Techniques',
        lessons: [
          { title: 'Double Ko', url: 'https://online-go.com/puzzle/53556' },
          { title: 'Eye versus No Eye Capturing Race', url: 'https://online-go.com/puzzle/53577' },
          { title: 'Life and Death training 7', url: 'https://online-go.com/puzzle/53590' },
          { title: 'Life and Death training 8', url: 'https://online-go.com/puzzle/53602' },
          { title: 'Life and Death training 9', url: 'https://online-go.com/puzzle/53614' },
          { title: 'Loose ladder', url: 'https://online-go.com/puzzle/53626' },
          { title: 'Net', url: 'https://online-go.com/puzzle/53638' },
          { title: 'Contact play', url: 'https://online-go.com/puzzle/53656' },
          { title: 'Squeeze', url: 'https://online-go.com/puzzle/53668' },
          { title: 'Oiotoshi', url: 'https://online-go.com/puzzle/53682' },
        ],
      },
      {
        title: 'Part 2: Connection Techniques',
        lessons: [
          { title: 'Kosumi on the bottom line', url: 'https://online-go.com/puzzle/53746' },
          { title: 'Two-stone edge squeeze', url: 'https://online-go.com/puzzle/53721' },
          { title: 'Cut to increase liberties', url: 'https://online-go.com/puzzle/53832' },
          { title: 'Ryobane', url: 'https://online-go.com/puzzle/53844' },
          { title: 'Snap back', url: 'https://online-go.com/puzzle/53856' },
          { title: 'Kosumi to connect', url: 'https://online-go.com/puzzle/53909' },
          { title: 'Atekomi to connect', url: 'https://online-go.com/puzzle/53922' },
          { title: 'Knight move to connect', url: 'https://online-go.com/puzzle/53934' },
          { title: 'Underneath Attachment', url: 'https://online-go.com/puzzle/53946' },
          { title: 'Monkey climbing the mountain', url: 'https://online-go.com/puzzle/53962' },
        ],
      },
      {
        title: 'Part 3: Cutting Techniques & Group Shapes',
        lessons: [
          { title: 'Atekomi to cut', url: 'https://online-go.com/puzzle/53977' },
          { title: 'Wedge to cut', url: 'https://online-go.com/puzzle/53992' },
          { title: 'Waist cut', url: 'https://online-go.com/puzzle/54010' },
          { title: 'Cut on two sides', url: 'https://online-go.com/puzzle/54026' },
          { title: 'Kosumi to cut', url: 'https://online-go.com/puzzle/54039' },
          { title: 'J group', url: 'https://online-go.com/puzzle/56207' },
          { title: 'Tripod Group', url: 'https://online-go.com/puzzle/56219' },
          { title: 'Rectangular six (corner)', url: 'https://online-go.com/puzzle/56232' },
          { title: 'Rectangular eight', url: 'https://online-go.com/puzzle/56244' },
          { title: 'Leaf group', url: 'https://online-go.com/puzzle/56256' },
        ],
      },
      {
        title: 'Part 4: Special Formations',
        lessons: [
          { title: 'L+1 group', url: 'https://online-go.com/puzzle/56303' },
          { title: 'Life and Death training 10', url: 'https://online-go.com/puzzle/56315' },
          { title: 'Life and Death training 11', url: 'https://online-go.com/puzzle/56327' },
          { title: 'Life and Death training 12', url: 'https://online-go.com/puzzle/56339' },
          { title: 'Life and Death training 13', url: 'https://online-go.com/puzzle/56351' },
          { title: 'Six die but eight live', url: 'https://online-go.com/puzzle/56469' },
          { title: 'Door group', url: 'https://online-go.com/puzzle/56481' },
          { title: 'Bridge group', url: 'https://online-go.com/puzzle/56494' },
          { title: 'Rectangular six (edge)', url: 'https://online-go.com/puzzle/56506' },
          { title: 'Life and death on the edge', url: 'https://online-go.com/puzzle/56518' },
        ],
      },
      {
        title: 'Part 5: Life & Death Challenge',
        lessons: [
          { title: 'Life and death quiz 1', url: 'https://online-go.com/puzzle/58764' },
          { title: 'Life and death quiz 2', url: 'https://online-go.com/puzzle/58776' },
          { title: 'Life and death quiz 3', url: 'https://online-go.com/puzzle/58789' },
          { title: 'Life and death quiz 4', url: 'https://online-go.com/puzzle/58801' },
          { title: 'Life and death quiz 5', url: 'https://online-go.com/puzzle/58819' },
          { title: 'Life and death quiz 6', url: 'https://online-go.com/puzzle/58847' },
          { title: 'Life and death quiz 7', url: 'https://online-go.com/puzzle/58864' },
          { title: 'Life and death quiz 8', url: 'https://online-go.com/puzzle/58882' },
          { title: 'Life and death quiz 9', url: 'https://online-go.com/puzzle/58894' },
          { title: 'Life and death quiz 10', url: 'https://online-go.com/puzzle/58907' },
        ],
      },
    ],
  },
  {
    slug: 'life-and-death',
    title: 'Life & Death Encyclopedia',
    description: 'A comprehensive reference for corner, edge, and real-game life and death patterns.',
    icon: 'star',
    status: 'active',
    tier: 'building-strength',
    difficultyRange: '15k\u20131d+',
    sections: [
      {
        title: 'Corner Formations',
        lessons: [
          { title: 'Second line formation', url: 'https://online-go.com/puzzle/56662' },
          { title: 'Comb formation', url: 'https://online-go.com/puzzle/57045' },
          { title: 'Key formation', url: 'https://online-go.com/puzzle/56749' },
          { title: 'Rectangular Eight 1', url: 'https://online-go.com/puzzle/56929' },
          { title: 'Rectangular Eight 2', url: 'https://online-go.com/puzzle/56986' },
          { title: 'Rectangular Eight 3', url: 'https://online-go.com/puzzle/56999' },
          { title: 'Carpenter\'s Square', url: 'https://online-go.com/puzzle/57085' },
          { title: 'Carpenter\'s Square 2', url: 'https://online-go.com/puzzle/57151' },
        ],
      },
      {
        title: 'Edge Formations',
        lessons: [
          { title: 'Second line formation', url: 'https://online-go.com/puzzle/57166' },
          { title: 'Third line formation', url: 'https://online-go.com/puzzle/57331' },
          { title: 'Fourth line formation', url: 'https://online-go.com/puzzle/57650' },
        ],
      },
      {
        title: 'Life & Death in Real Games',
        lessons: [
          { title: 'Battle of one eye', url: 'https://online-go.com/puzzle/58079' },
          { title: 'Tesuji for kill', url: 'https://online-go.com/puzzle/58385' },
          { title: 'Tesuji for live', url: 'https://online-go.com/puzzle/58521' },
          { title: 'Types of ko', url: 'https://online-go.com/puzzle/57938' },
          { title: 'Is there any play?', url: 'https://online-go.com/puzzle/57934' },
        ],
      },
      {
        title: 'Life & Death of Sacrifice',
        lessons: [
          { title: 'Sacrifice a bit', url: 'https://online-go.com/puzzle/47230' },
          { title: 'Sacrifice more', url: 'https://online-go.com/puzzle/47253' },
          { title: 'Simple Sacrifice', url: 'https://online-go.com/puzzle/47284' },
          { title: 'Sacrifice a lot', url: 'https://online-go.com/puzzle/47272' },
          { title: 'Technical sacrifice', url: 'https://online-go.com/puzzle/47371' },
          { title: 'Magnificent Sacrifice', url: 'https://online-go.com/puzzle/47426' },
        ],
      },
      {
        title: 'Famous Life & Death',
        lessons: [
          { title: '3-3 invasion' },
          { title: 'Attach the star point' },
          { title: 'L&D classics' },
          { title: 'Star point Joseki' },
        ],
      },
      {
        title: 'Advanced Questions',
        lessons: [
          { title: 'Hondojo\'s secret question bank (2d-4d)', url: 'https://online-go.com/puzzle/47738' },
          { title: 'Hondojo\'s secret question bank (4d-5d)', url: 'https://online-go.com/puzzle/48513' },
          { title: 'Hondojo\'s secret question bank (>5d)', url: 'https://online-go.com/puzzle/48536' },
          { title: 'Satan\'s move 1', url: 'https://online-go.com/puzzle/59960' },
          { title: 'Satan\'s move 2', url: 'https://online-go.com/puzzle/60184' },
        ],
      },
    ],
  },
  {
    slug: 'tesuji-encyclopedia',
    title: 'Tesuji Encyclopedia',
    description: 'Master offensive and defensive tesuji \u2014 the tactical weapons of Go.',
    icon: 'tesuji',
    status: 'active',
    tier: 'building-strength',
    difficultyRange: '10k\u20131d',
    sections: [
      {
        title: 'Aggressive Tesuji',
        lessons: [
          { title: 'Cut', url: 'https://online-go.com/puzzle/48970' },
          { title: 'Miai', url: 'https://online-go.com/puzzle/49411' },
          { title: 'Capturing', url: 'https://online-go.com/puzzle/48998' },
          { title: 'Take the base', url: 'https://online-go.com/puzzle/49546' },
          { title: 'Kake', url: 'https://online-go.com/puzzle/49114' },
          { title: 'Yose', url: 'https://online-go.com/puzzle/49566' },
          { title: 'Destroy shape', url: 'https://online-go.com/puzzle/49155' },
          { title: 'Ijime (Bullying)', url: 'https://online-go.com/puzzle/49587' },
          { title: 'Heaviness', url: 'https://online-go.com/puzzle/49272' },
          { title: 'Ko 1', url: 'https://online-go.com/puzzle/49625' },
          { title: 'Capturing race', url: 'https://online-go.com/puzzle/49292' },
          { title: 'To kill', url: 'https://online-go.com/puzzle/49654' },
        ],
      },
      {
        title: 'Defensive Tesuji',
        lessons: [
          { title: 'Connect', url: 'https://online-go.com/puzzle/49693' },
          { title: 'Sabaki', url: 'https://online-go.com/puzzle/51294' },
          { title: 'Shinogi', url: 'https://online-go.com/puzzle/51312' },
          { title: 'Advance', url: 'https://online-go.com/puzzle/51380' },
          { title: 'Ko 2', url: 'https://online-go.com/puzzle/51547' },
          { title: 'Capturing race', url: 'https://online-go.com/puzzle/51425' },
          { title: 'Make shape', url: 'https://online-go.com/puzzle/51392' },
          { title: 'To live', url: 'https://online-go.com/puzzle/51573' },
          { title: 'Probe', url: 'https://online-go.com/puzzle/51471' },
          { title: 'Others', url: 'https://online-go.com/puzzle/51711' },
        ],
      },
      {
        title: 'Classic Tesuji (2 kyu — 1 dan)',
        lessons: [
          { title: 'The raccoon-dog drums his belly', url: 'https://online-go.com/puzzle/51777' },
          { title: 'Mouse stealing oil', url: 'https://online-go.com/puzzle/51788' },
          { title: 'Squeeze', url: 'https://online-go.com/puzzle/51800' },
          { title: 'Golden Chicken Standing on one Leg', url: 'https://online-go.com/puzzle/51816' },
          { title: 'Two-stone edge squeeze', url: 'https://online-go.com/puzzle/51827' },
          { title: 'Acacia cut', url: 'https://online-go.com/puzzle/51748' },
        ],
      },
    ],
  },
  {
    slug: 'yose',
    title: 'Yose (Endgame)',
    description: 'Calculate yose values, master sente vs gote, and win the endgame.',
    icon: 'techniqueKey',
    status: 'active',
    tier: 'advancing',
    difficultyRange: '5k\u20131d+',
    sections: [
      {
        title: 'Yose Value Determination',
        lessons: [
          { title: 'Double Sente Yose value', url: 'https://online-go.com/puzzle/49752' },
          { title: 'Basic Double Gote Yose value 1', url: 'https://online-go.com/puzzle/49832' },
          { title: 'Basic Double Gote Yose value 2', url: 'https://online-go.com/puzzle/50062' },
          { title: 'Basic Double Gote Yose value 3', url: 'https://online-go.com/puzzle/50182' },
          { title: 'Basic Single Sente Yose value', url: 'https://online-go.com/puzzle/49755' },
          { title: 'Intermediate Double Gote Yose value 1', url: 'https://online-go.com/puzzle/50423' },
          { title: 'Intermediate Double Gote Yose value 2', url: 'https://online-go.com/puzzle/50534' },
          { title: 'Intermediate Double Gote Yose value 3', url: 'https://online-go.com/puzzle/50670' },
          { title: 'Intermediate Single Sente Yose value', url: 'https://online-go.com/puzzle/50308' },
          { title: 'Advanced Double Gote Yose value 1', url: 'https://online-go.com/puzzle/50867' },
          { title: 'Advanced Double Gote Yose value 2', url: 'https://online-go.com/puzzle/50922' },
          { title: 'Advanced Double Gote Yose value 3', url: 'https://online-go.com/puzzle/50977' },
          { title: 'Advanced Single Sente Yose value', url: 'https://online-go.com/puzzle/50819' },
          { title: 'Advanced Yose Tesuji', url: 'https://online-go.com/puzzle/51029' },
        ],
      },
      {
        title: '9x9 Yose Questions by Terayama',
        lessons: [
          { title: 'Beginner', url: 'https://online-go.com/puzzle/59003' },
          { title: 'Intermediate', url: 'https://online-go.com/puzzle/59161' },
          { title: 'Advanced', url: 'https://online-go.com/puzzle/59240' },
          { title: '1 dan — 2 dan', url: 'https://online-go.com/puzzle/47433' },
          { title: '3 dan — 4 dan', url: 'https://online-go.com/puzzle/47479' },
          { title: '5 dan and above', url: 'https://online-go.com/puzzle/47499' },
          { title: 'Professional', url: 'https://online-go.com/puzzle/47728' },
        ],
      },
      {
        title: 'Mini Yose Encyclopedia',
        lessons: [
          { title: 'Yose value list', url: 'https://online-go.com/puzzle/59300' },
          { title: 'There is move in endgame', url: 'https://online-go.com/puzzle/59417' },
          { title: 'There is no move', url: 'https://online-go.com/puzzle/59447' },
          { title: 'Yose tesuji', url: 'https://online-go.com/puzzle/59512' },
        ],
      },
    ],
  },
  {
    slug: 'openings',
    title: 'Openings & Joseki',
    description: 'Learn opening theory, classical and AI-era joseki, and how to start a game with confidence.',
    icon: 'compass',
    status: 'active',
    tier: 'advancing',
    difficultyRange: '15k\u20131d+',
    sections: [
      {
        title: 'Opening Theory',
        lessons: [
          { title: 'Basic opening theory' },
          { title: 'Decline of classical openings' },
          { title: 'Change of general knowledge' },
          { title: 'Revolutionary AI joseki' },
          { title: 'Shibano Toramaru Column' },
        ],
      },
      {
        title: 'Joseki',
        lessons: [
          { title: 'Star joseki' },
          { title: 'Komoku joseki' },
          { title: 'OGS Joseki Library', url: 'https://online-go.com/joseki/15081' },
        ],
      },
    ],
  },
];
