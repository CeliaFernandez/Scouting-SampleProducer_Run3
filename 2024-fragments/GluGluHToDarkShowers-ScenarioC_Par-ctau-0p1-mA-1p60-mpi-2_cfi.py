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
            "HiddenValley:Lambda = 2.88              ! dark confinement scale",
            "HiddenValley:pTminFSR = 3.168        ! pT cut off on dark shower (IR regulator)",
            "HiddenValley:spinFv=0                            ! spin of bifundamentals: not used, but set for consistency",
            "HiddenValley:probVector=0.75                     ! fraction of hadronization to spin 1",
            "HiddenValley:separateFlav = on                   ! allow for non-degenerate mesons",
            "HiddenValley:probKeepEta1 = 1.0                  ! suppression factor for eta hadronization",
            "4900101:m0 = 3.5039379650576374          ! Dark Quark Mass, following arXiv:2203.09503",
            "4900102:m0 = 3.644950923831251          ! Dark Quark Mass, following arXiv:2203.09503",
            "4900111:m0 = 2                        ! Setting pion Mass",
            "4900211:m0 = 2                        ! Setting pion Mass",
            "4900221:m0 = 2.88                        ! Setting eta Mass",
            "4900113:m0 = 2.88                       ! Setting rho Mass",
            "4900213:m0 = 2.88                       ! Setting rho Mass",
            "4900113:onMode = 0",
            "4900213:onMode = 0",
            "4900221:addChannel = 1 0.314 91 4900211 11 -11              ! eta -> pi2 e+ e-",
            "4900221:addChannel = 1 0.394 91 4900211 211 -211              ! eta -> pi2 pi+ pi-",
            "4900221:addChannel = 1 0.0281 91 4900211 211 -211 111              ! eta -> pi2 pi+ pi- pi0",
            "4900221:addChannel = 1 0.263 91 4900211 13 -13              ! eta -> pi2 mu+ mu-",
            "4900221:tau0 = 0.1                            ! proper lifetime, in mm",
            "4900111:onMode = 0",
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

