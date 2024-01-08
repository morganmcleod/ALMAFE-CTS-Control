import os
from AmpPhaseDataLib.Constants import DataSource, PlotEl, SpecLines, DataKind
from AmpPhaseDataLib.LegacyImport import importTimeSeriesBand6CTS_experimental2
from AmpPhaseDataLib import TimeSeriesAPI
from AmpPhasePlotLib import PlotAPI
tsa = TimeSeriesAPI.TimeSeriesAPI()
plt = PlotAPI.PlotAPI()

band = 6
systemName = 'CTS2'

tsIds = [199]

for tsId in tsIds:
    spectrumPlotEls = { 
        PlotEl.SPEC_LINE1 : SpecLines.BAND6_PHASE_STABILITY1,
        PlotEl.SPEC_LINE2 : SpecLines.BAND6_PHASE_STABILITY2,
        PlotEl.SPEC2_NAME : "CTS relaxed spec"
    }
    plt.plotTimeSeries(tsId, show = True, unwrapPhase = True)
    plt.plotPhaseStability(tsId, plotElements = spectrumPlotEls, show = True)