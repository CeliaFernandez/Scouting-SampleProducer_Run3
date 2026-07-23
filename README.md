# Scouting-SampleProducer_Run3

## Global Tag

`scripts/submit_gensim.py` runs GEN-SIM with `--conditions 150X_mcRun3_2024_realistic_v3`
(used instead of the official campaign GT `140X_mcRun3_2024_realistic_v26` since we're
running under CMSSW_17_0_0, where the 140X tag isn't available). The two GTs only differ
in the AK4PFPuppi jet-correction payload, which GEN-SIM doesn't use, so this has no effect
on the output.

## Setup

```sh
# 1. CMSSW area matching the GT above
export SCRAM_ARCH=el9_amd64_gcc13
source /cvmfs/cms.cern.ch/cmsset_default.sh
cmsrel CMSSW_17_0_0_pre2
cd CMSSW_17_0_0_pre2/src
cmsenv

# 2. Grid proxy (needed for CRAB submission, not for a local test)
voms-proxy-init --voms cms --valid 168:00

# 3. CRAB env (needed for CRAB submission, not for a local test)
source /cvmfs/cms.cern.ch/crab3/crab.sh
```

## Launch and test locally

Before submitting anything to CRAB, generate a cfg for a single fragment and run it
locally with a handful of events to make sure it doesn't crash.

```sh
cd $CMSSW_BASE/src

# Install the fragments so cmsDriver can find them as
# Configuration/GenProduction/python/<name>_cfi.py
mkdir -p Configuration/GenProduction/python
cp ../../2024-fragments/complete/*_cfi.py Configuration/GenProduction/python/
scram b -j 8

# Generate the cfg for one sample (swap in the fragment you want to test)
FRAGMENT=GluGluHToDarkShowers-ScenarioA_Par-ctau-0p25-mA-1p67-mpi-5_cfi.py
cmsDriver.py Configuration/GenProduction/python/$FRAGMENT \
  --era Run3_2024 \
  --customise Configuration/DataProcessing/Utils.addMonitoring \
  --beamspot DBrealistic \
  --step LHE,GEN,SIM \
  --geometry DB:Extended \
  --conditions 150X_mcRun3_2024_realistic_v3 \
  --customise_commands 'process.RandomNumberGeneratorService.externalLHEProducer.initialSeed=12345' \
  --datatier GEN-SIM \
  --eventcontent RAWSIM \
  --python_filename test_cfg.py \
  --fileout file:test.root \
  --number 10 --number_out 10 \
  --no_exec --mc

# SEED is referenced in the cfg via the customise_commands above — set it before running
SEED=1 cmsRun test_cfg.py
```

If `cmsRun` completes and `test.root` is produced with 10 events, the fragment and GT
combination is good to submit. Repeat with `--filter` restricted to a couple of other
mass points/ctaus before trusting the whole batch.

Alternatively, `submit_gensim.py --dry-run --filter <sample>` will print the exact
`cmsDriver.py`/CRAB commands it would run for a given sample without executing anything —
useful for sanity-checking flags before doing the manual local test above.

## Submit to CRAB

```sh
python3 scripts/submit_gensim.py \
  --lfn-base /store/user/<your-username>/samples/GEN-SIM/ \
  --site <your-T2-site> \
  --dry-run          # drop this once the printed commands look right
```

Use `--filter` (substring match on the fragment filename, e.g. `ScenarioA` or `mpi-1p2`)
or the hardcoded `DATASETS` list at the top of `main()` in `submit_gensim.py` to restrict
which samples get submitted. Already-submitted samples (detected via
`<work-area>/<name>/crab_<name>/`) are skipped automatically, so the command is safe to
re-run.

## RAWSIM (DIGI/DATAMIX/L1/DIGI2RAW premix) step

Once the GEN-SIM samples above are published, `scripts/submit_rawsim.py` runs the premix
DIGI/RAW step on top of them — the same cmsDriver command baked into
`CMSSW_17_0_0_pre2/src/rawsim_cfg.py`. Unlike GEN-SIM, this step doesn't read a
sample-specific fragment — CRAB substitutes the actual input files at runtime per
`Data.inputDataset` — so the script generates a single shared cfg
(`<work-area>/rawsim_cfg.py`) once and reuses it for every sample. For each sample it then:

1. Looks up the published GEN-SIM dataset via `dasgoclient` (matching
   `/<sample>/*<gensim-tag>*/<dataset-tier>`, default tag
   `RunIII2024Summer24wmLHEGS` and tier `GEN-SIM` — the defaults `submit_gensim.py` uses).
2. Writes a CRAB config with `JobType.pluginName = 'Analysis'`, `JobType.psetName` pointing
   at the shared cfg, `Data.inputDataset` set to the dataset found in step 1, and
   `FileBased` splitting (since the input already exists as a dataset, unlike the
   `PrivateMC`/`EventBased` submission used for GEN-SIM).
3. Submits.

```sh
python3 scripts/submit_rawsim.py \
  --lfn-base /store/user/<your-username>/samples/GEN-SIM-RAW/ \
  --site <your-T2-site> \
  --dry-run          # drop this once the printed commands look right
```

Requires a `dasgoclient`-capable environment and a valid grid proxy (same CRAB env from
Setup above). `--filter` and the hardcoded `DATASETS` dict at the top of `main()` work the
same way as `submit_gensim.py` — `DATASETS` here maps sample name directly to an explicit
`input_dataset` path, useful to skip the `dasgoclient` lookup or pin a specific dataset.
Already-submitted samples (`<work-area>/<name>/crab_<name>_RAWSIM/`) are skipped
automatically.
