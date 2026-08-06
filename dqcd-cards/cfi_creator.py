import os

p = "../data/"
files = os.listdir(p)

for f in files:
    name = f.split(".")[0]
    print(name)
    os.system("cp scenarioA_mpi_4_mA_1p33_ctau_10_cfi.py %s_cfi.py" % name)
    os.system("sed -i 's/scenarioA_mpi_4_mA_1p33_ctau_10_cfi/%s/g' %s_cfi.py" % (name, name))
