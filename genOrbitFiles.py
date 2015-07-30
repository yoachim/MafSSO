import numpy as np
import matplotlib.pyplot as plt
from moObs import MoObs
from lsst.sims.maf.db import OpsimDatabase
import os

# Gererate the orbit files for each opsim run

runNames = ['ops2_1094', 'enigma_1257',
            'enigma_1258','enigma_1259','enigma_1189']

useCamera=False

orbitfile = 'pha20141031.des'
moo = MoObs()

dbcols = ['expMJD', 'night', 'fieldRA', 'fieldDec', 'rotSkyPos', 'filter',
          'finSeeing', 'fiveSigmaDepth', 'visitExpTime', 'solarElong']

for runName in runNames:
    print 'Generating orbit file for %s' % runName

    outfileName = runName+'_out.txt'
    moo.runMoObs(orbitfile, outfilename,
                 '/Users/yoachim/Scratch/Opsim_sqlites/'+runName+'_sqlite.db',
                 dbcols=dbcols, useCamera=useCamera)
