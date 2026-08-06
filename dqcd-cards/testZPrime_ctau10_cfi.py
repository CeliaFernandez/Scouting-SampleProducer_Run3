import FWCore.ParameterSet.Config as cms

from Configuration.Generator.Pythia8CommonSettings_cfi import *
from Configuration.Generator.MCTunesRun3ECM13p6TeV.PythiaCP5Settings_cfi import *
from Configuration.Generator.PSweightsPythia.PythiaPSweightsSettings_cfi import *




generator = cms.EDFilter("Pythia8ConcurrentGeneratorFilter",
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
            "HiddenValley:Ngauge=3",
            "HiddenValley:nFlav=2",
            "HiddenValley:spinFv=0",
            "HiddenValley:Lambda=0.35",
            "HiddenValley:ffbar2Zv=on",
            "HiddenValley:FSR=on",
            "HiddenValley:fragment=on",
            "HiddenValley:probVector=0",
            "HiddenValley:aLund=0.1",
            "HiddenValley:bmqv2=2.0",
            "HiddenValley:rFactqv=1.0",
            "4900023:onMode = off",
            "4900023:m0=91",
            "4900023:mMin=0",
            "4900023:mWidth=1",
            "4900101:m0=0.4",
            "4900023:addChannel = 1 1 100 4900101 -4900101",
            "4900113:m0=3",
            "4900213:m0=3",
            "4900211:m0=2",
            "4900111:m0=2",
            "4900211:mayDecay=on",
            "4900111:mayDecay=on",
            "4900211:addChannel = 1 1 103 13 -13",
            "4900111:addChannel = 1 1 103 13 -13",
            "4900211:tau0=10",
            "4900111:tau0=10",
        ),
        parameterSets = cms.vstring(
            'pythia8CommonSettings',
            'processParameters',
            'pythia8PSweightsSettings',
            'pythia8CP5Settings',
        ),
    )
)

MuMuFilter = cms.EDFilter("MCParticlePairFilter",
    Status = cms.untracked.vint32(1, 1),
    MinPt = cms.untracked.vdouble(1, 1),
    MaxEta = cms.untracked.vdouble(2.5, 2.5),
    MinEta = cms.untracked.vdouble(-2.5, -2.5),
    ParticleID1 = cms.untracked.vint32(13,-13),
)

ProductionFilterSequence = cms.Sequence(generator*MuMuFilter)
generator.PythiaParameters.pythia8CommonSettings.extend(['ParticleDecays:limitTau0 = off'])
MuMuFilter = cms.EDFilter("MCParticlePairFilter",
    Status = cms.untracked.vint32(1, 1),
    MinPt = cms.untracked.vdouble(2, 2),
    MaxEta = cms.untracked.vdouble(2.5, 2.5),
    MinEta = cms.untracked.vdouble(-2.5, -2.5),
    ParticleID1 = cms.untracked.vint32(13,-13),
)
ProductionFilterSequence = cms.Sequence(generator*MuMuFilter)
