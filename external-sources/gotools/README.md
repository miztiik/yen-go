# GoTools Puzzles for YenGo

Downloaded from [cameron-martin/tsumego-solver](https://github.com/cameron-martin/tsumego-solver).

## Structure

SGF files are organized by YenGo difficulty level:
- `elementary/` - GoTools Level 1
- `intermediate/` - GoTools Level 2
- `upper-intermediate/` - GoTools Level 3
- `advanced/` - GoTools Level 4
- `low-dan/` - GoTools Level 5
- `high-dan/` - GoTools Level 6

## Usage

Use with LocalAdapter in sources.yaml:
```yaml
gotools:
  adapter: local
  enabled: true
  path: external-sources/gotools
```

## Source

- Repository: cameron-martin/tsumego-solver
- Format: GoTools compressed format (Thomas Wolf, 1994)
- Total puzzles: ~18,000 across 6 difficulty levels

## Level Mapping

| GoTools | YenGo Level | Rank Range |
|---------|-------------|------------|
| Lv1 | elementary | 20k-16k |
| Lv2 | intermediate | 15k-11k |
| Lv3 | upper-intermediate | 10k-6k |
| Lv4 | advanced | 5k-1k |
| Lv5 | low-dan | 1d-3d |
| Lv6 | high-dan | 4d-6d |
