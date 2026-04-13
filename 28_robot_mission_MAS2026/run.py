"""Main script to run the RobotMission model and visualize results"""

import matplotlib.pyplot as plt
from model import RobotMission

if __name__ == "__main__":
    model = RobotMission(
        n_green=3,
        n_yellow=3,
        n_red=3,
        n_green_waste=10,
        width=30,
        height=10,
    )

    N_STEPS = 200
    for _ in range(N_STEPS):
        model.step()

    data = model.datacollector.get_model_vars_dataframe()
    print(data.tail(10))

    # Plot the number of wastes remaining on the grid over time
    data[["Green Waste", "Yellow Waste", "Red Waste"]].plot(
        title="Waste count over time",
        xlabel="Step",
        ylabel="Number of waste items on grid",
        color={"Green Waste": "#00cc44", "Yellow Waste": "#ffdd00", "Red Waste": "#ff3300"},
    )
    plt.tight_layout()
    plt.show()
