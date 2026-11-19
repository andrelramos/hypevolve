import sys,json
sys.path.insert(0, ".")
import prob_script
r=prob_script.experiment(prob_script.setup())
e=json.load(open("reference_output.json"))
assert r == e, (r,e)
print("equivalence OK")
