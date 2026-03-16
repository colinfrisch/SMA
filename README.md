# Robot Mission MAS 2026

Multi-agent simulation of robots collecting radioactive waste across a zoned grid.

**Group:** Colin Friesh, Marie LUDUC, Hammale Mourad
**Date:** 2026-03-16

## Overview

The simulation models a 3-zone grid where specialized robots cooperate to collect and dispose of radioactive waste:

- **Zone 1** (green) — Green robots collect and merge green waste into yellow
- **Zone 2** (yellow) — Yellow robots collect and merge yellow waste into red
- **Zone 3** (red) — Red robots carry red waste to the disposal zone and deposit it

Each robot can only enter zones up to its clearance level. The simulation ends when all waste has been deposited.

## Setup

Requires Python 3.10+ and [uv](https://github.com/astral-sh/uv).

```bash
cd SMA
uv sync
```

## Run

**Headless** (saves `simulation_results.png`):
```bash
python run.py
```

**Interactive web visualization** (opens browser at `http://localhost:8765`):
```bash
solara run server.py
```

The web UI provides sliders to adjust grid size, robot counts, initial waste count, and simulation speed.

## Default Parameters

| Parameter | Value |
|---|---|
| Grid size | 15 × 10 |
| Green robots | 3 |
| Yellow robots | 2 |
| Red robots | 2 |
| Initial green waste | 12 |
| Max steps | 300 |

## Architecture

| File | Role |
|---|---|
| `objects.py` | Passive agents: `RadioactivityAgent`, `WasteAgent`, `WasteDisposalZone` |
| `agents.py` | Robot agents: `GreenAgent`, `YellowAgent`, `RedAgent` with deliberative logic |
| `model.py` | `RobotMission` model — grid setup, action execution, data collection |
| `run.py` | Headless runner with matplotlib chart output |
| `server.py` | Solara web visualization |

## Dependencies

- [Mesa 3.x](https://mesa.readthedocs.io/) — agent-based modeling framework
- [Solara](https://solara.dev/) — reactive web visualization
- [matplotlib](https://matplotlib.org/) — chart generation
