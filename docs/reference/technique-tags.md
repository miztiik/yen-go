# Technique Tags Reference

Complete reference for technique tags used in puzzle classification.

---

## Tag Categories

### Capture Techniques

| Tag | Description | Aliases |
|-----|-------------|---------|
| `ladder` | Diagonal chase capture (shicho) | shicho, running fight |
| `snapback` | Sacrifice then recapture with gain | snap back, uttegaeshi |
| `ko` | Ko fight situation | ko fight |
| `throw_in` | Liberty-reducing sacrifice | throw in, horikomi |
| `net` | Loose surrounding capture (geta) | geta, loose net |
| `squeeze` | Damezumari-based capture | damezumari, shortage of liberties |
| `double_atari` | Threatens two groups at once | double attack |
| `oiotoshi` | Connect-and-die sequence | connect and die |
| `under_the_stones` | Play under captured stones | ishi no shita |
| `capturing_race` | Semeai - race to capture | semeai, liberty race |

### Connection Techniques

| Tag | Description | Aliases |
|-----|-------------|---------|
| `connect` | Connect two groups | connection |
| `cut` | Separate opponent's groups | cutting |
| `cross_cut` | Four alternating stones pattern | crosscut |
| `bamboo_joint` | Diagonal connection pattern | tiger's mouth, bamboo |
| `peep` | Threatens to cut | nozoki |
| `escape` | Group runs to center | running, escape route |

### Eye/Life Techniques

| Tag | Description | Aliases |
|-----|-------------|---------|
| `eye_steal` | Destroys eye potential | eye stealing, me tori |
| `false_eye` | Creates false eye | false eye shape |
| `seki` | Mutual life situation | mutual life |
| `killing` | Kills opponent group | death |
| `living` | Makes two eyes | life, living shape |
| `big_eye` | Large eye space manipulation | - |

### Dead Shapes

| Tag | Description | Aliases |
|-----|-------------|---------|
| `bent_four` | Bent four in the corner | bent 4 |
| `l_group` | L-shaped dead group | L group, L shape |
| `bulky_five` | Five-stone dead shape | bulky 5 |
| `straight_three` | Three in a row dead | straight 3 |
| `dead_shape` | Generic dead shape | killable shape |

### Move Shapes

| Tag | Description | Aliases |
|-----|-------------|---------|
| `hane` | Diagonal wrap move | hanetsugi |
| `clamp` | Attachment move | attachment, tsuke |
| `placement` | Play inside enemy group | uchikomi |
| `descent` | Move toward edge | sagari |
| `wedge` | Insertion between stones | warikomi |
| `attachment` | Direct contact play | tsuke |

### General Tags

| Tag | Description | Aliases |
|-----|-------------|---------|
| `tesuji` | General clever move | technique |
| `reading` | Requires deep reading | calculation |
| `sacrifice` | Sacrificing stones | sacrifice play |
| `timing` | Move order important | timing play |
| `shape` | Shape-based problem | good shape, bad shape |

---

## Tag Configuration

### tags.json Structure

```json
{
  "version": "1.0",
  "tags": ["ladder", "snapback", "ko", "..."],
  "aliases": {
    "shicho": "ladder",
    "snap back": "snapback",
    "geta": "net",
    "semeai": "capturing_race"
  },
  "categories": {
    "capture": ["ladder", "snapback", "ko", "throw_in", "net"],
    "connection": ["connect", "cut", "cross_cut", "bamboo_joint"],
    "eye": ["eye_steal", "false_eye", "seki", "killing", "living"],
    "shape": ["hane", "clamp", "placement", "descent", "wedge"]
  }
}
```

### Tag Normalization

Input tags are normalized:
- `"shicho"` → `"ladder"`
- `"Snap Back"` → `"snapback"`
- `"GETA"` → `"net"`

---

## Detection Methods

Tags are detected during the Tag stage of the pipeline:

1. **Solution Analysis** - Examine move sequences
2. **Capture Events** - Track captures during playback
3. **Board State** - Compare initial/final positions
4. **Shape Recognition** - Identify known patterns

### Detection Examples

**Ladder Detection**:
- 6+ consecutive ataris in diagonal direction
- Captured group moves toward edge/center

**Snapback Detection**:
- Player sacrifices stone(s)
- Immediately recaptures with gain

**Ko Detection**:
- Ko event triggered during solution
- Position repeats with ko rule

---

## 15-Day Technique Rotation

Daily challenges rotate through techniques:

| Day | Primary | Secondary |
|-----|---------|-----------|
| 1 | ladder | escape |
| 2 | snapback | throw_in |
| 3 | ko | seki |
| 4 | net | double_atari |
| 5 | connect | cut |
| 6 | eye_steal | false_eye |
| 7 | capturing_race | squeeze |
| 8 | hane | descent |
| 9 | clamp | placement |
| 10 | cross_cut | peep |
| 11 | bamboo_joint | wedge |
| 12 | oiotoshi | under_the_stones |
| 13 | dead_shape | bent_four |
| 14 | killing | living |
| 15 | tesuji | reading |

---

## Tag Statistics

Typical distribution in collections:

| Tag | Frequency |
|-----|-----------|
| tesuji | ~35% |
| killing | ~25% |
| living | ~20% |
| ko | ~12% |
| ladder | ~10% |
| snapback | ~8% |
| capturing_race | ~7% |
| connect | ~6% |
| cut | ~5% |
| eye_steal | ~5% |

---

## API Usage

### Validate Tags

```python
from puzzle_manager.config import get_config_loader

config = get_config_loader()

tags = ["ladder", "ko", "unknown"]
valid, invalid = config.validate_tags(tags)
# valid = ["ladder", "ko"]
# invalid = ["unknown"]
```

### Normalize Tags

```python
normalized = config.normalize_tag("shicho")  # "ladder"
```

### Get All Tags

```python
all_tags = config.get_all_tags()
```

---

## Adding New Tags

1. Add to `config/tags.json`:
   ```json
   {
     "tags": ["...", "new_technique"],
     "aliases": {
       "alternative name": "new_technique"
     }
   }
   ```

2. Implement detection (optional):
   ```python
   # In stages/tag.py
   def _detect_new_technique(self, puzzle, board_history):
       return is_detected
   ```

3. Add to category:
   ```json
   {
     "categories": {
       "capture": ["...", "new_technique"]
     }
   }
   ```

---

## Japanese-English Glossary

| Japanese | English | Tag |
|----------|---------|-----|
| Shicho | Ladder | `ladder` |
| Uttegaeshi | Snapback | `snapback` |
| Ko | Ko | `ko` |
| Geta | Net | `net` |
| Semeai | Capturing Race | `capturing_race` |
| Damezumari | Liberty Shortage | `squeeze` |
| Nozoki | Peep | `peep` |
| Tsuke | Attachment | `clamp` |
| Sagari | Descent | `descent` |
| Hane | Hane | `hane` |
| Warikomi | Wedge | `wedge` |
| Uchikomi | Placement | `placement` |
| Seki | Seki | `seki` |

---

## See Also

- [reference/configuration.md](configuration.md) - Configuration reference
- [architecture/backend/stages.md](../architecture/backend/stages.md) - Pipeline stages
- [getting-started/play.md](../getting-started/play.md) - Player guide
