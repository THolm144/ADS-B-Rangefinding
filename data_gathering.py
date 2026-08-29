import pandas as pd

dipole_summary_path = "[PATH TO DIPOLE FILE SUMMARY"
reflector_summary_path = "PATH TO RELFECTOR SUMMARY CSV"

dipole = pd.read_csv(dipole_summary_path)
reflector = pd.read_csv(reflector_summary_path)

# Extract column maximum values using df['column'].max()
max_range_reflector = reflector["best_range_nm"].max()
max_range_dipole = dipole["best_range_nm"].max()

mean_range_reflector = reflector["median_best_range_nm"].max()
mean_range_dipole = dipole["median_best_range_nm"].max()

number_pickups_reflector = reflector["unique_icaos"].max()
number_pickups_dipole = dipole["unique_icaos"].max()

# Percentage improvement calculation (relative to the baseline dipole)
percent_improvement_max = ((max_range_reflector - max_range_dipole) / max_range_dipole) * 100
percent_improvement_mean = ((mean_range_reflector - mean_range_dipole) / mean_range_dipole) * 100

print(f"The Improvement the Reflector Gives to Max Range is {percent_improvement_max:.2f}%")
print(f"The Improvement the Reflector Gives to Mean Range is {percent_improvement_mean:.2f}%")
print(f"The Dipole Picked up {number_pickups_dipole} Unique Planes")
print(f"The Reflector Picked up {number_pickups_reflector} Unique Planes")
