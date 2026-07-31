# Scouting-SampleProducer_Run3

## Global Tag

`scripts/submit_gensim.py` runs GEN-SIM with `--conditions 150X_mcRun3_2024_realistic_v3`
(used instead of the official campaign GT `140X_mcRun3_2024_realistic_v26` since we're
running under CMSSW_17_0_0, where the 140X tag isn't available). The two GTs only differ
in the AK4PFPuppi jet-correction payload, which GEN-SIM doesn't use, so this has no effect
on the output.

## Setup

Running on **lxplus8**!

```sh
# 1. CMSSW area matching the GT above
export SCRAM_ARCH=el8_amd64_gcc12
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
FRAGMENT=GluGluHToDarkShowers-ScenarioA_Par-ctau-10-mA-1p67-mpi-5_cfi.py
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
  --number 100 \
  --no_exec --mc
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
  --lfn-base /store/user/fernance/FinalScoutingProduction/GEN-SIM/ \
  --n-events 1000000 \
  --events-per-job 1000 \
  --site T2_US_UCSD \
  --dry-run          # drop this once the printed commands look right
```

Use `--filter` (substring match on the fragment filename, e.g. `ScenarioA` or `mpi-1p2`)
or the hardcoded `DATASETS` list at the top of `main()` in `submit_gensim.py` to restrict
which samples get submitted. Already-submitted samples (detected via
`<work-area>/<name>/crab_<name>/`) are skipped automatically, so the command is safe to
re-run.

## RAWSIM (DIGI/DATAMIX/L1/DIGI2RAW premix) step

Once the GEN-SIM samples above are published, `scripts/submit_rawsim.py` runs the premix
DIGI/RAW step on top of them, reusing the cfg already produced in `chain/rawsim_cfg.py`
(see "Launch and test locally" below for how that file is generated). Unlike GEN-SIM, this
step doesn't read a sample-specific fragment — CRAB substitutes the actual input files at
runtime per `Data.inputDataset` — so the same cfg covers every sample. For each sample it
then:

1. Copies `chain/rawsim_cfg.py` into a single self-contained pset
   (`<work-area>/rawsim_cfg.py`), shared by every sample, with `process.maxEvents.input`
   reset to `-1`. `chain/rawsim_cfg.py` was generated locally with `--number 100`; without
   this override every CRAB job would stop after 100 events instead of processing (and
   writing) every event in its input file(s).
2. Writes a CRAB config with `JobType.pluginName = 'Analysis'`, `JobType.psetName` pointing
   at the shared cfg from step 1, `Data.inputDataset` set to the sample's entry in the
   hardcoded `RAWSIM_DATASETS` dict (see below), `FileBased` splitting (since the input
   already exists as a dataset, unlike the `PrivateMC`/`EventBased` submission used for
   GEN-SIM) and `Data.totalUnits = -1` so all files — and therefore all events — of the
   input dataset are processed.
3. Submits.

### Launch and test locally

As with GEN-SIM, run the premix step locally on the `test.root` produced above before
submitting to CRAB:

```sh
cd $CMSSW_BASE/src

cmsDriver.py \
  --era Run3_2024 \
  --customise Configuration/DataProcessing/Utils.addMonitoring \
  --procModifiers premix_stage2 \
  --datamix PreMix \
  --step DIGI,DATAMIX,L1,DIGI2RAW \
  --geometry DB:Extended \
  --conditions 150X_mcRun3_2024_realistic_v3 \
  --datatier GEN-SIM-RAW \
  --eventcontent PREMIXRAW \
  --python_filename rawsim_cfg.py \
  --fileout file:rawsim_out.root \
  --filein file:test.root \
  --number 100 \
  --pileup_input dbs:/Neutrino_E-10_gun/RunIIISummer24PrePremix-Premixlib2024_140X_mcRun3_2024_realistic_v26-v1/PREMIX \
  --no_exec --mc
```

If `cmsRun` completes and produces `rawsim_out.root`, copy the resulting `rawsim_cfg.py`
into `chain/rawsim_cfg.py` — that's the file `scripts/submit_rawsim.py` reuses for every
CRAB submission (it is never regenerated by the script itself).

### Test the CRAB submission itself before going to the grid

Two levels, cheapest first:

1. **Sanity-check the pset `submit_rawsim.py` will actually submit** (with the
   `maxEvents.input = -1` override applied) by running it locally on the `test.root`
   from above, no CRAB/grid involved:

   ```sh
   python3 scripts/submit_rawsim.py --work-area crab_rawsim_test   # writes crab_rawsim_test/rawsim_cfg.py, no --dry-run so the file gets written
   cd crab_rawsim_test && cmsRun rawsim_cfg.py
   ```

2. **Exercise the real CRAB machinery without launching grid jobs**, using `--crab-dryrun`
   (passes `--dryrun` through to `crab submit`, which validates the config and builds the
   sandbox/pset but submits nothing) followed by `crab preparelocal` to run one job locally
   against a real input file from the dataset:

   ```sh
   python3 scripts/submit_rawsim.py --crab-dryrun --work-area crab_rawsim_test --filter <sample>
   crab preparelocal -d crab_rawsim_test/<sample>/crab_<sample>_RAWSIM
   cd crab_rawsim_test/<sample>/crab_<sample>_RAWSIM/local && ./run_local.sh
   ```

   Use a throwaway `--work-area` (as above) for both — a real `crab submit` afterwards
   looks for `<work-area>/<name>/crab_<name>_RAWSIM/` to decide a sample was already
   submitted and would otherwise skip it.

```sh
python3 scripts/submit_rawsim.py \
  --lfn-base /store/user/<your-username>/samples/GEN-SIM-RAW/ \
  --site <your-T2-site> \
  --dry-run          # drop this once the printed commands look right
```

Requires a valid grid proxy (same CRAB env from Setup above). `--filter` narrows by
substring on the sample name. The published GEN-SIM dataset for each sample must be
hardcoded in the `RAWSIM_DATASETS` dict at the top of `main()` in `submit_rawsim.py` —
look it up once with `dasgoclient -query="dataset dataset=/<name>/*/GEN-SIM"` after
`submit_gensim.py`'s job has finished and published. The script refuses to run while a
sample's entry is still the placeholder value. Already-submitted samples
(`<work-area>/<name>/crab_<name>_RAWSIM/`) are skipped automatically.

## HLT: reL1 + HLT

Inputs should be the ones from the RAWSIM step.

:warning: Files are already available in hlt_re-emulation/ folder so it it enough with copying, but instructions to produce it are here.

### 1: 2022 setup


### 1: 2023 setup


### 1: 2024 setup

Should be run on CMSSW_14_0_21 (same as central production but any after CMSSW_14_0_18 should have the correct menu):

```sh
export SCRAM_ARCH=el8_amd64_gcc13
source /cvmfs/cms.cern.ch/cmsset_default.sh
cmsrel CMSSW_14_1_0
cd CMSSW_14_1_0/src
cmsenv
```
Recipe for emulation is this one:

```sh
hltGetConfiguration /dev/CMSSW_14_1_0/GRun \
--globaltag 150X_mcRun3_2024_realistic_v3 \
--mc \
--input file:rawsim_out.root  \
--max-events -1  \
--output full  \
--unprescale \
--eras Run3_2024 \
--l1-emulator uGT --l1 L1Menu_Collisions2024_v1_3_0_xml \
--paths ScoutingPFOutput,\
DST_PFScouting_*,\
Dataset_ScoutingPFRun3 \
> reHLT_mc_2024.py

echo 'process.source.bypassVersionCheck = cms.untracked.bool(True)' >> reHLT_mc_2024.py
echo 'process.source.inputCommands = cms.untracked.vstring("keep *","drop TH2PolyMEtoEDM_*_*_*")' >> reHLT_mc_2024.py
echo 'process.options.wantSummary = False' >> reHLT_mc_2024.py
```

### 1: 2025 setup

Should be run on CMSSW_15_0_15_patch1:

```sh
export SCRAM_ARCH=el8_amd64_gcc13
source /cvmfs/cms.cern.ch/cmsset_default.sh
cmsrel CMSSW_15_0_15_patch1
cd CMSSW_15_0_15_patch1/src
cmsenv
```

:warning: The file is already available in hlt_re-emulation/ folder so it it enough with copying, but instructions to produce it are here.

Recipe for emulation is this one:

```sh
hltGetConfiguration /dev/CMSSW_15_0_0/GRun \
--globaltag 150X_mcRun3_2024_realistic_v3  \
--mc \
--input file:rawsim_out.root  \
--max-events -1  \
--output full  \
--unprescale  \
--eras Run3_2025  \
--l1-emulator uGT --l1 L1Menu_Collisions2025_v1_3_0_xml  \
--paths ScoutingPFOutput,\
DST_PFScouting_*,\
Dataset_ScoutingPFRun3 \
> reHLT_mc_2025.py

echo 'process.source.bypassVersionCheck = cms.untracked.bool(True)' >> reHLT_mc_2025.py
echo 'process.source.inputCommands = cms.untracked.vstring("keep *","drop TH2PolyMEtoEDM_*_*_*")' >> reHLT_mc_2025.py
echo 'process.options.wantSummary = False' >> reHLT_mc_2025.py
```

### 1: 2026 setup

```sh
export SCRAM_ARCH=el8_amd64_gcc13
source /cvmfs/cms.cern.ch/cmsset_default.sh
cmsrel CMSSW_16_1_0
cd CMSSW_16_1_0/src
cmsenv
```

:warning: The file is already available in hlt_re-emulation/ folder so it it enough with copying, but instructions to produce it are here.

Recipe for emulation is this one:

```sh
hltGetConfiguration /dev/CMSSW_16_1_0/GRun \
--globaltag 150X_mcRun3_2024_realistic_v3  \
--mc \
--input file:rawsim_out.root  \
--max-events -1  \
--output full  \
--unprescale  \
--eras Run3_2026  \
--l1-emulator uGT --l1 L1Menu_Collisions2026_v1_1_0_xml   \
--paths ScoutingPFOutput,\
DST_PFScouting_*,\
Dataset_ScoutingPFRun3 \
> reHLT_mc_2026.py

echo 'process.source.bypassVersionCheck = cms.untracked.bool(True)' >> reHLT_mc_2026.py
echo 'process.source.inputCommands = cms.untracked.vstring("keep *","drop TH2PolyMEtoEDM_*_*_*")' >> reHLT_mc_2026.py
echo 'process.options.wantSummary = False' >> reHLT_mc_2026.py
```

### 2: Event content - reduced

Define the full event content:
```sh
process.hltOutputFull.outputCommands = cms.untracked.vstring(
    "drop *",
    "keep *_*Packer*_*_*",
    "keep FEDRawDataCollection_*_*_*",
    "keep *_gtStage2Digis_*_*",
    "keep edmTriggerResults_*_*_*",
    "keep *_addPileupInfo_*_*"
)
```

But preferred is the **reduced**:

```sh
process.hltOutputFull.outputCommands = cms.untracked.vstring(
    "drop *",
    "keep *_*Packer*_*_*",
    "keep FEDRawDataCollection_hltFEDSelectorL1_*_*",
    "keep *_gtStage2Digis_*_*",
    "keep edmTriggerResults_*_*_*",
    "keep *_addPileupInfo_*_*",
    "keep *_genParticles_*_*",
)
```

### 3: Process renaming

Replace "HLTX" by "HLT" in the process of every config file of every year