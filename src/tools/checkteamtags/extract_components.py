#!/usr/bin/env python
# Copyright (c) 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Parses OWNERS recursively and generates a machine readable component mapping.

OWNERS files are expected to contain a well-formatted pair of tags as shown
below.  A presubmit check exists that validates this.

This script finds lines in the OWNERS files such as:
  `# TEAM: team@chromium.org` and
  `# COMPONENT: Tools>Test>Findit`
and dumps this information into a json file.

Refer to crbug.com/667952
"""

import json
import optparse
import os
import sys

from owners_file_tags import aggregate_components_from_owners


_DEFAULT_SRC_LOCATION = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir)

_README = """
This file is generated by src/tools/checkteamtags/extract_components.py
by parsing the contents of OWNERS files throughout the chromium source code and
extracting `# TEAM:` and `# COMPONENT:` tags.

Manual edits of this file will be overwritten by an automated process.
""".splitlines()


def write_results(filename, data):
  """Write data to the named file, or the default location."""
  if not filename:
    filename = 'component_map.json'
  with open(filename, 'w') as f:
    f.write(data)


def display_stat(stats, root, options):
  """"Display coverage statistic.

  The following three values are always displayed:
    - The total number of OWNERS files under directory root and its sub-
      directories.
    - The number of OWNERS files (and its percentage of the total) that have
      component information but no team information.
    - The number of OWNERS files (and its percentage of the total) that have
      both component and team information.

  Optionally, if options.stat_coverage or options.complete_coverage are given,
    the same information will be shown for each depth level.
    (up to the level given by options.stat_coverage, if any).

  Args:
    stats (dict): Tha statistics in dictionary form as produced by the
        owners_file_tags module.
    root (str): The root directory from which the depth level is calculated.
    options (optparse.Values): The command line options as returned by
        optparse.
  """
  file_total = stats['OWNERS-count']
  print ("%d OWNERS files in total." % file_total)
  file_with_component = stats['OWNERS-with-component-only-count']
  file_pct_with_component = "N/A"
  if file_total > 0:
    file_pct_with_component = "{0:.2f}".format(
        100.0 * file_with_component / file_total)
  print '%(file_with_component)d (%(file_pct_with_component)s%%) OWNERS '\
        'files have COMPONENT' % {
            'file_with_component': file_with_component,
            'file_pct_with_component': file_pct_with_component}
  file_with_team_component = stats['OWNERS-with-team-and-component-count']
  file_pct_with_team_component = "N/A"
  if file_total > 0:
    file_pct_with_team_component = "{0:.2f}".format(
        100.0 * file_with_team_component / file_total)
  print '%(file_with_team_component)d (%(file_pct_with_team_component)s%%) '\
        'OWNERS files have TEAM and COMPONENT' % {
            'file_with_team_component': file_with_team_component,
            'file_pct_with_team_component': file_pct_with_team_component}

  print ("\nUnder directory %s " % root)
  # number of depth to display, default is max depth under root
  num_output_depth = len(stats['OWNERS-count-by-depth'])
  if (options.stat_coverage > 0
      and options.stat_coverage < num_output_depth):
    num_output_depth = options.stat_coverage

  for depth in range(0, num_output_depth):
    file_total_by_depth = stats['OWNERS-count-by-depth'][depth]
    file_with_component_by_depth =\
    stats['OWNERS-with-component-only-count-by-depth'][depth]
    file_pct_with_component_by_depth = "N/A"
    if file_total_by_depth > 0:
      file_pct_with_component_by_depth = "{0:.2f}".format(
          100.0 * file_with_component_by_depth / file_total_by_depth)
    file_with_team_component_by_depth =\
    stats['OWNERS-with-team-and-component-count-by-depth'][depth]
    file_pct_with_team_component_by_depth = "N/A"
    if file_total_by_depth > 0:
      file_pct_with_team_component_by_depth = "{0:.2f}".format(
          100.0 * file_with_team_component_by_depth / file_total_by_depth)
    print '%(file_total_by_depth)d OWNERS files at depth %(depth)d'% {
        'file_total_by_depth': file_total_by_depth, 'depth': depth}
    print 'have COMPONENT: %(file_with_component_by_depth)d, '\
          'percentage: %(file_pct_with_component_by_depth)s%%' % {
              'file_with_component_by_depth':
              file_with_component_by_depth,
              'file_pct_with_component_by_depth':
              file_pct_with_component_by_depth}
    print 'have COMPONENT and TEAM: %(file_with_team_component_by_depth)d,'\
          'percentage: %(file_pct_with_team_component_by_depth)s%%' % {
              'file_with_team_component_by_depth':
              file_with_team_component_by_depth,
              'file_pct_with_team_component_by_depth':
              file_pct_with_team_component_by_depth}


def main(argv):
  usage = """Usage: python %prog [options] [<root_dir>]
  root_dir  specifies the topmost directory to traverse looking for OWNERS
            files, defaults to two levels up from this file's directory.
            i.e. where src/ is expected to be.

Examples:
  python %prog
  python %prog /b/build/src
  python %prog -v /b/build/src
  python %prog -w /b/build/src
  python %prog -o ~/components.json /b/build/src
  python %prog -c /b/build/src
  python %prog -s 3 /b/build/src
  """
  parser = optparse.OptionParser(usage=usage)
  parser.add_option('-w', '--write', action='store_true',
                    help='If no errors occur, write the mappings to disk.')
  parser.add_option('-v', '--verbose', action='store_true',
                    help='Print warnings.')
  parser.add_option('-f', '--force_print', action='store_true',
                    help='Print the mappings despite errors.')
  parser.add_option('-o', '--output_file', help='Specify file to write the '
                    'mappings to instead of the default: <CWD>/'
                    'component_map.json (implies -w)')
  parser.add_option('-c', '--complete_coverage', action='store_true',
                    help='Print complete coverage statistic')
  parser.add_option('-s', '--stat_coverage', type="int",
                    help='Specify directory depth to display coverage stats')
  options, args = parser.parse_args(argv[1:])
  if args:
    root = args[0]
  else:
    root = _DEFAULT_SRC_LOCATION

  mappings, warnings, errors, stats = aggregate_components_from_owners(root)
  if options.verbose:
    for w in warnings:
      print w

  for e in errors:
    print e

  if options.stat_coverage or options.complete_coverage:
    display_stat(stats, root, options)

  mappings['AAA-README']= _README
  mapping_file_contents = json.dumps(mappings, sort_keys=True, indent=2)
  if options.write or options.output_file:
    if errors:
      print 'Not writing to file due to errors'
      if options.force_print:
        print mapping_file_contents
    else:
      write_results(options.output_file, mapping_file_contents)
  else:
    print mapping_file_contents

  return len(errors)


if __name__ == '__main__':
  sys.exit(main(sys.argv))