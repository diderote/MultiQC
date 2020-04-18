#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" MultiQC module to parse output files from iVar """

from __future__ import print_function
from collections import OrderedDict
import logging
import re

from multiqc import config
from multiqc.plots import bargraph
from multiqc.modules.base_module import BaseMultiqcModule

# Initialise the logger
log = logging.getLogger(__name__)

class MultiqcModule(BaseMultiqcModule):

    def __init__(self):

        # Initialise the parent object
        super(MultiqcModule, self).__init__(
            name = 'ivar',
            anchor = 'ivar',
            href = 'https://github.com/andersen-lab/ivar',
            info = "is a computational package that contains functions broadly useful for viral amplicon-based sequencing."
        )

        # Find and load iVar trim results
        self.ivar_data = dict()
        for f in self.find_log_files('ivar/trim', filehandles=True):
            parsed_data = self.parse_ivar(f)
            if parsed_data is not None and len(parsed_data) > 0:
                self.ivar_data[f['s_name']] = parsed_data
                self.add_data_source(f, f['s_name'])

        # Filter to strip out ignored sample names
        self.ivar_data = self.ignore_samples(self.ivar_data)

        # Warning when no files are found
        if len(self.ivar_data) == 0:
            raise UserWarning

        # Write parsed data to a file
        self.write_data_file(self.ivar_data, 'multiqc_ivar_summary')

        #Found reports or not?
        log.info("Found {} reports".format(len(self.ivar_data)))

        # Basic Stats Table
        self.ivar_general_stats_table()

        #Basic barplot section
        self.add_section(
            description = 'This plot shows primer trimming read categories for iVar, created via ivar trim.',
            plot = self.ivar_metrics_plot()
        )
        
            

    # Parse a ivar report
    def parse_ivar(self, f):
        parsed_data = dict()
        regexes = {
            'total_reads': r'(?:Trimmed primers from )(?:\d+\.\d+\% \()?(\d+)',
            'reads_outside_primer_region': r'^(?:\d+\.\d+\% \()?(\d+)(?:\))?(?:.*[of]?)reads\sstarted',
            'reads_too_short_after_trimming': r'^(?:\d+\.\d+\% \()?(\d+)(?:\))?(?:.*[of]?)reads\swere(?: quality trimmed | shortened)'
        }
        for l in f['f']:
            # Search regexes for stats
            for k, r in regexes.items():
                match = re.search(r, l)
                if match:
                    parsed_data[k] = int(match.group(1))
        
        # Compute properly trimmed from given values
        parsed_data['properly_trimmed'] = (
            parsed_data['total_reads']
                - parsed_data['reads_outside_primer_region']
                - parsed_data['reads_too_short_after_trimming']
        )

        return parsed_data

    # Add to general stats table

    def ivar_general_stats_table(self):
        """ Take the parsed stats from the iVAR report and add it to the
        basic stats table"""

        headers = OrderedDict()
        headers['total_reads'] = {
            'title': 'Total input reads',
            'description': 'Total number of reads where trimming was performed.',
            'min': 0,
            'scale': 'PuRd',
            'format': '{:,.0f}'
        }
        headers['properly_trimmed'] = {
            'title': 'Properly primer trimmed',
            'description': 'Correctly primer trimmed reads',
            'min': 0,
            'scale': 'PuRd',
            'format': '{:,.0f}'
        }
        headers['reads_too_short_after_trimming'] = {
            'title': 'Number of reads too short after trimming',
            'description': 'Number of reads too short (<30bp) after primer trimming',
            'min': 0,
            'scale': 'RdYlGn',
            'format': '{:,.0f}'
        }
        headers['reads_outside_primer_region'] = {
            'title': 'Reads outside primer region',
            'description': 'Number of reads outside the primer region',
            'scale': 'RdYlGn-rev',
            'format': '{:,.0f}'
        }
        self.general_stats_addcols(self.ivar_data, headers)
    
    def ivar_metrics_plot (self):
        """ Make the HighCharts HTML to plot the duplication rates """

        # Specify the order of the different possible categories
        keys = OrderedDict()
        keys['properly_trimmed'] =   { 'name': 'Properly Trimmed' }
        keys['reads_too_short_after_trimming'] = { 'name': 'Too short (<30)' }
        keys['reads_outside_primer_region'] =   { 'name': 'Outside primer region' }

        # Config for the plot
        config = {
            'id': 'ivar_groups',
            'title': 'iVAR: Primer trimming',
            'ylab': '# Reads',
            'cpswitch_counts_label': 'Number of Reads',
            'hide_zero_cats': False
        }

        return bargraph.plot(self.ivar_data, keys, config)
