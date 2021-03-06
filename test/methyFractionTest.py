import logging
import os
import platform
import unittest
from pbcore.io import CmpH5Reader
from pbcore.deprecated import ReferenceEntry
from kineticsTools.KineticWorker import KineticWorker
from kineticsTools.ipdModel import IpdModel

from test import TestSetup


class TestMethylFraction(TestSetup):

    # We inherit the setup method for test.py.
    # If you need to customize your dataset, we should set up some different conventions
    # def setUp(self):

    def getOpts(self):
        opts = self.basicOpts()
        opts.methylFraction = True
        return opts

    def testSmallDecode(self):
        """
        Test a modification decode around a known modification in lambda
        """

        # First methlyated A in lambda:
        # strand            motif onTarget seqid   tpl
        #      0    GCACNNNNNNGTT       On     1 14983

        start = 14900
        end = 15100
        referenceWindow = (1, start, end)
        bounds = (start, end)

        self.kw._prepForReferenceWindow(referenceWindow)
        kinetics = self.kw._summarizeReferenceRegion(bounds, True, True)
        mods = self.kw._decodePositiveControl(kinetics, bounds)
        print mods

        # Verify that we detect m6A mods at 14982 and 14991
        m6AMods = [x for x in mods if x['modification'] == 'm6A' and x['tpl'] in (14982, 14991)]

        for mod in m6AMods:
            self.assertGreater(mod["frac"], 0.5)


if __name__ == '__main__':
    unittest.main()
