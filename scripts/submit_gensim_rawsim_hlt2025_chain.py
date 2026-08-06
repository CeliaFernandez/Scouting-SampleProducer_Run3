#!/usr/bin/env python3
"""
GEN-SIM -> RAWSIM -> HLT2025 launcher for DQCD Run3 2025 production, chained
in a single CRAB job (no intermediate GEN-SIM or RAWSIM dataset staged out or
published).

Three separate cfgs, each run by its own cmsRun call inside ONE CRAB job via
JobType.pluginName='PrivateMC' + JobType.scriptExe=run_chain.sh:

  1. step1_cfg.py (cmsDriver, LHE,GEN,SIM)                 -> GEN-SIM
  2. step2_cfg.py (cmsDriver, DIGI,DATAMIX,L1,DIGI2RAW)     -> RAWSIM
     No HLT and no event-content reduction here -- the full PREMIXRAW content
     is kept (HLT re-emulation downstream needs the real FED raw data), and
     no events are filtered/dropped by an HLT path decision.
  3. step3_cfg.py (hltGetConfiguration, real 2025 HLT menu) -> RAWSIM+HLT2025

Unlike submit_gensim_rawsim_hlt2024_chain.py (which folds HLT into step2 via
cmsDriver's `--step ...,HLT:2024v14`), 2025 HLT re-emulation instead reuses
the exact recipe already validated in README.md ("HLT: reL1 + HLT" -> "1: 2025
setup") and hlt_re-emulation/reHLT_mc_2025.py: the real GRun-style menu
resolved via `hltGetConfiguration`, not a cmsDriver HLT:<version> keyword.

  hltGetConfiguration adg:/cdaq/physics/Run2025/2e34/v1.3.4/HLT/V1 \\
    --process HLT --globaltag 150X_mcRun3_2024_realistic_v3 --mc \\
    --input file:<rawsim>.root --max-events -1 --output full --unprescale \\
    --eras Run3_2025 --l1-emulator uGT --l1 L1Menu_Collisions2025_v1_3_0_xml \\
    --paths ScoutingPFOutput,DST_PFScouting_*,Dataset_ScoutingPFRun3 \\
    > step3_cfg.py

step3_cfg.py's era (Run3_2025) only affects the HLT re-emulation step -- it is
independent of the Run3_2024 era used for step1/step2 (GEN-SIM/RAWSIM), same
as submit_25hlt.py's standalone reHLT_mc_2025.py.

IMPORTANT: all three steps run under CMSSW_15_0_15_patch1 with GT
150X_mcRun3_2024_realistic_v3 -- the release/GT combination the 2025 HLT menu
resolves against (see README.md, section "1: 2025 setup"):

  export SCRAM_ARCH=el8_amd64_gcc12
  source /cvmfs/cms.cern.ch/cmsset_default.sh
  cmsrel CMSSW_15_0_15_patch1
  cd CMSSW_15_0_15_patch1/src
  cmsenv

Assumes:
  - cmsenv has been sourced inside the CMSSW_15_0_15_patch1 area above
  - The complete/ fragment directory has been installed as
    Configuration/GenProduction/python/ (via scram b or symlink)
  - CRAB env is set up (source /cvmfs/cms.cern.ch/crab3/crab.sh)
  - hltGetConfiguration is on PATH (ships with CMSSW, available after cmsenv)

Usage:
  python3 submit_gensim_rawsim_hlt2025_chain.py [options]
  python3 submit_gensim_rawsim_hlt2025_chain.py --dry-run
  python3 submit_gensim_rawsim_hlt2025_chain.py --filter ScenarioA
  python3 submit_gensim_rawsim_hlt2025_chain.py --filter mpi-1p2
"""

# CMSSW_15_0_15_patch1 ships Python 3.9, which doesn't evaluate `str | None`-style
# annotations at runtime (that needs 3.10+); this defers evaluation so they
# work as plain strings instead of raising at import time.
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults — override via CLI flags
# ---------------------------------------------------------------------------
FRAGMENTS_DIR = Path(__file__).resolve().parent.parent / "2024-fragments" / "complete"
REQUIRED_CMSSW_RELEASE = "CMSSW_15_0_15_patch1"

# Standard 2024 premix library used for the DATAMIX step (see rawsim_cfg.py)
PILEUP_INPUT = "dbs:/Neutrino_E-10_gun/RunIIISummer24PrePremix-Premixlib2024_140X_mcRun3_2024_realistic_v26-v1/PREMIX"

# hltGetConfiguration menu/GT/L1 recipe for the 2025 HLT re-emulation step
# (see README.md "HLT: reL1 + HLT" -> "1: 2025 setup" and
# hlt_re-emulation/reHLT_mc_2025.py, which was generated with this same
# recipe against a standalone RAWSIM input rather than a locally-chained one).
HLT_MENU = "adg:/cdaq/physics/Run2025/2e34/v1.3.4/HLT/V1"
HLT_GLOBALTAG = "150X_mcRun3_2024_realistic_v3"
HLT_ERA = "Run3_2025"
HLT_L1_MENU = "L1Menu_Collisions2025_v1_3_0_xml"
HLT_PATHS = "ScoutingPFOutput,DST_PFScouting_*,Dataset_ScoutingPFRun3"

# Local scratch filenames run_chain.sh renames each step's real output to
# before the next step reads it back. Neither is staged out itself.
STEP1_OUTPUT = "step1_gensim.root"
STEP2_OUTPUT = "step2_rawsim.root"

# Final output filename, staged out by CRAB (listed in CRAB_TEMPLATE's
# outputFiles). ALSO used as step1_cfg.py's own --fileout (see
# STEP1_CMSDRIVER_TEMPLATE below) even though step1 doesn't produce this
# content -- CRABClient's Analysis.run() builds the task's "EDM output to
# publish" list purely from the PoolOutputModule(s) it finds scheduled in
# JobType.psetName, matched by filename against the real FrameworkJobReport
# the job produces at runtime. psetName has to stay step1_cfg.py (PrivateMC
# forbids a PoolSource-based pset, which step2_cfg.py/step3_cfg.py have via
# --filein/process.source), and a pset with >1 scheduled output module makes
# CRAB refuse the submission outright ("can't publish more than one dataset
# per task") -- so step1_cfg.py must declare exactly one output module, and
# it must be named like step3's real output for CRAB to publish the right
# (RAWSIM+HLT2025, not GEN-SIM) file. run_chain.sh's mv is what reconciles
# this with step1 still needing to write its real GEN-SIM bytes somewhere
# step2 can read from -- step3_cfg.py's hltOutputFull.fileName is set to this
# same value directly (see STEP3_HLTGETCONFIG_TEMPLATE), so step3 doesn't
# need an equivalent rename.
STEP3_OUTPUT = "rawsim_hlt2025.root"

# Reseeds the PSets under RandomNumberGeneratorService that the LHE,GEN,SIM
# step actually uses (externalLHEProducer, generator, VtxSmeared, g4SimHits)
# from $CRAB_Id -- the per-job number CRAB always exports into the job's
# environment, scriptExe or not. Evaluated at cmsRun runtime on the worker
# node (not at cfg-generation time), so every job of a sample runs the
# identical step1_cfg.py but each still gets distinct seeds. Without this,
# every job would use the same hardcoded seed and generate near-identical,
# correlated events -- CRAB's automatic per-job seed patching only kicks in
# when it runs psetName directly, which scriptExe bypasses (see
# submit_gensim.py for that direct-execution case).
#
# Deliberately NOT a loop over parameterNames_(): cmsDriver executes
# --customise_commands via exec(re.sub(...)) on the raw string, and (a) a
# list/generator comprehension loses access to the substituted "self" in
# that exec() (NameError: self is not defined -- comprehensions get their
# own scope that doesn't see exec()'s locals), and (b) a real for-loop needs
# literal newlines, which corrupt cmsDriver's auto-generated "# with command
# line options: ..." header comment (it doesn't expect embedded newlines in
# an argument value). Both were tested and failed; semicolon-joined single
# statements are the only form that survives cmsDriver's own machinery.
SEED_CUSTOMISE = (
    "import os;"
    '_seed=int(os.environ.get("CRAB_Id","1"));'
    "process.RandomNumberGeneratorService.externalLHEProducer.initialSeed=(_seed*4+1)%900000000+1;"
    "process.RandomNumberGeneratorService.generator.initialSeed=(_seed*4+2)%900000000+1;"
    "process.RandomNumberGeneratorService.VtxSmeared.initialSeed=(_seed*4+3)%900000000+1;"
    "process.RandomNumberGeneratorService.g4SimHits.initialSeed=(_seed*4+4)%900000000+1"
)

STEP1_CMSDRIVER_TEMPLATE = (
    "cmsDriver.py Configuration/GenProduction/python/{fragment}"
    " --era Run3_2024"
    " --customise Configuration/DataProcessing/Utils.addMonitoring"
    " --beamspot DBrealistic"
    " --step LHE,GEN,SIM"
    " --geometry DB:Extended"
    " --conditions 150X_mcRun3_2024_realistic_v3"
    f" --customise_commands '{SEED_CUSTOMISE}'"
    " --datatier GEN-SIM"
    " --eventcontent RAWSIM"
    " --python_filename {cfg}"
    # Deliberately STEP3_OUTPUT, not STEP1_OUTPUT -- see the comment on
    # STEP3_OUTPUT above. run_chain.sh renames the real file this produces
    # to STEP1_OUTPUT before step2 runs.
    f" --fileout file:{STEP3_OUTPUT}"
    # Baked statically per job (not the sample total) — under scriptExe, CRAB
    # never gets to patch process.maxEvents.input the way it does when it
    # runs psetName directly, so this has to already be Data.unitsPerJob.
    " --number {events_per_job} --number_out {events_per_job}"
    " --no_exec --mc"
)

STEP2_CMSDRIVER_TEMPLATE = (
    "cmsDriver.py"
    " --era Run3_2024"
    " --customise Configuration/DataProcessing/Utils.addMonitoring"
    " --procModifiers premix_stage2"
    " --datamix PreMix"
    " --step DIGI,DATAMIX,L1,DIGI2RAW"
    " --geometry DB:Extended"
    " --conditions 150X_mcRun3_2024_realistic_v3"
    " --datatier GEN-SIM-RAW"
    " --eventcontent PREMIXRAW"
    " --python_filename {cfg}"
    f" --fileout file:{STEP2_OUTPUT}"
    f" --filein file:{STEP1_OUTPUT}"
    " --number -1 --number_out -1"
    " --pileup_input {pileup_input}"
    " --no_exec --mc"
)

# hltGetConfiguration, not cmsDriver -- generates step3_cfg.py by running the
# real 2025 HLT menu tool and appending a few fixups on top, exactly as in
# README.md's "1: 2025 setup" recipe. Shared by every sample (only reads
# step2's local scratch RAWSIM output), so it's generated once per work-area
# just like step2_cfg.py.
STEP3_HLTGETCONFIG_TEMPLATE = """\
hltGetConfiguration {menu} \\
  --process HLT \\
  --globaltag {globaltag} \\
  --mc \\
  --input file:{step2_output} \\
  --max-events -1 \\
  --output full \\
  --unprescale \\
  --eras {era} \\
  --l1-emulator uGT --l1 {l1_menu} \\
  --paths {paths} \\
  > {cfg}

echo 'process.source.bypassVersionCheck = cms.untracked.bool(True)' >> {cfg}
echo 'process.source.inputCommands = cms.untracked.vstring("keep *","drop TH2PolyMEtoEDM_*_*_*")' >> {cfg}
echo 'process.options.wantSummary = False' >> {cfg}
echo 'process.hltOutputFull.fileName = cms.untracked.string("{step3_output}")' >> {cfg}

cat >> {cfg} << 'PYEOF'

process.hltOutputFull.outputCommands = cms.untracked.vstring(
    "drop *",
    "keep *_*Packer*_*_*",
    "keep FEDRawDataCollection_hltFEDSelectorL1_*_*",
    "keep *_gtStage2Digis_*_*",
    "keep edmTriggerResults_*_*_*",
    "keep *_addPileupInfo_*_*",
    "keep *_genParticles_*_*",
)
PYEOF
"""

CRAB_TEMPLATE = """\
from CRABClient.UserUtilities import config
config = config()

config.General.requestName = '{name}_GENSIM_RAWSIM_HLT2025'
config.General.workArea = '{work_area}'
config.General.transferOutputs = True
config.General.transferLogs = True

config.JobType.pluginName = 'PrivateMC'
config.JobType.psetName = '{step1_cfg}'
config.JobType.scriptExe = '{run_chain}'
config.JobType.inputFiles = ['{step1_cfg}', '{step2_cfg}', '{step3_cfg}']
config.JobType.outputFiles = ['{step3_output}']
config.JobType.numCores = 1
config.JobType.maxMemoryMB = {max_memory_mb}

config.Data.outputPrimaryDataset = '{name}'
config.Data.splitting = 'EventBased'
config.Data.unitsPerJob = {events_per_job}
config.Data.totalUnits = {total_events}
config.Data.outLFNDirBase = '{lfn_base}'
config.Data.publication = True
config.Data.outputDatasetTag = '{tag}'

config.Site.storageSite = '{site}'
config.Site.blacklist = ['T2_US_MIT']

config.section_("Debug")
config.Debug.extraJDL = ['My.CMS_ALLOW_OVERFLOW=False']
"""

# scriptExe run by the CRAB job. Generated per work-area (not a static file)
# because step1_cfg.py's own --fileout is deliberately STEP3_OUTPUT, not a
# scratch name -- see the STEP3_OUTPUT comment above for why (CRABClient only
# recognizes a task's EDM output to publish from the PoolOutputModule(s)
# scheduled in JobType.psetName, which has to stay step1_cfg.py, and matches
# it to the real file the job produces at runtime by name). So step1's real
# GEN-SIM bytes land in STEP3_OUTPUT and have to be renamed to the scratch
# filename (STEP1_OUTPUT) before step2 runs -- otherwise step2 would need to
# read and overwrite the same filename in one cmsRun process, which corrupts
# the input mid-read. step2's own output (STEP2_OUTPUT) needs no such trick
# since it isn't the last step -- step3 reads it directly and writes the real
# STEP3_OUTPUT itself (via the hltOutputFull.fileName override baked into
# step3_cfg.py), so no rename is needed after step3 either.
RUN_CHAIN_TEMPLATE = """\
#!/bin/bash
# Generated by submit_gensim_rawsim_hlt2025_chain.py -- do not edit by hand.
set -e

# Step 1: GEN-SIM -> {step3_output} (real bytes, wrong filename -- fixed up below)
cmsRun -j FrameworkJobReport1.xml step1_cfg.py
mv {step3_output} {step1_output}

# Step 2: RAWSIM (no HLT, full event content), reading {step1_output} -> {step2_output}
cmsRun -j FrameworkJobReport2.xml step2_cfg.py

# Step 3: HLT2025 re-emulation, reading {step2_output} -> final output ({step3_output}).
# This must be the LAST cmsRun call and must write FrameworkJobReport.xml —
# CRAB reads that report to figure out what to stage out/publish.
cmsRun -j FrameworkJobReport.xml step3_cfg.py
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check_cmssw_release(dry_run: bool) -> None:
    """The 2025 HLT menu (HLT_MENU) and 150X_mcRun3_2024_realistic_v3 resolve
    against the HLT table shipped in REQUIRED_CMSSW_RELEASE; running from
    another release can silently pick up a different (incompatible) menu/GT."""
    version = os.environ.get("CMSSW_VERSION")
    if version == REQUIRED_CMSSW_RELEASE:
        return
    msg = (
        f"CMSSW_VERSION is '{version}', expected '{REQUIRED_CMSSW_RELEASE}'.\n"
        f"       cmsenv from a {REQUIRED_CMSSW_RELEASE}/src area before submitting."
    )
    if dry_run:
        print(f"WARNING: {msg}")
    else:
        sys.exit(f"ERROR: {msg}")


def discover_fragments(fragments_dir: Path, pattern: str | None) -> list[Path]:
    fragments = sorted(fragments_dir.glob("*_cfi.py"))
    if pattern:
        fragments = [f for f in fragments if pattern in f.name]
    return fragments


def sample_name(fragment: Path) -> str:
    """Strip _cfi suffix to get the canonical sample name."""
    return fragment.stem.removesuffix("_cfi")


def is_already_submitted(work_area: Path, name: str) -> bool:
    """CRAB creates crab_<name>_GENSIM_RAWSIM_HLT2025/ inside workArea after a successful submit."""
    return (work_area / name / f"crab_{name}_GENSIM_RAWSIM_HLT2025").exists()


def run(cmd: str, cwd: Path, dry_run: bool) -> None:
    print(f"    $ {cmd}")
    if dry_run:
        return
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(f"Command exited with code {result.returncode}")


def generate_step1_cfg(fragment: Path, job_dir: Path, events_per_job: int, dry_run: bool) -> Path:
    cfg = job_dir / "step1_cfg.py"
    cmd = STEP1_CMSDRIVER_TEMPLATE.format(
        fragment=fragment.name, cfg=cfg.name, events_per_job=events_per_job,
    )
    run(cmd, cwd=job_dir, dry_run=dry_run)
    return cfg


def generate_step2_cfg(work_area: Path, pileup_input: str, dry_run: bool) -> Path:
    """Generate the single DIGI/RAW cfg shared by every sample (mirrors
    submit_rawsim.py: this step doesn't read anything sample-specific — it
    only reads step1's local scratch output — so one cfg covers every sample
    instead of regenerating an identical one per submission)."""
    cfg = work_area / "step2_cfg.py"
    cmd = STEP2_CMSDRIVER_TEMPLATE.format(cfg=cfg.name, pileup_input=pileup_input)
    run(cmd, cwd=work_area, dry_run=dry_run)
    return cfg


def generate_step3_cfg(work_area: Path, dry_run: bool) -> Path:
    """Generate the shared HLT2025 re-emulation cfg via hltGetConfiguration
    (not cmsDriver) -- reused for every sample, same reasoning as
    generate_step2_cfg above."""
    cfg = work_area / "step3_cfg.py"
    cmd = STEP3_HLTGETCONFIG_TEMPLATE.format(
        menu=HLT_MENU, globaltag=HLT_GLOBALTAG, era=HLT_ERA, l1_menu=HLT_L1_MENU,
        paths=HLT_PATHS, cfg=cfg.name, step2_output=STEP2_OUTPUT, step3_output=STEP3_OUTPUT,
    )
    run(cmd, cwd=work_area, dry_run=dry_run)
    return cfg


def generate_run_chain(work_area: Path, dry_run: bool) -> Path:
    """Generate the scriptExe shared by every sample (mirrors generate_step2_cfg:
    STEP1_OUTPUT/STEP2_OUTPUT/STEP3_OUTPUT are constants, not per-sample, so one
    file covers every sample in this work area)."""
    run_chain = work_area / "run_chain.sh"
    print(f"    $ write {run_chain}")
    content = RUN_CHAIN_TEMPLATE.format(
        step1_output=STEP1_OUTPUT, step2_output=STEP2_OUTPUT, step3_output=STEP3_OUTPUT,
    )
    if not dry_run:
        run_chain.write_text(content)
        run_chain.chmod(0o755)
    return run_chain


def write_crab_config(name: str, step1_cfg: Path, step2_cfg: Path, step3_cfg: Path,
                      run_chain: Path, job_dir: Path, work_area: Path, events_per_job: int,
                      total_events: int, lfn_base: str, tag: str, site: str,
                      max_memory_mb: int, dry_run: bool) -> Path:
    crab_cfg = job_dir / f"crab_{name}_gensim_rawsim_hlt2025.py"
    print(f"    $ write {crab_cfg}")
    content = CRAB_TEMPLATE.format(
        name=name,
        work_area=str(work_area),
        step1_cfg=str(step1_cfg),
        step2_cfg=str(step2_cfg),
        step3_cfg=str(step3_cfg),
        run_chain=str(run_chain),
        step3_output=STEP3_OUTPUT,
        events_per_job=events_per_job,
        total_events=total_events,
        lfn_base=lfn_base,
        tag=tag,
        site=site,
        max_memory_mb=max_memory_mb,
    )
    print(content)
    if not dry_run:
        crab_cfg.write_text(content)
    return crab_cfg


def crab_submit(name: str, crab_cfg: Path, job_dir: Path, dry_run: bool) -> None:
    run(f"crab submit {crab_cfg}", cwd=job_dir, dry_run=dry_run)


def install_fragments(fragments_dir: Path, cmssw_base: Path, dry_run: bool) -> None:
    """Symlink all complete fragments into CMSSW and rebuild."""
    target_dir = cmssw_base / "src" / "Configuration" / "GenProduction" / "python"
    print(f"Installing fragments into {target_dir}")
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    for fragment in sorted(fragments_dir.glob("*_cfi.py")):
        link = target_dir / fragment.name
        if link.exists() or link.is_symlink():
            link.unlink()
        print(f"    -> {fragment.name}")
        if not dry_run:
            link.symlink_to(fragment.resolve())

    run("scram b", cwd=cmssw_base / "src", dry_run=dry_run)
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Submit combined GEN-SIM->RAWSIM->HLT2025 CRAB jobs (single task, no intermediate dataset) for DQCD Run3 2025 production.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--fragments-dir", type=Path, default=FRAGMENTS_DIR,
        help="Directory containing the complete (ExternalLHEProducer+hadronizer) fragments",
    )
    p.add_argument(
        "--filter", type=str, default=None, metavar="STR",
        help="Only process fragments whose filename contains STR (e.g. 'ScenarioA', 'mpi-1p2')",
    )
    p.add_argument(
        "--work-area", type=str, default="crab_gensim_rawsim_hlt2025",
        help="CRAB workArea directory (created if absent)",
    )
    p.add_argument(
        "--n-events", type=int, default=1000000,
        help="Total events per sample",
    )
    p.add_argument(
        "--events-per-job", type=int, default=1000,
        help="Events per CRAB job — baked directly into step1_cfg.py's --number (see run_chain.sh)",
    )
    p.add_argument(
        "--pileup-input", type=str, default=PILEUP_INPUT,
        help="Premix library dataset passed to cmsDriver's --pileup_input for the DIGI/RAW step",
    )
    p.add_argument(
        "--lfn-base", type=str, default="/store/user/fernance/FinalScoutingProduction/GEN-SIM-RAW-HLT2025/",
        help="LFN output base path on the storage element",
    )
    p.add_argument(
        "--site", type=str, default="T2_US_UCSD",
        help="CMS storage site for output",
    )
    p.add_argument(
        "--tag", type=str, default="hlt_2025_v3",
        help="CRAB outputDatasetTag",
    )
    p.add_argument(
        "--max-memory-mb", type=int, default=3000,
        help="JobType.maxMemoryMB — the job runs GEN+SIM+DIGI+premix, then the full HLT menu+L1 emulator, sequentially",
    )
    p.add_argument(
        "--cmssw-base", type=Path,
        default=Path(os.environ.get("CMSSW_BASE", "")),
        help="Path to the CMSSW area (defaults to $CMSSW_BASE)",
    )
    p.add_argument(
        "--no-install", action="store_true",
        help="Skip fragment installation into CMSSW (use if already installed)",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Print all commands without executing anything",
    )
    return p.parse_args()


def main():
    # Hardcoded (scenario, mpi, mA, ctau) mass points/lifetimes to produce.
    # Leave empty to process every fragment discovered in --fragments-dir
    # (optionally narrowed by --filter).
    DATASETS = [
        #("A",  "5", "1p67", "10"),
        ("A",  "5", "1p67", "0p1"),
        ("A",  "5", "1p67", "0p25"),
        ("A",  "5", "1p67", "0p6"),
        ("A",  "5", "1p67", "1p0"),
        ("A",  "5", "1p67", "2p5"),
        ("A",  "5", "1p67", "6p0"),
        ("A",  "5", "1p67", "10"),
        ("A",  "5", "1p67", "25"),
        ("A",  "5", "1p67", "60"),
        ("A",  "5", "1p67", "100"),
        ("A",  "5", "1p67", "1000")
        # ("B1", "2",   "0p67", "10"),
    ]

    args = parse_args()

    check_cmssw_release(args.dry_run)

    fragments = discover_fragments(args.fragments_dir, args.filter)
    if DATASETS:
        wanted = {
            f"GluGluHToDarkShowers-Scenario{scenario}_Par-ctau-{ctau}-mA-{mA}-mpi-{mpi}"
            for scenario, mpi, mA, ctau in DATASETS
        }
        fragments = [f for f in fragments if sample_name(f) in wanted]
    if not fragments:
        sys.exit(
            f"ERROR: No fragments found in {args.fragments_dir}"
            + (f" matching '{args.filter}'" if args.filter else "")
        )

    if not args.no_install:
        if not args.cmssw_base or not args.cmssw_base.is_dir():
            sys.exit(
                "ERROR: CMSSW_BASE is not set or is not a valid directory.\n"
                "       Source cmsenv or pass --cmssw-base /path/to/CMSSW_X_Y_Z"
            )
        install_fragments(args.fragments_dir, args.cmssw_base, args.dry_run)

    work_area = Path(args.work_area).resolve()
    if not args.dry_run:
        work_area.mkdir(parents=True, exist_ok=True)

    label = "[DRY-RUN] " if args.dry_run else ""
    print(f"{label}Processing {len(fragments)} fragment(s)  |  "
          f"{args.n_events} events/sample  |  {args.events_per_job} events/job\n")

    print("Generating shared DIGI/RAW cfg, no HLT (reused for every sample):")
    step2_cfg = generate_step2_cfg(work_area, args.pileup_input, args.dry_run)
    print()

    print("Generating shared HLT2025 re-emulation cfg via hltGetConfiguration (reused for every sample):")
    step3_cfg = generate_step3_cfg(work_area, args.dry_run)
    print()

    print("Generating shared scriptExe (reused for every sample):")
    run_chain = generate_run_chain(work_area, args.dry_run)
    print()

    n_ok = n_skip = n_fail = 0

    for fragment in fragments:
        name = sample_name(fragment)

        if is_already_submitted(work_area, name):
            print(f"  [SKIP]   {name}")
            n_skip += 1
            continue

        print(f"  [SUBMIT] {name}")
        job_dir = work_area / name
        if not args.dry_run:
            job_dir.mkdir(parents=True, exist_ok=True)

        try:
            step1_cfg = generate_step1_cfg(fragment, job_dir, args.events_per_job, args.dry_run)
            crab_cfg = write_crab_config(
                name=name,
                step1_cfg=step1_cfg,
                step2_cfg=step2_cfg,
                step3_cfg=step3_cfg,
                run_chain=run_chain,
                job_dir=job_dir,
                work_area=work_area,
                events_per_job=args.events_per_job,
                total_events=args.n_events,
                lfn_base=args.lfn_base,
                tag=args.tag,
                site=args.site,
                max_memory_mb=args.max_memory_mb,
                dry_run=args.dry_run,
            )
            crab_submit(name, crab_cfg, job_dir, args.dry_run)
            n_ok += 1
        except Exception as exc:
            print(f"    ERROR: {exc}", file=sys.stderr)
            n_fail += 1

    print(f"\nDone — submitted: {n_ok}  skipped: {n_skip}  failed: {n_fail}")
    if n_fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
