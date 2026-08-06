#!/usr/bin/env python3
"""
Materialize hadronizer-only (2024-fragments/) and complete (2024-fragments/complete/)
GEN fragments for every (scenario, mpi, mA, ctau) card found in dqcd-cards/ that
doesn't have one yet.

dqcd-cards/scenario<X>_mpi_<mpi>_mA_<mA>_ctau_<ctau>_cfi.py holds the raw decay
parameters (Pythia8ConcurrentGeneratorFilter, self-contained -- no external LHE, no
dimuon filter, MCTunes2017 tune). Every fragment already in 2024-fragments/complete/
is a mechanical transform of the matching card:
  1. Tune import: MCTunes2017 -> MCTunesRun3ECM13p6TeV
  2. Filter type: Pythia8ConcurrentGeneratorFilter -> Pythia8ConcurrentHadronizerFilter
     (the card generates the hard process itself; the production fragment instead
     hadronizes an LHE event read from the POWHEG ggH gridpack)
  3. Two lines appended to processParameters (POWHEG:nFinal + ParticleDecays:limitTau0)
  4. 2024-fragments/<stem>_cfi.py = the transformed block alone
     2024-fragments/complete/<stem>_cfi.py = gridpack ExternalLHEProducer header +
     the transformed block + a MuMuFilter (MinPt 2 GeV, |eta|<2.5) + ProductionFilterSequence
This was verified against the 86 fragments that already exist in both directories
(see README "GEN-SIM -> RAWSIM..." sections) -- this script reproduces them exactly
modulo harmless numeric-literal formatting (e.g. "10" vs "10.0"), which is why
already-existing targets are always skipped rather than overwritten.

Only scenarios with an established GluGluHToDarkShowers-Scenario<X> naming precedent
in 2024-fragments/complete/ or 2024-fragments/ are handled (A, B1, B2, C). The
hiddenValleyGridPack_vector_* (different physics model) and testZPrime_* cards in
dqcd-cards/ have no such precedent and are intentionally left untouched.

Usage:
  python3 build_fragments_from_cards.py --dry-run
  python3 build_fragments_from_cards.py --filter ScenarioA
  python3 build_fragments_from_cards.py
"""

import argparse
import re
from pathlib import Path

CARDS_DIR = Path(__file__).resolve().parent.parent / "dqcd-cards"
FRAGS_DIR = Path(__file__).resolve().parent.parent / "2024-fragments"
COMPLETE_DIR = FRAGS_DIR / "complete"

CARD_RE = re.compile(
    r"^scenario(?P<scenario>A|B1|B2|C)_mpi_(?P<mpi>[^_]+)_mA_(?P<mA>[^_]+)_ctau_(?P<ctau>[^_]+)_cfi\.py$"
)

COMPLETE_RE = re.compile(
    r"^GluGluHToDarkShowers-Scenario(?P<scenario>A|B1|B2|C)_Par-ctau-(?P<ctau>[^-]+)-mA-(?P<mA>[^-]+)-mpi-(?P<mpi>[^_]+)_cfi\.py$"
)

GRIDPACK = (
    "/cvmfs/cms.cern.ch/phys_generator/gridpacks/RunIII/13p6TeV/"
    "slc7_amd64_gcc10/powheg/V2/"
    "gg_H_quark-mass-effects_mwindow1d0_slc7_amd64_gcc10_CMSSW_12_4_8.tgz"
)

TUNE_OLD = "MCTunes2017"
TUNE_NEW = "MCTunesRun3ECM13p6TeV"
FILTER_OLD = "Pythia8ConcurrentGeneratorFilter"
FILTER_NEW = "Pythia8ConcurrentHadronizerFilter"

# Anchor line every card's processParameters block ends on -- verified across every
# sampled scenario A/B1/B2/C card. The two extra lines get inserted right after it.
ONMODE_LINE = '            "4900211:onMode = 0",\n'
EXTRA_LINES = (
    '            "ParticleDecays:limitTau0 = off           ! Tau limits to override pythia8CommonSettings configuration",\n'
    '            "POWHEG:nFinal = 1           ! needed since it uses ggH gridpacks",\n'
)

MUMU_BLOCK = (
    "\n\n"
    'MuMuFilter = cms.EDFilter("MCParticlePairFilter",\n'
    "    Status = cms.untracked.vint32(1, 1),\n"
    "    MinPt = cms.untracked.vdouble(2, 2),\n"
    "    MaxEta = cms.untracked.vdouble(2.5, 2.5),\n"
    "    MinEta = cms.untracked.vdouble(-2.5, -2.5),\n"
    "    ParticleID1 = cms.untracked.vint32(13,-13),\n"
    ")\n"
    "ProductionFilterSequence = cms.Sequence(generator*MuMuFilter)\n"
)


def external_lhe_header() -> str:
    return f"""\
import FWCore.ParameterSet.Config as cms

externalLHEProducer = cms.EDProducer("ExternalLHEProducer",
    args = cms.vstring('{GRIDPACK}'),
    nEvents = cms.untracked.uint32(5000),
    numberOfParameters = cms.uint32(1),
    outputFile = cms.string('cmsgrid_final.lhe'),
    generateConcurrently = cms.untracked.bool(True),
    scriptName = cms.FileInPath('GeneratorInterface/LHEInterface/data/run_generic_tarball_cvmfs.sh')
)
"""


def extract_generator_block(card_text: str) -> str:
    """Card content from the top through the generator EDFilter's closing paren
    (a bare ')' at column 0), transformed to the production hadronizer style.
    Anything after that line (MuMuFilter/ProductionFilterSequence in the card,
    sometimes even duplicated -- see scenarioB2/C cards) is discarded: the
    production fragment gets its own filter block appended separately."""
    start = card_text.index("generator = cms.EDFilter(")
    m = re.search(r"\n\)\n", card_text[start:])
    if not m:
        raise ValueError("could not find the generator EDFilter's closing paren")
    block = card_text[: start + m.end()]

    if TUNE_OLD in block:
        block = block.replace(TUNE_OLD, TUNE_NEW)
    elif TUNE_NEW not in block:
        # A handful of cards were already updated to the Run3 tune ahead of the
        # rest -- only error if neither the old nor the new tune import is there.
        raise ValueError(f"neither '{TUNE_OLD}' nor '{TUNE_NEW}' tune import found")

    if FILTER_OLD not in block:
        raise ValueError(f"expected filter type '{FILTER_OLD}' not found")
    block = block.replace(FILTER_OLD, FILTER_NEW, 1)

    if ONMODE_LINE not in block:
        raise ValueError("expected trailing '4900211:onMode = 0' line not found")
    block = block.replace(ONMODE_LINE, ONMODE_LINE + EXTRA_LINES, 1)

    return block


def hadronizer_fragment(card_text: str) -> str:
    return extract_generator_block(card_text) + "\n"


def complete_fragment(card_text: str, stem: str) -> str:
    block = extract_generator_block(card_text)
    footer = f"\n\n\n# Link to generator fragment:\n# {stem}_cfi.py\n"
    return external_lhe_header() + block + MUMU_BLOCK + footer


def to_num(s):
    return round(float(s.replace("p", ".")), 6)


def canonical_index(directory):
    """(scenario, mpi, mA, ctau) -> filename, for every GluGluHToDarkShowers-Scenario*
    fragment already in `directory`, keyed by numeric value rather than string
    formatting -- some legacy mass points (mpi=1.2, 2, 5, 7.5) use fewer decimal
    digits (e.g. 'mA-2p5') than the cards do ('mA-2p50') for the exact same sample,
    and string-only matching would create a formatting-divergent duplicate."""
    index = {}
    for f in directory.glob("GluGluHToDarkShowers-Scenario*_cfi.py"):
        m = COMPLETE_RE.match(f.name)
        if not m:
            continue
        key = (m["scenario"], to_num(m["mpi"]), to_num(m["mA"]), to_num(m["ctau"]))
        index[key] = f.name
    return index


def discover_cards(cards_dir, pattern):
    out = []
    for f in sorted(cards_dir.iterdir()):
        m = CARD_RE.match(f.name)
        if not m:
            continue
        if pattern and pattern not in f.name:
            continue
        out.append((f, m))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cards-dir", type=Path, default=CARDS_DIR)
    p.add_argument("--frags-dir", type=Path, default=FRAGS_DIR)
    p.add_argument("--complete-dir", type=Path, default=COMPLETE_DIR)
    p.add_argument("--filter", type=str, default=None, metavar="STR",
                    help="Only process cards whose filename contains STR")
    p.add_argument("--dry-run", action="store_true",
                    help="Report what would be created without writing anything")
    args = p.parse_args()

    cards = discover_cards(args.cards_dir, args.filter)
    if not cards:
        raise SystemExit(f"No cards found in {args.cards_dir}" + (f" matching '{args.filter}'" if args.filter else ""))

    args.frags_dir.mkdir(exist_ok=True)
    args.complete_dir.mkdir(exist_ok=True)

    hadr_index = canonical_index(args.frags_dir)
    comp_index = canonical_index(args.complete_dir)

    n_hadr_created = n_hadr_skipped = 0
    n_comp_created = n_comp_skipped = 0
    n_errors = 0
    by_scenario_new = {}

    for card_path, m in cards:
        scenario, mpi, mA, ctau = m["scenario"], m["mpi"], m["mA"], m["ctau"]
        stem = f"GluGluHToDarkShowers-Scenario{scenario}_Par-ctau-{ctau}-mA-{mA}-mpi-{mpi}"
        key = (scenario, to_num(mpi), to_num(mA), to_num(ctau))

        hadr_path = args.frags_dir / f"{stem}_cfi.py"
        comp_path = args.complete_dir / f"{stem}_cfi.py"

        if key in hadr_index and key in comp_index:
            n_hadr_skipped += 1
            n_comp_skipped += 1
            continue

        try:
            card_text = card_path.read_text()
        except OSError as exc:
            print(f"    ERROR reading {card_path.name}: {exc}")
            n_errors += 1
            continue

        try:
            if key in hadr_index:
                n_hadr_skipped += 1
            else:
                content = hadronizer_fragment(card_text)
                if not args.dry_run:
                    hadr_path.write_text(content)
                hadr_index[key] = hadr_path.name
                n_hadr_created += 1

            if key in comp_index:
                n_comp_skipped += 1
            else:
                content = complete_fragment(card_text, stem)
                if not args.dry_run:
                    comp_path.write_text(content)
                comp_index[key] = comp_path.name
                n_comp_created += 1
                by_scenario_new[scenario] = by_scenario_new.get(scenario, 0) + 1
        except ValueError as exc:
            print(f"    ERROR transforming {card_path.name}: {exc}")
            n_errors += 1

    label = "[DRY-RUN] " if args.dry_run else ""
    print(f"{label}Cards processed: {len(cards)}")
    print(f"{label}2024-fragments/:          created {n_hadr_created:4d}  skipped {n_hadr_skipped:4d}")
    print(f"{label}2024-fragments/complete/: created {n_comp_created:4d}  skipped {n_comp_skipped:4d}")
    print(f"{label}New complete fragments by scenario: {by_scenario_new}")
    if n_errors:
        print(f"{label}ERRORS: {n_errors}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
