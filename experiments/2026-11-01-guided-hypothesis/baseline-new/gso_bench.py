import sys,time
sys.path.insert(0, ".")
import prob_script
data=prob_script.setup()
t=time.perf_counter(); prob_script.experiment(data); print(f"{time.perf_counter()-t:.9f}")
