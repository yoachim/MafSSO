import numpy as np


__all__ = ['BaseMoMetric', 'NObsMetric', 'DiscoveryMetric',
           'ActivityOverTimeMetric', 'ActivityOverPeriodMetric']


class BaseMoMetric(object):
    def __init__(self,
                 m5Col='fiveSigmaDepth', lossCol='dmagDetect',
                 magFilterCol='magFilter',
                 nightCol='night', expMJDCol='expMJD'):
        self.m5Col = m5Col
        self.lossCol = lossCol
        self.magFilterCol = magFilterCol
        self.nightCol = nightCol
        self.expMJDCol = expMJDCol
        self.snrLimit = None
        self.colsReq = [self.m5Col, self.lossCol, self.magFilterCol,
                        self.nightCol, self.expMJDCol]

    def _calcAppMag(self, ssoObs, Hval, Href):
        """
        Adjust the apparent magnitude of the object in this filter for any changes to H
         (in case of cloning the objects in this orbit).
        """
        return ssoObs[self.magFilterCol] + Hval - Href

    def _calcMagLimit(self, ssoObs):
        """
        Calculate the effective magnitude limit, accounting for the velocity of the moving object.
        The mag limit must be adjusted by 'dmagDetect' if detection is done on a 'stationary
        object likelihood image' (this is the maximum loss).
        The mag limit should be adjusted by 'dmagTrailing' if only accounting for SNR loss
        due to increased number of sky pixels.
        """
        return ssoObs[self.m5Col] - ssoObs[self.lossCol]

    def _calcSNR(self, appMag, magLimit, gamma=0.038):
        """
        Calculate the SNR of a source with appMag in an image with 'magLimit'.
        """
        xval = np.power(10, 0.5*(appMag - magLimit))
        snr = 1.0 / np.sqrt((0.04 - gamma)*xval + gamma*xvxal*xval)
        return snr

    def _calcVis(self, appMag, magLimit, sigma=0.12):
        """
        Calculate whether an object is visible according to
        Fermi-Dirac completeness formula (see SDSS, eqn 24, Stripe82 analysis:
         http://iopscience.iop.org/0004-637X/794/2/120/pdf/apj_794_2_120.pdf).
        Calculate estimated completeness/probability of detection,
        then evaluates if this object could be visible.
        """
        completeness = 1.0 / (1 + np.exp((appMag - magLimit)/sigma))
        probability = np.random.random_sample(len(appMag))
        vis = np.where(probability <= completeness, 1, 0)
        return vis

    def _prep(self, ssoObs, orb, Hval):
        """
        We will almost always need to convert the incoming observation + Hval
        into apparent magnitude / see what's visible, etc.
        This is a convenience function for that.
        """
        if len(ssoObs) == 0:
            return ValueError('No data here')
        Href = orb['H']
        if Hval is None:
            Hval = Href
        appMag = self._calcAppMag(ssoObs, Hval, Href)
        magLimit = self._calcMagLimit(ssoObs)
        if self.snrLimit is None:
            snr = None
            vis = self._calcVis(appMag, magLimit)
        else:
            snr = self._calcSNR(appMag, magLimit)
            vis = np.where(snr >= self.snrLimit)[0]
        return appMag, magLimit, vis, snr

    def run(self, ssoObs, orb, Hval):
        raise NotImplementedError


class NObsMetric(BaseMoMetric):
    """
    Count the number of observations for an object.
    """
    def __init__(self, snrLimit=None, **kwargs):
        """
        @ snrLimit .. if snrLimit is None, this uses the _calcVis method/completeness
                      if snrLimit is not None, this uses that value as a cutoff instead.
        """
        super(NObsMetric, self).__init__(**kwargs)
        self.snrLimit = snrLimit

    def run(self, ssoObs, orb, Hval):
        try:
            appMag, magLimit, vis, snr = self._prep(ssoObs, orb, Hval)
            return np.where(vis == 1)[0].size
        except ValueError:
            return 0

class DiscoveryMetric(BaseMoMetric):
    """
    Count the number of discovery opportunities for an object.
    """
    def __init__(self, nObsPerNight=2, tNight=90.*60.,
                 nNightsPerWindow=3, tWindow=15, snrLimit=None, **kwargs):
        """
        @ nObsPerNight = number of observations per night required for tracklet
        @ tNight = max time start/finish for the tracklet (seconds)
        @ nNightsPerWindow = number of nights with observations required for track
        @ tWindow = max number of nights in track (days)
        @ snrLimit .. if snrLimit is None then uses 'completeness' calculation,
                   .. if snrLimit is not None, then uses this value as a cutoff.
        """
        super(DiscoveryMetric, self).__init__(**kwargs)
        self.snrLimit = snrLimit
        self.nObsPerNight = nObsPerNight
        self.tNight = tNight
        self.nNightsPerWindow = nNightsPerWindow
        self.tWindow = tWindow

    def run(self, ssoObs, orb, Hval):
        # Calculate visibility for this orbit at this H.
        try:
            appMag, magLimit, vis, snr = self._prep(ssoObs, orb, Hval)
        except ValueError:
            return 0
        # Calculate number of discovery chances.
        if len(vis) == 0:
            discoveryChances = 0
        else:
            # Now to identify where observations meet the timing requirements.
            #  Identify visits where the 'night' changes.
            visSort = np.argsort(ssoObs[self.nightCol])[vis]
            n = np.unique(ssoObs[self.nightCol][visSort])
            # Identify all the indexes where the night changes (swap from one night to next)
            nIdx = np.searchsorted(ssoObs[self.nightCol][visSort], n)
            # Add index pointing to last observation.
            nIdx = np.concatenate([nIdx, np.array([len(visSort)-1])])
            # Find the nights & indexes where there were more than nObsPerNight observations.
            obsPerNight = (nIdx - np.roll(nIdx, 1))[1:]
            nWithXObs = n[np.where(obsPerNight >= self.nObsPerNight)]
            nIdxMany = np.searchsorted(ssoObs[self.nightCol][visSort], nWithXObs)
            nIdxManyEnd = np.searchsorted(ssoObs[self.nightCol][visSort], nWithXObs, side='right') - 1
            # Check that nObsPerNight observations are within tNight
            timesStart = ssoObs[self.expMJDCol][visSort][nIdxMany]
            timesEnd = ssoObs[self.expMJDCol][visSort][nIdxManyEnd]
            # Identify the nights where the total time interval may exceed tNight
            # (but still have a subset of nObsPerNight which are within tNight)
            check = np.where((timesEnd - timesStart > self.tNight) & (nIdxManyEnd + 1 - nIdxMany > self.nObsPerNight))[0]
            bad = []
            for i, j, c in zip(visSort[nIdxMany][check], visSort[nIdxManyEnd][check], check):
                t = ssoObs[self.expMJDCol][i:j+1]
                dtimes = (np.roll(t, 1-nObsPerNight) - t)[:-1]
                if np.all(dtimes > self.tNight+eps):
                    bad.append(c)
            goodIdx = np.delete(visSort[nIdxMany], bad)
            # Now (with indexes of start of 'good' nights with nObsPerNight within tNight),
            # look at the intervals between 'good' nights (for tracks)
            if len(goodIdx) < self.nNightsPerWindow:
                discoveryChances = 0
            else:
                dnights = (np.roll(ssoObs[self.nightCol][goodIdx], 1-self.nNightsPerWindow) - ssoObs[self.nightCol][goodIdx])
                discoveryChances = len(np.where((dnights >= 0) & (dnights <= self.tWindow))[0])
        return discoveryChances


class ActivityOverTimeMetric(BaseMoMetric):
    """
    Count the time periods where we would have a chance to detect activity on
    a moving object.
    Splits observations into time periods set by 'window', then looks for observations within each window,
    and reports what fraction of the total windows receive 'nObs' visits.
    """
    def __init__(self, window, snrLimit=5, surveyYears=10.0, **kwargs):
        super(ActivityOverTimeMetric, self).__init__(**kwargs)
        self.snrLimit = snrLimit
        self.window = window
        self.surveyYears = surveyYears

    def run(self, ssoObs, orb,  Hval):
        # For cometary activity, expect activity at the same point in its orbit at the same time, mostly
        # For collisions, expect activity at random times
        windowBins = np.arange(0, self.surveyYears*365 + window/2.0, window)
        nWindows = len(windowBins)
        try:
            appMag, magLimit, vis, snr = self._prep(ssoObs, orb, Hval)
        except ValueError:
            return 0
        if len(vis) == 0:
            return 0
        else:
            n, b = np.histogram(ssoObs[vis][self.nightCol], bins=windowBins)
            activityWindows = np.where(n>0)[0].size
        return activityWindows / float(nWindows)


class ActivityOverPeriodMetric(BaseMoMetric):
    """
    Count the fraction of the orbit (when split into nBins) that receive
    observations, in order to have a chance to detect activity.
    """
    def __init__(self, window, snrLimit=5, nBins=10,
                 aCol='a', tPeriCol='tPeri', **kwargs):
        super(ActivityOverPeriodMetric, self).__init(**kwargs)
        self.aCol = aCol
        self.tPeriCol = tPeriCol
        self.snrLimit = snrLimit
        self.nBins = nBins

    def run(self, ssoObs, orb, Hval):
        # For cometary activity, expect activity at the same point in its orbit at the same time, mostly
        # For collisions, expect activity at random times
        period = np.power(orb[self.aCol], 3./2.) * 365.25
        anomaly = ((ssoObs[self.expMJDCol] - orb[self.tPeriCol]) / period) % (2*np.pi)
        binsize = 2*np.pi / float(nBins)
        anomalyBins = np.arange(0, 2*np.pi + binsize/2.0, binsize)
        try:
            appMag, magLimit, vis, snr = self._prep(ssoObs, orb, Hval)
        except ValueError:
            return 0
        if len(vis) == 0:
            return 0
        else:
            n, b = np.histogram(anomaly[vis], bins=anomalyBins)
            activityWindows = np.where(n>0)[0].size
        return activityWindows / float(nBins)
