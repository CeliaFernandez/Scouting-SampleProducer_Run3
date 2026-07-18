#!/usr/bin/env python3
"""
GEN-SIM launcher for DQCD Run3 2024 production.

Discovers complete fragments in 2024-fragments/complete/, generates a CMSSW
cfg per sample via cmsDriver, writes a CRAB config, and submits.

Assumes:
  - cmsenv has been sourced inside a CMSSW_X_Y_Z area
  - The complete/ fragment directory has been installed as
    Configuration/GenProduction/python/ (via scram b or symlink)
  - CRAB env is set up (source /cvmfs/cms.cern.ch/crab3/crab.sh)

Usage:
  python3 submit_gensim.py [options]
  python3 submit_gensim.py --dry-run
  python3 submit_gensim.py --filter ScenarioA
  python3 submit_gensim.py --filter mpi-1p2
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults — override via CLI flags
# ---------------------------------------------------------------------------
FRAGMENTS_DIR = Path(__file__).resolve().parent.parent / "2024-fragments" / "complete"

CMSDRIVER_TEMPLATE = (
    "cmsDriver.py Configuration/GenProduction/python/{fragment}"
    " --era Run3_2024"
    " --customise Configuration/DataProcessing/Utils.addMonitoring"
    " --beamspot DBrealistic"
    " --step LHE,GEN,SIM"
    " --geometry DB:Extended"
    " --conditions 140X_mcRun3_2024_realistic_v26"
    r""" --customise_commands 'process.RandomNumberGeneratorService.externalLHEProducer.initialSeed="int(${SEED})"'"""
    " --datatier GEN-SIM,LHE"
    " --eventcontent RAWSIM,LHE"
    " --python_filename {cfg}"
    " --fileout file:{name}.root"
    " --number {n_events}"
    " --number_out {n_events}"
    " --no_exec --mc"
)

CRAB_TEMPLATE = """\
from CRABClient.UserUtilities import config
config = config()

config.General.requestName = '{name}'
config.General.workArea = '{work_area}'
config.General.transferOutputs = True
config.General.transferLogs = True

config.JobType.pluginName = 'PrivateMC'
config.JobType.psetName = '{cfg}'

config.Data.outputPrimaryDataset = '{name}'
config.Data.splitting = 'EventBased'
config.Data.unitsPerJob = {events_per_job}
config.Data.totalUnits = {total_events}
config.Data.outLFNDirBase = '{lfn_base}'
config.Data.publication = True
config.Data.outputDatasetTag = '{tag}'

config.Site.storageSite = '{site}'
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def discover_fragments(fragments_dir: Path, pattern: str | None) -> list[Path]:
    fragments = sorted(fragments_dir.glob("*_cfi.py"))
    if pattern:
        fragments = [f for f in fragments if pattern in f.name]
    return fragments


def sample_name(fragment: Path) -> str:
    """Strip _cfi suffix to get the canonical sample name."""
    return fragment.stem.removesuffix("_cfi")


def is_already_submitted(work_area: Path, name: str) -> bool:
    """CRAB creates crab_<name>/ inside workArea after a successful submit."""
    return (work_area / name / f"crab_{name}").exists()


def run(cmd: str, cwd: Path, dry_run: bool) -> None:
    print(f"    $ {cmd}")
    if dry_run:
        return
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(f"Command exited with code {result.returncode}")


def generate_cfg(fragment: Path, name: str, job_dir: Path,
                 n_events: int, dry_run: bool) -> Path:
    cfg = job_dir / f"{name}_cfg.py"
    cmd = CMSDRIVER_TEMPLATE.format(
        fragment=fragment.name,
        cfg=cfg.name,
        name=name,
        n_events=n_events,
    )
    run(cmd, cwd=job_dir, dry_run=dry_run)
    return cfg


def write_crab_config(name: str, cfg: Path, work_area: Path,
                      events_per_job: int, total_events: int,
                      lfn_base: str, tag: str, site: str) -> Path:
    crab_cfg = cfg.parent / f"crab_{name}.py"
    crab_cfg.write_text(CRAB_TEMPLATE.format(
        name=name,
        work_area=str(work_area),
        cfg=str(cfg),
        events_per_job=events_per_job,
        total_events=total_events,
        lfn_base=lfn_base,
        tag=tag,
        site=site,
    ))
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
        description="Submit GEN-SIM CRAB jobs for DQCD Run3 2024 production.",
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
        "--work-area", type=str, default="crab_gensim",
        help="CRAB workArea directory (created if absent)",
    )
    p.add_argument(
        "--n-events", type=int, default=10000,
        help="Total events per sample",
    )
    p.add_argument(
        "--events-per-job", type=int, default=500,
        help="Events per CRAB job",
    )
    p.add_argument(
        "--lfn-base", type=str, default="/store/user/YOUR_USERNAME/samples/GEN-SIM/",
        help="LFN output base path on the storage element",
    )
    p.add_argument(
        "--site", type=str, default="T2_UK_London_IC",
        help="CMS storage site for output",
    )
    p.add_argument(
        "--tag", type=str, default="RunIII2024Summer24wmLHEGS",
        help="CRAB outputDatasetTag",
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
    args = parse_args()

    fragments = discover_fragments(args.fragments_dir, args.filter)
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
    work_area.mkdir(parents=True, exist_ok=True)

    label = "[DRY-RUN] " if args.dry_run else ""
    print(f"{label}Processing {len(fragments)} fragment(s)  |  "
          f"{args.n_events} events/sample  |  {args.events_per_job} events/job\n")

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
            cfg = generate_cfg(fragment, name, job_dir, args.n_events, args.dry_run)
            crab_cfg = write_crab_config(
                name=name,
                cfg=cfg,
                work_area=work_area,
                events_per_job=args.events_per_job,
                total_events=args.n_events,
                lfn_base=args.lfn_base,
                tag=args.tag,
                site=args.site,
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
