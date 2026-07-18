#!/usr/bin/env python3
"""
Generate 2024 GEN-SIM fragments for new (mpi, mA) mass points.

Creates both hadronizer-only files (2024-fragments/) and complete production
files with ExternalLHEProducer prepended (2024-fragments/complete/).
"""

from pathlib import Path

FRAGS_DIR    = Path(__file__).resolve().parent.parent / "2024-fragments"
COMPLETE_DIR = FRAGS_DIR / "complete"
GRIDPACK     = (
    "/cvmfs/cms.cern.ch/phys_generator/gridpacks/RunIII/13p6TeV/"
    "slc7_amd64_gcc10/powheg/V2/"
    "gg_H_quark-mass-effects_mwindow1d0_slc7_amd64_gcc10_CMSSW_12_4_8.tgz"
)

# ---------------------------------------------------------------------------
# Physics parameters per mass point
# ---------------------------------------------------------------------------

# (mpi_str, mA_str): physics block
MASS_POINTS = {
    ("2", "0p67"): dict(
        Lambda       = "8",
        pTminFSR     = "8.8",
        mq1          = "8.22461766742075",
        mq2          = "8.27538233257925",
        m_pi         = "2",
        m_eta_rho    = "8",
        # ScenarioA: 9900015 is the dark photon, its tau0 is the ctau parameter
        scenA_pdg    = "9900015",
        scenA_mass   = "0.6666666666666666",
        scenA_pi3_tau0 = "0.000549",
        scenA_channels = [
            "9900015:addChannel = 1 0.171 91 11 -11              ! A' -> e+ e-",
            "9900015:addChannel = 1 0.17 91 13 -13              ! A' -> mu+ mu-",
            "9900015:addChannel = 1 0.685 91 211 -211              ! A' -> pi+ pi-",
            "9900015:addChannel = 1 0.00479 91 211 -211 111              ! A' -> pi+ pi- pi0",
        ],
        # ScenarioB1: 999999 is the dark photon (prompt), dark pion tau0 is the ctau
        scenB1_pdg   = "999999",
        scenB1_mass  = "0.6666666666666666",
        scenB1_a_tau0 = "2.09e-09",
        scenB1_channels = [
            "999999:addChannel = 1 0.171 91 11 -11              ! A' -> e+ e-",
            "999999:addChannel = 1 0.17 91 13 -13              ! A' -> mu+ mu-",
            "999999:addChannel = 1 0.685 91 211 -211              ! A' -> pi+ pi-",
            "999999:addChannel = 1 0.00479 91 211 -211 111              ! A' -> pi+ pi- pi0",
        ],
        ctau_values  = [
            (0.1,  "0p1"),  (0.25, "0p25"), (0.3,  "0p3"),  (0.6,  "0p6"),
            (1.0,  "1p0"),  (2.5,  "2p5"),  (3.0,  "3p0"),  (6.0,  "6p0"),
            (10,   "10"),   (25.0, "25"),   (30,   "30"),   (60.0, "60"),
            (100,  "100"),  (1000, "1000"),
        ],
    ),
    ("5", "1p67"): dict(
        Lambda       = "20.0",
        pTminFSR     = "22.0",
        mq1          = "20.561544168551873",
        mq2          = "20.688455831448127",
        m_pi         = "5.0",
        m_eta_rho    = "20.0",
        scenA_pdg    = "9900015",
        scenA_mass   = "1.6666666666666667",
        scenA_pi3_tau0 = "0.0002199000159900015998",
        scenA_channels = [
            "9900015:addChannel = 1 0.0833 91 1 -1              ! A' -> d dbar",
            "9900015:addChannel = 1 0.333 91 2 -2              ! A' -> u ubar",
            "9900015:addChannel = 1 0.0833 91 3 -3              ! A' -> s sbar",
            "9900015:addChannel = 1 0.25 91 11 -11              ! A' -> e+ e-",
            "9900015:addChannel = 1 0.25 91 13 -13              ! A' -> mu+ mu-",
        ],
        scenB1_pdg   = "999999",
        scenB1_mass  = "1.6666666666666667",
        scenB1_a_tau0 = "1.22e-09",
        scenB1_channels = [
            "999999:addChannel = 1 0.0833 91 1 -1              ! A' -> d dbar",
            "999999:addChannel = 1 0.333 91 2 -2              ! A' -> u ubar",
            "999999:addChannel = 1 0.0833 91 3 -3              ! A' -> s sbar",
            "999999:addChannel = 1 0.25 91 11 -11              ! A' -> e+ e-",
            "999999:addChannel = 1 0.25 91 13 -13              ! A' -> mu+ mu-",
        ],
        ctau_values  = [
            (0.1,  "0p1"),  (0.25, "0p25"), (0.3,  "0p3"),  (0.6,  "0p6"),
            (1.0,  "1p0"),  (2.5,  "2p5"),  (3.0,  "3p0"),  (6.0,  "6p0"),
            (10,   "10"),   (25.0, "25"),   (30,   "30"),   (60.0, "60"),
            (100,  "100"),  (1000, "1000"),
        ],
    ),
    ("7p5", "2p5"): dict(
        Lambda       = "30.0",
        pTminFSR     = "33.0",
        mq1          = "30.84231625282781",
        mq2          = "31.03268374717219",
        m_pi         = "7.5",
        m_eta_rho    = "30.0",
        scenA_pdg    = "9900015",
        scenA_mass   = "2.5",
        scenA_pi3_tau0 = "0.000146",
        scenA_channels = [
            "9900015:addChannel = 1 0.0726 91 1 -1              ! A' -> d dbar",
            "9900015:addChannel = 1 0.29 91 2 -2              ! A' -> u ubar",
            "9900015:addChannel = 1 0.0726 91 3 -3              ! A' -> s sbar",
            "9900015:addChannel = 1 0.129 91 4 -4              ! A' -> c cbar",
            "9900015:addChannel = 1 0.218 91 11 -11              ! A' -> e+ e-",
            "9900015:addChannel = 1 0.218 91 13 -13              ! A' -> mu+ mu-",
        ],
        scenB1_pdg   = "999999",
        scenB1_mass  = "2.5",
        scenB1_a_tau0 = "7.089999999999999e-10",
        scenB1_channels = [
            "999999:addChannel = 1 0.0726 91 1 -1              ! A' -> d dbar",
            "999999:addChannel = 1 0.29 91 2 -2              ! A' -> u ubar",
            "999999:addChannel = 1 0.0726 91 3 -3              ! A' -> s sbar",
            "999999:addChannel = 1 0.129 91 4 -4              ! A' -> c cbar",
            "999999:addChannel = 1 0.218 91 11 -11              ! A' -> e+ e-",
            "999999:addChannel = 1 0.218 91 13 -13              ! A' -> mu+ mu-",
        ],
        ctau_values  = [
            (0.1,  "0p1"),  (0.25, "0p25"), (0.6,  "0p6"),
            (1.0,  "1p0"),  (2.5,  "2p5"),  (6.0,  "6p0"),
            (10,   "10"),   (25.0, "25"),   (60.0, "60"),
            (100,  "100"),  (1000, "1000"),
        ],
    ),
}


# ---------------------------------------------------------------------------
# Fragment builders
# ---------------------------------------------------------------------------

def _join_lines(items):
    """Join a list of strings as consecutive lines with 12-space indent."""
    return "\n            ".join(items)


def _scenA_block(p, ctau_str, ctau_val, pdg):
    channel_lines = _join_lines(f'"{ch}",' for ch in p["scenA_channels"])
    parts = [
        f'"{pdg}:all = GeneralResonance void 1 0 0 {p["scenA_mass"]} 0.001 0. 0. 0.        ! dark photon A\'",',
        channel_lines,
        f'"{pdg}:tau0 = {ctau_val}                            ! proper lifetime, in mm",',
        '"4900221:addChannel = 1 0.5 91 4900211 4900211 4900111              ! eta -> pi1 pi1 pi3",',
        '"4900221:addChannel = 1 0.5 91 -4900211 -4900211 4900111              ! eta -> pi2 pi2 pi3",',
        '"4900221:tau0 = 0.0                            ! proper lifetime, in mm",',
        f'"4900111:addChannel = 1 1.0 91 {pdg} {pdg}              ! pi3 -> A\'A\'",',
        f'"4900111:tau0 = {p["scenA_pi3_tau0"]}                            ! proper lifetime, in mm",',
    ]
    return _join_lines(parts)


def _scenB1_block(p, ctau_str, ctau_val, pdg):
    channel_lines = _join_lines(f'"{ch}",' for ch in p["scenB1_channels"])
    parts = [
        f'"{pdg}:all = GeneralResonance void 1 0 0 {p["scenB1_mass"]} 0.001 0. 0. 0.        ! dark photon A\'",',
        channel_lines,
        f'"{pdg}:tau0 = {p["scenB1_a_tau0"]}                            ! proper lifetime, in mm",',
        '"4900221:addChannel = 1 0.5 91 4900211 4900211 4900111              ! eta -> pi1 pi1 pi3",',
        '"4900221:addChannel = 1 0.5 91 -4900211 -4900211 4900111              ! eta -> pi2 pi2 pi3",',
        '"4900221:tau0 = 0.0                            ! proper lifetime, in mm",',
        f'"4900111:addChannel = 1 1.0 91 {pdg} {pdg}              ! pi3 -> A\'A\'",',
        f'"4900111:tau0 = {ctau_val}                            ! proper lifetime, in mm",',
    ]
    return _join_lines(parts)


def hadronizer_content(p, scenario_block, stem):
    return f"""\
import FWCore.ParameterSet.Config as cms

from Configuration.Generator.Pythia8CommonSettings_cfi import *
from Configuration.Generator.MCTunesRun3ECM13p6TeV.PythiaCP5Settings_cfi import *
from Configuration.Generator.PSweightsPythia.PythiaPSweightsSettings_cfi import *




generator = cms.EDFilter("Pythia8ConcurrentHadronizerFilter",
    pythiaPylistVerbosity = cms.untracked.int32(1),
    filterEfficiency = cms.untracked.double(1.0),
    pythiaHepMCVerbosity = cms.untracked.bool(False),
    comEnergy = cms.double(13600.0),
    crossSection = cms.untracked.double(1.),
    maxEventsToPrint = cms.untracked.int32(1),
    PythiaParameters = cms.PSet(
        pythia8CommonSettingsBlock,
        pythia8PSweightsSettingsBlock,
        pythia8CP5SettingsBlock,
        processParameters = cms.vstring(
            "HiggsSM:gg2H = on",
            "25:m0 =125",
            "25:addChannel = 1 0.5 102 4900101 -4900101",
            "25:addChannel = 1 0.5 102 4900102 -4900102",
            "25:0:onMode=0",
            "25:1:onMode=0",
            "25:2:onMode=0",
            "25:3:onMode=0",
            "25:4:onMode=0",
            "25:5:onMode=0",
            "25:6:onMode=0",
            "25:7:onMode=0",
            "25:8:onMode=0",
            "25:9:onMode=0",
            "25:10:onMode=0",
            "25:11:onMode=0",
            "25:12:onMode=0",
            "25:13:onMode=0",
            "HiddenValley:Ngauge = 3                          ! number of colors",
            "HiddenValley:nFlav = 2                           ! number of flavors",
            "HiddenValley:fragment = on",
            "HiddenValley:FSR = on",
            "HiddenValley:alphaOrder = 1                      ! use running coupling",
            "HiddenValley:setLambda = on                      ! only for pythia 8.309 and higher",
            "HiddenValley:Lambda = {p['Lambda']}              ! dark confinement scale",
            "HiddenValley:pTminFSR = {p['pTminFSR']}        ! pT cut off on dark shower (IR regulator)",
            "HiddenValley:spinFv=0                            ! spin of bifundamentals: not used, but set for consistency",
            "HiddenValley:probVector=0.75                     ! fraction of hadronization to spin 1",
            "HiddenValley:separateFlav = on                   ! allow for non-degenerate mesons",
            "HiddenValley:probKeepEta1 = 1.0                  ! suppression factor for eta hadronization",
            "4900101:m0 = {p['mq1']}          ! Dark Quark Mass, following arXiv:2203.09503",
            "4900102:m0 = {p['mq2']}          ! Dark Quark Mass, following arXiv:2203.09503",
            "4900111:m0 = {p['m_pi']}                        ! Setting pion Mass",
            "4900211:m0 = {p['m_pi']}                        ! Setting pion Mass",
            "4900221:m0 = {p['m_eta_rho']}                        ! Setting eta Mass",
            "4900113:m0 = {p['m_eta_rho']}                       ! Setting rho Mass",
            "4900213:m0 = {p['m_eta_rho']}                       ! Setting rho Mass",
            "4900113:addChannel = 1 1.00 91 4900211 -4900211",
            "4900213:addChannel = 1 1.00 91 4900211 4900111",
            {scenario_block}
            "4900211:onMode = 0",
            "ParticleDecays:limitTau0 = off           ! Tau limits to override pythia8CommonSettings configuration",
            "POWHEG:nFinal = 1           ! needed since it uses ggH gridpacks",
        ),
        parameterSets = cms.vstring(
            'pythia8CommonSettings',
            'processParameters',
            'pythia8PSweightsSettings',
            'pythia8CP5Settings',
        ),
    )
)



# Link to generator fragment:
# {stem}_cfi.py
"""


def external_lhe_header():
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    FRAGS_DIR.mkdir(exist_ok=True)
    COMPLETE_DIR.mkdir(exist_ok=True)

    n_created = n_skipped = 0

    for (mpi_str, mA_str), p in MASS_POINTS.items():
        for ctau_val, ctau_str in p["ctau_values"]:
            for scenario in ("A", "B1"):
                stem = (
                    f"GluGluHToDarkShowers-Scenario{scenario}"
                    f"_Par-ctau-{ctau_str}-mA-{mA_str}-mpi-{mpi_str}"
                )
                fname = f"{stem}_cfi.py"

                if scenario == "A":
                    pdg   = p["scenA_pdg"]
                    sblock = _scenA_block(p, ctau_str, ctau_val, pdg)
                else:
                    pdg   = p["scenB1_pdg"]
                    sblock = _scenB1_block(p, ctau_str, ctau_val, pdg)

                hadronizer = hadronizer_content(p, sblock, stem)
                complete   = external_lhe_header() + hadronizer

                hadr_path = FRAGS_DIR / fname
                comp_path = COMPLETE_DIR / fname

                for path, content in [(hadr_path, hadronizer), (comp_path, complete)]:
                    if path.exists():
                        n_skipped += 1
                    else:
                        path.write_text(content)
                        n_created += 1

    print(f"Done — created: {n_created}  skipped (already existed): {n_skipped}")


if __name__ == "__main__":
    main()
