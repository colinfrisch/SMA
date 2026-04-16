# Group 28 - Robot Mission MAS 2026
# Created: 2026-04-16
# Members: Colin Frisch, Marie Leduc, Mourad Hammale
"""Batch runs and statistical analysis of the simulation"""

import matplotlib.pyplot as plt
import numpy as np
from model import RobotMission
from objects import Waste

STEPS = 300
N_RUNS = 30


def run_one(steps=STEPS, **kwargs):
    """Run one simulation, return final stats."""
    m = RobotMission(**kwargs)
    for _ in range(steps):
        m.step()
    remaining = sum(1 for a in m.agents if isinstance(a, Waste))
    return m.waste_disposed_count, remaining, m.total_messages_sent


def collect_curves(steps=STEPS, **kwargs):
    """Run one simulation, return waste count arrays (green, yellow, red)."""
    m = RobotMission(**kwargs)
    g, y, r = [], [], []
    for _ in range(steps):
        m.step()
        g.append(m._count_waste("green"))
        y.append(m._count_waste("yellow"))
        r.append(m._count_waste("red"))
    return np.array(g), np.array(y), np.array(r)


# --- 1. Average waste dynamics over time ---
def experiment_dynamics():
    all_g, all_y, all_r = [], [], []
    for s in range(N_RUNS):
        g, y, r = collect_curves(n_green_waste=20, seed=s)
        all_g.append(g); all_y.append(y); all_r.append(r)

    fig, ax = plt.subplots()
    x = np.arange(1, STEPS + 1)
    for arr, color, label in [(all_g, "#00cc44", "Green"), (all_y, "#e6c800", "Yellow"), (all_r, "#cc0000", "Red")]:
        mean = np.mean(arr, axis=0)
        std = np.std(arr, axis=0)
        ax.plot(x, mean, color=color, label=label)
        ax.fill_between(x, mean - std, mean + std, color=color, alpha=0.15)
    ax.set_xlabel("Step")
    ax.set_ylabel("Waste on grid")
    ax.set_title(f"Average waste dynamics ({N_RUNS} runs, 20 initial green)")
    ax.legend()
    fig.tight_layout()
    fig.savefig("batch_dynamics.png", dpi=150)
    plt.close(fig)
    print("  Saved batch_dynamics.png")


# --- 2. Disposed count vs robot count ---
def experiment_robot_count():
    counts = [1, 2, 3, 5, 7, 10]
    disposed_m, disposed_s, remaining_m = [], [], []
    for n in counts:
        results = [run_one(n_green=n, n_yellow=n, n_red=n, n_green_waste=20, seed=s) for s in range(N_RUNS)]
        d = [r[0] for r in results]
        rem = [r[1] for r in results]
        disposed_m.append(np.mean(d)); disposed_s.append(np.std(d))
        remaining_m.append(np.mean(rem))
        print(f"  robots={n}: disposed={disposed_m[-1]:.1f}±{disposed_s[-1]:.1f}, remaining={remaining_m[-1]:.1f}")

    fig, ax1 = plt.subplots()
    ax1.errorbar(counts, disposed_m, yerr=disposed_s, marker="o", capsize=4, label="Disposed")
    ax1.set_xlabel("Robots per type")
    ax1.set_ylabel("Waste disposed (after 300 steps)")
    ax2 = ax1.twinx()
    ax2.plot(counts, remaining_m, marker="s", color="red", label="Remaining")
    ax2.set_ylabel("Waste remaining", color="red")
    ax1.legend(loc="upper left"); ax2.legend(loc="upper right")
    ax1.set_title("Performance vs robot count (20 initial green)")
    fig.tight_layout()
    fig.savefig("batch_robot_count.png", dpi=150)
    plt.close(fig)
    print("  Saved batch_robot_count.png")


# --- 3. Communication range impact ---
def experiment_communication():
    ranges = [0, 3, 5, 10, 20]
    disposed_m, disposed_s = [], []
    for r in ranges:
        results = [run_one(n_green_waste=20, communication_range=r, seed=s) for s in range(N_RUNS)]
        d = [x[0] for x in results]
        disposed_m.append(np.mean(d)); disposed_s.append(np.std(d))
        print(f"  range={r}: disposed={disposed_m[-1]:.1f}±{disposed_s[-1]:.1f}")

    fig, ax = plt.subplots()
    ax.errorbar(ranges, disposed_m, yerr=disposed_s, marker="s", capsize=4, color="green")
    ax.set_xlabel("Communication range")
    ax.set_ylabel("Waste disposed (after 300 steps)")
    ax.set_title("Impact of communication range (20 initial green)")
    fig.tight_layout()
    fig.savefig("batch_communication.png", dpi=150)
    plt.close(fig)
    print("  Saved batch_communication.png")


# --- 4. Distribution of disposed count over 100 runs ---
def experiment_distribution():
    results = [run_one(n_green_waste=20, seed=s) for s in range(100)]
    disposed = [r[0] for r in results]
    remaining = [r[1] for r in results]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    ax1.hist(disposed, bins=range(0, max(disposed) + 2), edgecolor="black", alpha=0.7, color="steelblue")
    ax1.axvline(np.mean(disposed), color="red", linestyle="--", label=f"mean={np.mean(disposed):.1f}")
    ax1.set_xlabel("Waste disposed"); ax1.set_ylabel("Frequency")
    ax1.set_title("Disposed (100 runs)"); ax1.legend()

    ax2.hist(remaining, bins=15, edgecolor="black", alpha=0.7, color="salmon")
    ax2.axvline(np.mean(remaining), color="red", linestyle="--", label=f"mean={np.mean(remaining):.1f}")
    ax2.set_xlabel("Waste remaining"); ax2.set_ylabel("Frequency")
    ax2.set_title("Remaining (100 runs)"); ax2.legend()

    fig.tight_layout()
    fig.savefig("batch_distribution.png", dpi=150)
    plt.close(fig)
    print(f"  disposed: mean={np.mean(disposed):.1f}, std={np.std(disposed):.1f}")
    print(f"  remaining: mean={np.mean(remaining):.1f}, std={np.std(remaining):.1f}")
    print("  Saved batch_distribution.png")


if __name__ == "__main__":
    print("1/4 Waste dynamics...")
    experiment_dynamics()
    print("2/4 Robot count impact...")
    experiment_robot_count()
    print("3/4 Communication range...")
    experiment_communication()
    print("4/4 Distribution...")
    experiment_distribution()
    print("Done!")
