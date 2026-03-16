# Group: robot_mission_MAS2026
# Date: 2026-03-16
# Members: Colin Friesh, Marie LUDUC , Hammale Mourad

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from model import RobotMission


def main():
    model = RobotMission(
        width=15,
        height=10,
        n_green_robots=3,
        n_yellow_robots=2,
        n_red_robots=2,
        n_initial_waste=12,
        seed=42,
    )

    max_steps = 300
    step = 0
    while model.running and step < max_steps:
        model.step()
        step += 1

    print(f"Simulation ended after {step} steps.")
    print(f"Total red waste deposited: {model.deposited}")

    df = model.datacollector.get_model_vars_dataframe()

    fig, axes = plt.subplots(2, 1, figsize=(10, 7))

    axes[0].plot(df["Green waste"],  label="Green waste",  color="green")
    axes[0].plot(df["Yellow waste"], label="Yellow waste", color="goldenrod")
    axes[0].plot(df["Red waste"],    label="Red waste",    color="crimson")
    axes[0].set_title("Waste remaining over time")
    axes[0].set_xlabel("Step")
    axes[0].set_ylabel("Count")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(df["Deposited"], label="Deposited (red)", color="navy")
    axes[1].set_title("Cumulative red waste deposited")
    axes[1].set_xlabel("Step")
    axes[1].set_ylabel("Count")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("simulation_results.png", dpi=150)
    print("Chart saved to simulation_results.png")


if __name__ == "__main__":
    main()
