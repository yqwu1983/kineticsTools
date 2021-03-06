#!/usr/bin/env python
#################################################################################
# Copyright (c) 2011-2013, Pacific Biosciences of California, Inc.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# * Neither the name of Pacific Biosciences nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE GRANTED BY
# THIS LICENSE.  THIS SOFTWARE IS PROVIDED BY PACIFIC BIOSCIENCES AND ITS
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL PACIFIC BIOSCIENCES OR
# ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
# IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#################################################################################


import cProfile
from itertools import groupby
from pbcore.io import GffReader, Gff3Record
import os
import logging
import sys

from pbcore.util.ToolRunner import PBToolRunner

# Version info...
__version__ = "1.0"


class ModificationSummary(PBToolRunner):

    def __init__(self):
        desc = ['Summarizes kinetic modifications in the alignment_summary.gff file',
                'Notes: For all command-line arguments, default values are listed in [].']
        super(ModificationSummary, self).__init__('\n'.join(desc))

        self.parser.add_argument('--modifications',
                                 dest="modifications",
                                 help='Name of input GFF file [%(default)s]')

        self.parser.add_argument('--alignmentSummary',
                                 dest="alignmentSummary",
                                 help='Name alignment summary file [%(default)s]')

        self.parser.add_argument('--outfile',
                                 dest="outfile",
                                 help='Name of modified alignment summary GFF file [%(default)s]')

    def getVersion(self):
        return __version__

    def validateArgs(self):
        if not os.path.exists(self.args.modifications):
            self.parser.error('input modifications gff file provided does not exist')

        if not os.path.exists(self.args.alignmentSummary):
            self.parser.error('input alignment summary gff file provided does not exist')

    def run(self):
        self.options = self.args

        self.knownModificationEvents = ["modified_base", "m6A", "m4C", "m5C"]

        # Log generously
        logFormat = '%(asctime)s [%(levelname)s] %(message)s'
        logging.basicConfig(level=logging.INFO, format=logFormat)
        stdOutHandler = logging.StreamHandler(sys.stdout)
        logging.Logger.root.addHandler(stdOutHandler)
        logging.info("t1")

        if self.args.profile:
            cProfile.runctx("self._mainLoop()",
                            globals=globals(),
                            locals=locals(),
                            filename="profile.out")

        else:
            return self._mainLoop()

    def countModificationTypes(self, mods):
        mods = sorted(mods, key=lambda x: x["type"])

        counts = dict([(x, 0) for x in self.knownModificationEvents])
        for k, g in groupby(mods, lambda x: x["type"]):
            counts[k] = len(list(g))

        return counts

    def _mainLoop(self):

        # Read in the existing modifications.gff
        modReader = GffReader(self.args.modifications)

        headerString = ",".join(['"' + x + '"' for x in self.knownModificationEvents])

        # Set up some additional headers to be injected
        headers = [
            ('source', 'kineticModificationCaller 1.3.3'),
            ('source-commandline', " ".join(sys.argv)),
            ('attribute-description', 'modsfwd - count of detected DNA modifications on forward strand by modification event type'),
            ('attribute-description', 'modsrev - count of detected DNA modifications on reverse strand by modification event type'),
            ('region-modsfwd', headerString),
            ('region-modsfwd', headerString)
        ]

        hitsByEvent = dict([(x, []) for x in self.knownModificationEvents])

        # Get modification calls
        hits = [{"pos": x.start, "strand": x.strand, "seqid": x.seqid, "type": x.type}
                for x in modReader if x.type in self.knownModificationEvents]

        # Summary reader
        summaryFile = file(self.args.alignmentSummary)

        # Modified gff file
        summaryWriter = file(self.args.outfile, "w")

        self.seqMap = {}
        inHeader = True

        # Loop through
        for line in summaryFile:
            # Pass any metadata line straight through
            if line[0] == "#":

                # Parse headers
                splitFields = line.replace('#', '').split(' ')
                field = splitFields[0]
                value = " ".join(splitFields[1:])
                if field == 'sequence-header':
                    [internalTag, delim, externalTag] = value.strip().partition(' ')
                    self.seqMap[internalTag] = externalTag
                print >>summaryWriter, line.strip()
                continue

            if inHeader:
                # We are at the end of the header -- write the tool-specific headers
                for field in headers:
                    print >>summaryWriter, ("##%s %s" % field)
                inHeader = False

            # Parse the line
            rec = Gff3Record.fromString(line)

            if rec.type == 'region':
                # Get the hits in this interval, add them to the gff record
                intervalHits = [h for h in hits if rec.start <= h['pos'] <= rec.end and rec.seqid == h['seqid']]

                cFwd = self.countModificationTypes([h for h in intervalHits if h['strand'] == '+'])
                cRev = self.countModificationTypes([h for h in intervalHits if h['strand'] == '-'])

                rec.modsfwd = ",".join([str(cFwd[x]) for x in self.knownModificationEvents])
                rec.modsrev = ",".join([str(cRev[x]) for x in self.knownModificationEvents])

                print >>summaryWriter, str(rec)

if __name__ == "__main__":
    kt = ModificationSummary()
    kt.start()
