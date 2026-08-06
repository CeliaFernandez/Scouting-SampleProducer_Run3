# Scouting-SampleProducer_Run3

## Global Tag

`scripts/submit_gensim.py` runs GEN-SIM with `--conditions 150X_mcRun3_2024_realistic_v3`
(used instead of the official campaign GT `140X_mcRun3_2024_realistic_v26` since we're
running under CMSSW_17_0_0, where the 140X tag isn't available). The two GTs only differ
in the AK4PFPuppi jet-correction payload, which GEN-SIM doesn't use, so this has no effect
on the output.

## Setup with 17X (failed)

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

## GEN-SIM -> RAWSIM in one job (no intermediate dataset)

`scripts/submit_gensim_rawsim_chain.py` is an alternative to the two-task
`submit_gensim.py` + `submit_rawsim.py` pipeline above, for when you don't want the
intermediate GEN-SIM staged out/published at all. GEN-SIM is still produced first and RAWSIM
second — two separate `cmsDriver.py` cfgs, `step1_cfg.py` (`LHE,GEN,SIM`, per sample, from
the fragment) and `step2_cfg.py` (`DIGI,DATAMIX,L1,DIGI2RAW`, shared across samples like
`submit_rawsim.py`'s cfg) — but both run inside **one** CRAB job:
`JobType.pluginName = 'PrivateMC'` with `JobType.scriptExe = 'scripts/run_chain.sh'`, which
just runs `cmsRun` on `step1_cfg.py` then on `step2_cfg.py` back to back. `step1_cfg.py`
writes a local scratch file (`step1_gensim.root`) that `step2_cfg.py` immediately reads back
in via `--filein`; only step2's output (`rawsim.root`, listed in `JobType.outputFiles`) is
staged out.

Since `scriptExe` bypasses CRAB running `psetName` directly, CRAB never gets to patch
`process.maxEvents.input` down to `Data.unitsPerJob` the way it does for the plain
`submit_gensim.py` task — so `step1_cfg.py`'s `--number` is baked to `--events-per-job` at
cfg-generation time instead (see `STEP1_CMSDRIVER_TEMPLATE` in the script); `step2_cfg.py`
keeps `--number -1` and just processes whatever step1 wrote.

The same bypass applies to per-job random seeding: CRAB only randomizes
`RandomNumberGeneratorService` when it runs `psetName` directly, so every job would
otherwise generate with the *same* hardcoded seed (correlated/duplicate events across the
whole sample). `step1_cfg.py`'s `--customise_commands` instead reads `$CRAB_Id` — the
per-job number CRAB always exports into the job's environment, `scriptExe` or not — at
`cmsRun` runtime and derives a distinct seed per job from it, for the PSets the `LHE,GEN,SIM`
step actually uses (`externalLHEProducer`, `generator`, `VtxSmeared`, `g4SimHits`). It has to
be one semicolon-joined line, not a `for` loop over `parameterNames_()`: cmsDriver executes
`--customise_commands` via `exec()` on the raw string, and a loop needs literal newlines,
which corrupt cmsDriver's own auto-generated header comment; a list comprehension avoids
that but then loses access to `self` inside that `exec()` instead. Both fail; explicit
semicolon-joined assignments are the only form that survives.

### Launch and test locally

Run the same two `cmsDriver.py` calls `submit_gensim_rawsim_chain.py` would generate,
followed by `run_chain.sh` itself, with a handful of events:

```sh
cd $CMSSW_BASE/src

FRAGMENT=GluGluHToDarkShowers-ScenarioA_Par-ctau-10-mA-1p67-mpi-5_cfi.py
cmsDriver.py Configuration/GenProduction/python/$FRAGMENT \
  --era Run3_2024 \
  --customise Configuration/DataProcessing/Utils.addMonitoring \
  --beamspot DBrealistic \
  --step LHE,GEN,SIM \
  --geometry DB:Extended \
  --conditions 150X_mcRun3_2024_realistic_v3 \
  --customise_commands "import os;_seed=int(os.environ.get('CRAB_Id','1'));process.RandomNumberGeneratorService.externalLHEProducer.initialSeed=(_seed*4+1)%900000000+1;process.RandomNumberGeneratorService.generator.initialSeed=(_seed*4+2)%900000000+1;process.RandomNumberGeneratorService.VtxSmeared.initialSeed=(_seed*4+3)%900000000+1;process.RandomNumberGeneratorService.g4SimHits.initialSeed=(_seed*4+4)%900000000+1" \
  --datatier GEN-SIM \
  --eventcontent RAWSIM \
  --python_filename step1_cfg.py \
  --fileout file:step1_gensim.root \
  --number 10 --number_out 10 \
  --no_exec --mc

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
  --python_filename step2_cfg.py \
  --fileout file:rawsim.root \
  --filein file:step1_gensim.root \
  --number -1 --number_out -1 \
  --pileup_input dbs:/Neutrino_E-10_gun/RunIIISummer24PrePremix-Premixlib2024_140X_mcRun3_2024_realistic_v26-v1/PREMIX \
  --no_exec --mc

# run_chain.sh isn't a static file — submit_gensim_rawsim_chain.py generates it per
# work-area (see generate_run_chain()) — so for a local test just write the same steps:
cat > run_chain.sh << 'EOF'
#!/bin/bash
set -e
cmsRun -j FrameworkJobReport1.xml step1_cfg.py
mv rawsim.root step1_gensim.root
cmsRun -j FrameworkJobReport.xml step2_cfg.py
EOF
chmod +x run_chain.sh && ./run_chain.sh
```

If `run_chain.sh` completes and `rawsim.root` is produced with 10 events, the fragment/GT/pileup
combination is good to submit. Repeat with `--filter` restricted to a couple of other mass
points/ctaus before trusting the whole batch.

Alternatively, `submit_gensim_rawsim_chain.py --dry-run --filter <sample>` prints the exact
`cmsDriver.py`/CRAB commands it would run without executing anything.

### Submit to CRAB

```sh
python3 scripts/submit_gensim_rawsim_chain.py \
  --lfn-base /store/user/fernance/FinalScoutingProduction/GEN-SIM-RAW/ \
  --n-events 1000000 \
  --events-per-job 1000 \
  --site T2_US_UCSD \
  --dry-run          # drop this once the printed commands look right
```

`--filter`, the hardcoded `DATASETS` list, and the already-submitted skip check (via
`<work-area>/<name>/crab_<name>_GENSIM_RAWSIM/`) all work the same way as
`submit_gensim.py`. `--max-memory-mb` (default 4000) gives the job more headroom than a
plain GEN-SIM task since it now runs GEN+SIM+DIGI+premix sequentially — bump it further (and
consider lowering `--events-per-job`) if jobs run out of memory or time out.

## GEN-SIM -> RAWSIM+HLT2024 in one job (no intermediate dataset)

`scripts/submit_gensim_rawsim_hlt2024_chain.py` is the same two-cfg/`scriptExe` design as
`submit_gensim_rawsim_chain.py` above (GEN-SIM produced first as `step1_cfg.py`, RAWSIM
second as `step2_cfg.py`, both run by `run_chain.sh` inside one CRAB job) — the only
differences are step2's `--step` list, which adds `HLT:2024v14`
(`DIGI,DATAMIX,L1,DIGI2RAW,HLT:2024v14`), and the GT/release both steps use, matching the
RAWSIM+HLT `cmsDriver` command (`--conditions 140X_mcRun3_2024_realistic_v26`).

**Different CMSSW release than everything else in this README**: `HLT:2024v14` resolves
against the HLT menu/table shipped in a specific release, and that GT isn't available under
`CMSSW_17_0_0_pre2` — so unlike `submit_gensim_rawsim_chain.py`, *both* `step1_cfg.py` and
`step2_cfg.py` here use `140X_mcRun3_2024_realistic_v26`, and the whole thing runs from
`CMSSW_14_0_21`:

```sh
export SCRAM_ARCH=el8_amd64_gcc12
source /cvmfs/cms.cern.ch/cmsset_default.sh
cmsrel CMSSW_14_0_21
cd CMSSW_14_0_21/src
cmsenv
```

The script checks `$CMSSW_VERSION` against this and refuses to submit (warns under
`--dry-run`) from the wrong release.

Per-job seeding works the same way as `submit_gensim_rawsim_chain.py` (see that section
above): `step1_cfg.py`'s `--customise_commands` derives a distinct seed per job from
`$CRAB_Id` at `cmsRun` runtime, since `scriptExe` bypasses CRAB's usual automatic seeding.

### Launch and test locally

Needs a valid grid proxy even for a local run — `--pileup_input` resolves the premix file
list via DAS at cfg-generation time, and an expired proxy silently produces an empty pileup
list instead of failing loudly (`voms-proxy-init --voms cms --valid 168:00` if
`voms-proxy-info --timeleft` comes back `0:00:00`).

```sh
cd $CMSSW_BASE/src   # CMSSW_14_0_21

FRAGMENT=GluGluHToDarkShowers-ScenarioA_Par-ctau-10-mA-1p67-mpi-5_cfi.py
cmsDriver.py Configuration/GenProduction/python/$FRAGMENT \
  --era Run3_2024 \
  --customise Configuration/DataProcessing/Utils.addMonitoring \
  --beamspot DBrealistic \
  --step LHE,GEN,SIM \
  --geometry DB:Extended \
  --conditions 140X_mcRun3_2024_realistic_v26 \
  --customise_commands "import os;_seed=int(os.environ.get('CRAB_Id','1'));process.RandomNumberGeneratorService.externalLHEProducer.initialSeed=(_seed*4+1)%900000000+1;process.RandomNumberGeneratorService.generator.initialSeed=(_seed*4+2)%900000000+1;process.RandomNumberGeneratorService.VtxSmeared.initialSeed=(_seed*4+3)%900000000+1;process.RandomNumberGeneratorService.g4SimHits.initialSeed=(_seed*4+4)%900000000+1" \
  --datatier GEN-SIM \
  --eventcontent RAWSIM \
  --python_filename step1_cfg.py \
  --fileout file:rawsim_hlt2024.root \
  --number 10 --number_out 10 \
  --no_exec --mc

cmsDriver.py \
  --era Run3_2024 \
  --customise Configuration/DataProcessing/Utils.addMonitoring \
  --procModifiers premix_stage2 \
  --datamix PreMix \
  --step DIGI,DATAMIX,L1,DIGI2RAW,HLT:2024v14 \
  --geometry DB:Extended \
  --conditions 140X_mcRun3_2024_realistic_v26 \
  --datatier GEN-SIM-RAW \
  --eventcontent PREMIXRAW \
  --customise_commands 'process.PREMIXRAWoutput.outputCommands = cms.untracked.vstring("drop *","keep *_*Packer*_*_*","keep FEDRawDataCollection_hltFEDSelectorL1_*_*","keep *_gtStage2Digis_*_*","keep edmTriggerResults_*_*_*","keep *_addPileupInfo_*_*","keep *_genParticles_*_*",)' \
  --python_filename step2_cfg.py \
  --fileout file:rawsim_hlt2024.root \
  --filein file:step1_gensim.root \
  --number -1 --number_out -1 \
  --pileup_input dbs:/Neutrino_E-10_gun/RunIIISummer24PrePremix-Premixlib2024_140X_mcRun3_2024_realistic_v26-v1/PREMIX \
  --no_exec --mc

# run_chain.sh isn't a static file — submit_gensim_rawsim_hlt2024_chain.py generates it per
# work-area (see generate_run_chain()) — so for a local test just write the same steps:
cat > run_chain.sh << 'EOF'
#!/bin/bash
set -e
cmsRun -j FrameworkJobReport1.xml step1_cfg.py
mv rawsim_hlt2024.root step1_gensim.root
cmsRun -j FrameworkJobReport.xml step2_cfg.py
EOF
chmod +x run_chain.sh && ./run_chain.sh
```

If it completes, inspect the result:

```sh
edmFileUtil rawsim_hlt2024.root          # event count, file size
edmDumpEventContent rawsim_hlt2024.root  # collections that survived the outputCommands above
```

A generator-level matching filter in the fragment can make `step1_gensim.root` end up with
fewer events than `--number` asked for (check `Filter efficiency` in step1's log) — that's
expected physics, not a bug in the chain.

Alternatively, `submit_gensim_rawsim_hlt2024_chain.py --dry-run --filter <sample>` prints
the exact commands without executing anything (and warns instead of exiting if the CMSSW
release check fails, so you can still sanity-check the flags from elsewhere).

### Submit to CRAB

1) Modify the `DATASETS` list of ```scripts/submit_gensim_rawsim_hlt2024_chain.py``` to select the mass points that you want to launch

2) Correct the tag if needed, v3 should be the default 

3) Init from lxplus8 (important):

```sh
export SCRAM_ARCH=el8_amd64_gcc12
source /cvmfs/cms.cern.ch/cmsset_default.sh
cmsrel CMSSW_14_0_21
cd CMSSW_14_0_21/src
cmsenv

voms-proxy-init --voms cms

cd ../../
```

4) Launch first with --dry-run and then without it. Please make sure the ```--lfn-base``` points to your user area

```sh
python3 scripts/submit_gensim_rawsim_hlt2024_chain.py \
  --lfn-base /store/user/fernance/FinalScoutingProduction/GEN-SIM-RAW-HLT2024/ \
  --n-events 1000000 \
  --events-per-job 1000 \
  --site T2_US_UCSD \
  --dry-run          # drop this once the printed commands look right
```

`--filter`, the hardcoded `DATASETS` list, and the already-submitted skip check (via
`<work-area>/<name>/crab_<name>_GENSIM_RAWSIM_HLT2024/`) all work the same way as
`submit_gensim_rawsim_chain.py`. `--max-memory-mb` defaults to 3000 since the job now also runs the full HLT menu + L1 emulator on top of
GEN+SIM+DIGI+premix (that it's the maximum that can be set when launching a new task).

:warning: **This is going to fail!** because running all of that is going to make the memory explode. The solution is to increase the memory again when resubmitting (higher values are allowed in resubmit vs submit). This is why we have to run step 5)

5) Init a tmux terminal and let the resubmitting run!

```sh
tmux new -s crab_resubmit

# and inside
cd CMSSW_14_0_21/src
cmsenv
voms-proxy-init --voms cms
cd ../../

./scripts/crab_resubmit_loop.sh crab_gensim_rawsim_hlt2024 600
```

And then Control+b, then d: to exit the tmux
This will leave it running and resubmitting automatically.

## GEN-SIM -> RAWSIM -> HLT2025 in one job (no intermediate dataset)

`scripts/submit_gensim_rawsim_hlt2025_chain.py` extends the two-cfg/`scriptExe` design of
`submit_gensim_rawsim_hlt2024_chain.py` above to **three** cfgs, each run by its own `cmsRun`
call inside one CRAB job via `run_chain.sh`:

1. `step1_cfg.py` (`cmsDriver`, `LHE,GEN,SIM`) → GEN-SIM
2. `step2_cfg.py` (`cmsDriver`, `DIGI,DATAMIX,L1,DIGI2RAW`) → RAWSIM. No HLT here, and no
   event-content reduction — the full `PREMIXRAW` content is kept (the real FED raw data the
   HLT re-emulation step needs), and no events get filtered by an HLT path decision.
3. `step3_cfg.py` (`hltGetConfiguration`, not `cmsDriver`) → RAWSIM+HLT2025.

Unlike the 2024 chain (which folds HLT into step2 via cmsDriver's `--step ...,HLT:2024v14`),
the 2025 HLT step instead reuses the exact recipe already validated in this README ("HLT: reL1
+ HLT" → "1: 2025 setup") and `hlt_re-emulation/reHLT_mc_2025.py`: the real GRun-style menu
resolved via `hltGetConfiguration`, not a cmsDriver `HLT:<version>` keyword:

```sh
hltGetConfiguration adg:/cdaq/physics/Run2025/2e34/v1.3.4/HLT/V1 \
  --process HLT --globaltag 150X_mcRun3_2024_realistic_v3 --mc \
  --input file:<rawsim>.root --max-events -1 --output full --unprescale \
  --eras Run3_2025 --l1-emulator uGT --l1 L1Menu_Collisions2025_v1_3_0_xml \
  --paths ScoutingPFOutput,DST_PFScouting_*,Dataset_ScoutingPFRun3 \
  > step3_cfg.py
```

`step3_cfg.py`'s era (`Run3_2025`) only applies to the HLT re-emulation step — it's independent
of the `Run3_2024` era used for step1/step2 (GEN-SIM/RAWSIM), same as `submit_25hlt.py`'s
standalone `reHLT_mc_2025.py`.

**Different CMSSW release than everything else in this README**: the 2025 HLT menu resolves
against the HLT table shipped in a specific release, and that GT isn't available under
`CMSSW_17_0_0_pre2` — so all three steps here use `150X_mcRun3_2024_realistic_v3`, and the
whole thing runs from `CMSSW_15_0_15_patch1`:

```sh
export SCRAM_ARCH=el8_amd64_gcc12
source /cvmfs/cms.cern.ch/cmsset_default.sh
cmsrel CMSSW_15_0_15_patch1
cd CMSSW_15_0_15_patch1/src
cmsenv
```

The script checks `$CMSSW_VERSION` against this and refuses to submit (warns under
`--dry-run`) from the wrong release.

Per-job seeding works the same way as `submit_gensim_rawsim_chain.py` (see that section
above): `step1_cfg.py`'s `--customise_commands` derives a distinct seed per job from
`$CRAB_Id` at `cmsRun` runtime, since `scriptExe` bypasses CRAB's usual automatic seeding.

### Launch and test locally

Needs a valid grid proxy even for a local run — `--pileup_input` resolves the premix file
list via DAS at cfg-generation time, and an expired proxy silently produces an empty pileup
list instead of failing loudly (`voms-proxy-init --voms cms --valid 168:00` if
`voms-proxy-info --timeleft` comes back `0:00:00`).

```sh
cd $CMSSW_BASE/src   # CMSSW_15_0_15_patch1

FRAGMENT=GluGluHToDarkShowers-ScenarioA_Par-ctau-10-mA-1p67-mpi-5_cfi.py
cmsDriver.py Configuration/GenProduction/python/$FRAGMENT \
  --era Run3_2024 \
  --customise Configuration/DataProcessing/Utils.addMonitoring \
  --beamspot DBrealistic \
  --step LHE,GEN,SIM \
  --geometry DB:Extended \
  --conditions 150X_mcRun3_2024_realistic_v3 \
  --customise_commands "import os;_seed=int(os.environ.get('CRAB_Id','1'));process.RandomNumberGeneratorService.externalLHEProducer.initialSeed=(_seed*4+1)%900000000+1;process.RandomNumberGeneratorService.generator.initialSeed=(_seed*4+2)%900000000+1;process.RandomNumberGeneratorService.VtxSmeared.initialSeed=(_seed*4+3)%900000000+1;process.RandomNumberGeneratorService.g4SimHits.initialSeed=(_seed*4+4)%900000000+1" \
  --datatier GEN-SIM \
  --eventcontent RAWSIM \
  --python_filename step1_cfg.py \
  --fileout file:rawsim_hlt2025.root \
  --number 10 --number_out 10 \
  --no_exec --mc

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
  --python_filename step2_cfg.py \
  --fileout file:step2_rawsim.root \
  --filein file:step1_gensim.root \
  --number -1 --number_out -1 \
  --pileup_input dbs:/Neutrino_E-10_gun/RunIIISummer24PrePremix-Premixlib2024_140X_mcRun3_2024_realistic_v26-v1/PREMIX \
  --no_exec --mc

hltGetConfiguration adg:/cdaq/physics/Run2025/2e34/v1.3.4/HLT/V1 \
  --process HLT \
  --globaltag 150X_mcRun3_2024_realistic_v3 \
  --mc \
  --input file:step2_rawsim.root \
  --max-events -1 \
  --output full \
  --unprescale \
  --eras Run3_2025 \
  --l1-emulator uGT --l1 L1Menu_Collisions2025_v1_3_0_xml \
  --paths ScoutingPFOutput,DST_PFScouting_*,Dataset_ScoutingPFRun3 \
  > step3_cfg.py

echo 'process.source.bypassVersionCheck = cms.untracked.bool(True)' >> step3_cfg.py
echo 'process.source.inputCommands = cms.untracked.vstring("keep *","drop TH2PolyMEtoEDM_*_*_*")' >> step3_cfg.py
echo 'process.options.wantSummary = False' >> step3_cfg.py
echo 'process.hltOutputFull.fileName = cms.untracked.string("rawsim_hlt2025.root")' >> step3_cfg.py

cat >> step3_cfg.py << 'EOF'

process.hltOutputFull.outputCommands = cms.untracked.vstring(
    "drop *",
    "keep *_*Packer*_*_*",
    "keep FEDRawDataCollection_hltFEDSelectorL1_*_*",
    "keep *_gtStage2Digis_*_*",
    "keep edmTriggerResults_*_*_*",
    "keep *_addPileupInfo_*_*",
    "keep *_genParticles_*_*",
)
EOF

# run_chain.sh isn't a static file — submit_gensim_rawsim_hlt2025_chain.py generates it per
# work-area (see generate_run_chain()) — so for a local test just write the same steps
# (this is exactly what CRAB's scriptExe runs on the grid):
cat > run_chain.sh << 'EOF'
#!/bin/bash
set -e

# Step 1: GEN-SIM -> rawsim_hlt2025.root (real bytes, wrong filename -- fixed up below)
cmsRun -j FrameworkJobReport1.xml step1_cfg.py
mv rawsim_hlt2025.root step1_gensim.root

# Step 2: RAWSIM (no HLT, full event content), reading step1_gensim.root -> step2_rawsim.root
cmsRun -j FrameworkJobReport2.xml step2_cfg.py

# Step 3: HLT2025 re-emulation, reading step2_rawsim.root -> final output (rawsim_hlt2025.root).
# This must be the LAST cmsRun call and must write FrameworkJobReport.xml —
# CRAB reads that report to figure out what to stage out/publish.
cmsRun -j FrameworkJobReport.xml step3_cfg.py
EOF
chmod +x run_chain.sh && ./run_chain.sh
```

If it completes, inspect the result:

```sh
edmFileUtil rawsim_hlt2025.root          # event count, file size
edmDumpEventContent rawsim_hlt2025.root  # collections that survived the outputCommands above
```

A generator-level matching filter in the fragment can make `step1_gensim.root` end up with
fewer events than `--number` asked for (check `Filter efficiency` in step1's log) — that's
expected physics, not a bug in the chain.

Alternatively, `submit_gensim_rawsim_hlt2025_chain.py --dry-run --filter <sample>` prints
the exact commands without executing anything (and warns instead of exiting if the CMSSW
release check fails, so you can still sanity-check the flags from elsewhere).

### Submit to CRAB

```sh
python3 scripts/submit_gensim_rawsim_hlt2025_chain.py \
  --lfn-base /store/user/fernance/FinalScoutingProduction/GEN-SIM-RAW-HLT2025/ \
  --n-events 1000000 \
  --events-per-job 1000 \
  --site T2_US_UCSD \
  --dry-run          # drop this once the printed commands look right
```

`--filter`, the hardcoded `DATASETS` list, and the already-submitted skip check (via
`<work-area>/<name>/crab_<name>_GENSIM_RAWSIM_HLT2025/`) all work the same way as
`submit_gensim_rawsim_chain.py`. `JobType.inputFiles` now ships all three cfgs
(`step1_cfg.py`, `step2_cfg.py`, `step3_cfg.py`) and `JobType.outputFiles` only lists the
final `rawsim_hlt2025.root`. `--max-memory-mb` defaults to 3000 since the job now runs
GEN+SIM+DIGI+premix, then the full HLT menu + L1 emulator, sequentially (that it's the
maximum that can be set when launching a new task).

:warning: **This is going to fail!** because running all of that is going to make the memory explode. The solution is to increase the memory again when resubmitting (higher values are allowed in resubmit vs submit).

## Automatic CRAB resubmit

`scripts/crab_resubmit_loop.sh` walks every `crab_*/` task directory inside a CRAB work area
(e.g. `crab_gensim_rawsim_hlt2024/`) and runs `crab resubmit` on each one, once per hour,
forever — meant to be left running in a `tmux` session so it survives disconnecting from
lxplus. A `crab resubmit` failure (task already `COMPLETE`, nothing to resubmit, etc.) is
logged and does not stop the loop. Progress is logged both to the terminal and to
`<work-area>/resubmit_loop.log`.

```sh
source /cvmfs/cms.cern.ch/crab3/crab.sh        # crab must be in PATH
voms-proxy-init --voms cms --valid 192:00      # long-lived proxy — see warning below

tmux new -s crab_resubmit
./scripts/crab_resubmit_loop.sh [work_area] [interval_seconds]
# Ctrl-b d to detach, then disconnect freely — reattach later with:
#   tmux attach -t crab_resubmit
```

Defaults: `work_area` = `crab_gensim_rawsim_hlt2024/` (relative to the script), `interval` =
3600s (1 hour). To stop it, reattach with `tmux attach -t crab_resubmit` and hit `Ctrl-C`.

:warning: a voms proxy lasts at most ~192h even when requested with `--valid 192:00`. If the
loop needs to run longer than that, the script only logs a warning
(`no valid voms proxy`) once it expires — it does **not** renew it — so you'll need to
reconnect and run `voms-proxy-init` again yourself.

## HLT: reL1 + HLT

Instructions [here](https://twiki.cern.ch/twiki/bin/view/CMSPublic/SWGuideGlobalHLT#Legacy_HLT_menus_and_older_relea)

Inputs should be the ones from the RAWSIM step.

:warning: Files are already available in hlt_re-emulation/ folder so it it enough with copying, but instructions to produce it are here.

### 1: 2025 setup

Should be run on CMSSW_15_0_15_patch1:

```sh
export SCRAM_ARCH=el8_amd64_gcc12
source /cvmfs/cms.cern.ch/cmsset_default.sh
cmsrel CMSSW_15_0_15_patch1
cd CMSSW_15_0_15_patch1/src
cmsenv
```

:warning: The file is already available in hlt_re-emulation/ folder so it it enough with copying, but instructions to produce it are here.

Recipe for emulation is this one:

```sh
hltGetConfiguration adg:/cdaq/physics/Run2025/2e34/v1.3.4/HLT/V1 \
--process HLT \
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

cat >> reHLT_mc_2025.py << 'EOF'

process.hltOutputFull.outputCommands = cms.untracked.vstring(
    "drop *",
    "keep *_*Packer*_*_*",
    "keep FEDRawDataCollection_hltFEDSelectorL1_*_*",
    "keep *_gtStage2Digis_*_*",
    "keep edmTriggerResults_*_*_*",
    "keep *_addPileupInfo_*_*",
    "keep *_genParticles_*_*",
)
EOF
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
hltGetConfiguration adg:/cdaq/physics/Run2026/2e34/v1.3.0/HLT/V6 \
--process HLT \
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

cat >> reHLT_mc_2026.py << 'EOF'

process.hltOutputFull.outputCommands = cms.untracked.vstring(
    "drop *",
    "keep *_*Packer*_*_*",
    "keep FEDRawDataCollection_hltFEDSelectorL1_*_*",
    "keep *_gtStage2Digis_*_*",
    "keep edmTriggerResults_*_*_*",
    "keep *_addPileupInfo_*_*",
    "keep *_genParticles_*_*",
)
EOF
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

For producing GEN-SIM through RAWSIM+HLT2024 without a separate CRAB task per step, see
"GEN-SIM -> RAWSIM+HLT2024 in one job (no intermediate dataset)" above — **not** a single
chained `cmsDriver` step (that doesn't work for this), but two separate cfgs run back to
back by `scripts/run_chain.sh`.


# Known problems

Problem producing a sample in 17X and reHLT in 14X: format problems

Problems running generator with el8_amd64_gcc13: Multiple memory problems, decided to follow the same approach as 2024 and run it in one go with HLT:2025v13