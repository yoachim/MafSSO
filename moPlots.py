import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.patches import Ellipse
from matplotlib.collections import PatchCollection

from lsst.sims.maf.plots import BasePlotter


class MetricVsH(BasePlotter):
    """
    Plot metric values versus H.
    Marginalize over metric values in each H bin using 'npReduce'.
    """
    def __init__(self):
        self.plotType = 'MetricVsH'
        self.objectPlotter = False
        self.defaultPlotDict = {'title':None, 'xlabel':'H (mag)', 'ylabel':None, 'label':None,
                                'linestyle':'-', 'npReduce':None, 'nbins':None}
        self.minHrange=1.0

    def __call__(self, metricValue, slicer, userPlotDict, fignum=None):
        fig = plt.figure(fignum)
        plotDict = {}
        plotDict.update(self.defaultPlotDict)
        plotDict.update(userPlotDict)
        Hvals = slicer.slicePoints['H']
        reduceFunc = plotDict['npReduce']
        if reduceFunc is None:
            reduceFunc = np.mean
        if Hvals.shape == metricValue.shape:
            # We have a simple set of values to plot against H.
            # This may be due to running a secondary metric, such as completeness.
            mVals = metricValue.filled()
        elif len(Hvals) == slicer.slicerShape[1]:
            # Using cloned H distribution.
            # Apply 'npReduce' method directly to metric values, and plot at matching H values.
            mVals = reduceFunc(metricValue, axis=0)
        else:
            # Probably each object has its own H value.
            hrange = Hvals.max() - Hvals.min()
            minH = Hvals.min()
            if hrange < self.minHrange:
                hrange = self.minHrange
                minH = Hvals.min() - hrange/2.0
            nbins = plotDict['nbins']
            if nbins is None:
                nbins = 30
            stepsize = hrange  / float(nbins)
            bins = np.arange(minH, minH + hrange + stepsize/2.0, stepsize)
            # In each bin of H, calculate the 'npReduce' value of the corresponding metricValues.
            inds = np.digitize(Hvals, bins)
            inds = inds-1
            mVals = np.zeros(len(bins), float)
            for i in range(len(bins)):
                match = metricValue[inds == i]
                if len(match) == 0:
                    mVals[i] = slicer.badval
                else:
                    mVals[i] = reduceFunc(match.filled())
            Hvals = bins
        plt.plot(Hvals, mVals, color=plotDict['color'], linestyle=plotDict['linestyle'],
                label=plotDict['label'])
        plt.title(plotDict['title'])
        plt.xlabel(plotDict['xlabel'])
        plt.ylabel(plotDict['ylabel'])
        if 'xMin' in plotDict:
            plt.xlim(xmin = plotDict['xMin'])
        if 'xMax' in plotDict:
            plt.xlim(xmax = plotDict['xMax'])
        return fig.number


class MetricVsOrbit(BasePlotter):
    """
    Plot metric values (at a particular H value) vs. orbital parameters.
    Marginalize over metric values in each orbital bin using 'npReduce'.
    """
    def __init__(self, xaxis='q', yaxis='e'):
        self.plotType = 'MetricVsOrbit'
        self.objectPlotter = False
        self.defaultPlotDict = {'title':None, 'xlabel':xaxis, 'ylabel':yaxis,
                                'xaxis':xaxis, 'yaxis':yaxis,
                                'label':None, 'cmap':cm.cubehelix,
                                'npReduce':None,
                                'nxbins':None, 'nybins':None, 'levels':None,
                                'Hval':None, 'Hwidth':None}

    def __call__(self, metricValue, slicer, userPlotDict, fignum=None):
        fig = plt.figure(fignum)
        plotDict = {}
        plotDict.update(self.defaultPlotDict)
        plotDict.update(userPlotDict)
        xvals = slicer.slicePoints['orbits'][plotDict['xaxis']]
        yvals = slicer.slicePoints['orbits'][plotDict['yaxis']]
        # Set x/y bins.
        nxbins = plotDict['nxbins']
        nybins = plotDict['nybins']
        if nxbins is None:
            nxbins = 100
        if nybins is None:
            nybins = 100
        if 'xbins' in plotDict:
            xbins = plotDict['xbins']
        else:
            xbinsize = (xvals.max() - xvals.min())/float(nxbins)
            xbins = np.arange(xvals.min(), xvals.max() + xbinsize/2.0, xbinsize)
        if 'ybins' in plotDict:
            ybins = plotDict['ybins']
        else:
            ybinsize = (yvals.max() - yvals.min())/float(nybins)
            ybins = np.arange(yvals.min(), yvals.max() + ybinsize/2.0, ybinsize)
        nxbins = len(xbins)
        nybins = len(ybins)
        # Identify the relevant metricValues for the Hvalue we want to plot.
        Hvals = slicer.slicePoints['H']
        Hwidth = plotDict['Hwidth']
        if Hwidth is None:
            Hwidth = 1.0
        if plotDict['Hval'] is None:
            if len(Hvals) == slicer.slicerShape[1]:
                Hidx = len(Hvals) / 2
                Hval = Hvals[Hidx]
            else:
                Hval = np.median(Hvals)
                Hidx = np.where(np.abs(Hvals - Hval) <= Hwidth/2.0)[0]
        if len(Hvals) == slicer.slicerShape[1]:
            mVals = np.swapaxes(metricValue, 1, 0)[Hidx].filled()
        else:
            mVals = metricValue[Hidx].filled()
        # Calculate the npReduce'd metric values at each x/y bin.
        binvals = np.zeros((nybins, nxbins), dtype='float') + slicer.badval
        xidxs = np.digitize(xvals, xbins) - 1
        yidxs = np.digitize(yvals, ybins) - 1
        reduceFunc = plotDict['npReduce']
        if reduceFunc is None:
            reduceFunc = np.mean
        for iy in range(nybins):
            ymatch = np.where(yidxs == iy)[0]
            for ix in range(nxbins):
                xmatch = np.where(xidxs[ymatch] == ix)[0]
                matchVals = mVals[ymatch][xmatch]
                if len(matchVals) > 0:
                    binvals[iy][ix] = reduceFunc(matchVals)
        xi, yi = np.meshgrid(xbins, ybins)
        if 'colorMin' in plotDict:
            vMin = plotDict['colorMin']
        else:
            vMin = binvals.min()
        if 'colorMax' in plotDict:
            vMax = plotDict['colorMax']
        else:
            vMax = binvals.max()
        nlevels = plotDict['levels']
        if nlevels is None:
            nlevels = 200
        levels = np.arange(vMin, vMax, (vMax-vMin)/float(nlevels))
        plt.contourf(xi, yi, binvals, levels, extend='max',
                     zorder=0, cmap=plotDict['cmap'])
        cbar = plt.colorbar()
        plt.title(plotDict['title'])
        plt.xlabel(plotDict['xlabel'])
        plt.ylabel(plotDict['ylabel'])
        return fig.number

class MetricVsOrbitPoints(BasePlotter):
    """
    Plot metric values (at a particular H value) as function of orbital parameters,
    using points for each metric value.
    """
    def __init__(self, xaxis='q', yaxis='e'):
        self.plotType = 'MetricVsOrbit'
        self.objectPlotter = False
        self.defaultPlotDict = {'title':None, 'xlabel':xaxis, 'ylabel':yaxis,
                                'label':None, 'cmap':cm.cubehelix,
                                'xaxis':xaxis, 'yaxis':yaxis,
                                'Hval':None, 'Hwidth':None,
                                'foregroundPoints':True, 'backgroundPoints':False}

    def __call__(self, metricValue, slicer, userPlotDict, fignum=None):
        fig = plt.figure(fignum)
        plotDict = {}
        plotDict.update(self.defaultPlotDict)
        plotDict.update(userPlotDict)
        xvals = slicer.slicePoints['orbits'][plotDict['xaxis']]
        yvals = slicer.slicePoints['orbits'][plotDict['yaxis']]
        # Identify the relevant metricValues for the Hvalue we want to plot.
        Hvals = slicer.slicePoints['H']
        Hwidth = plotDict['Hwidth']
        if Hwidth is None:
            Hwidth = 1.0
        if plotDict['Hval'] is None:
            if len(Hvals) == slicer.slicerShape[1]:
                Hidx = len(Hvals) / 2
                Hval = Hvals[Hidx]
            else:
                Hval = np.median(Hvals)
                Hidx = np.where(np.abs(Hvals - Hval) <= Hwidth/2.0)[0]
        if len(Hvals) == slicer.slicerShape[1]:
            mVals = np.swapaxes(metricValue, 1, 0)[Hidx]
        else:
            mVals = metricValue[Hidx]
        if 'colorMin' in plotDict:
            vMin = plotDict['colorMin']
        else:
            vMin = mVals.min()
        if 'colorMax' in plotDict:
            vMax = plotDict['colorMax']
        else:
            vMax = mVals.max()
        if plotDict['backgroundPoints']:
            # This isn't quite right for the condition .. but will do for now.
            condition = np.where(mVals == 0)
            plt.plot(xvals[condition], yvals[condition], 'r.', markersize=4, alpha=0.5, zorder=3)
        if plotDict['foregroundPoints']:
            plt.scatter(xvals, yvals, c=mVals, vmin=vMin, vmax=vMax,
                        cmap=plotDict['cmap'], s=15, alpha=0.8, zorder=0)
            cb = plt.colorbar()
        plt.title(plotDict['title'])
        plt.xlabel(plotDict['xlabel'])
        plt.ylabel(plotDict['ylabel'])
        return fig.number
