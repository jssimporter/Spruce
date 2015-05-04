#!/usr/bin/python
"""Spruce.py

Find all unused packages and scripts on a JSS and offer to remove them.

Copyright (C) 2015 Shea G Craig <shea.craig@da.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""


import argparse
from distutils.version import StrictVersion
import os.path
import readline  # pylint: disable=unused-import
import sys

# pylint: disable=no-name-in-module
from Foundation import (NSData,
                        NSPropertyListSerialization,
                        NSPropertyListMutableContainers,
                        NSPropertyListXMLFormat_v1_0)
# pylint: enable=no-name-in-module

import jss
# Ensure that python-jss dependency is at minimum version
try:
    from jss import __version__ as PYTHON_JSS_VERSION
except ImportError:
    PYTHON_JSS_VERSION = '0.0.0'

REQUIRED_PYTHON_JSS_VERSION = StrictVersion('0.5.5')


# Globals
# Edit these if you want to change their default values.
AUTOPKG_PREFERENCES = '~/Library/Preferences/com.github.autopkg.plist'
PYTHON_JSS_PREFERENCES = \
    '~/Library/Preferences/com.github.sheagcraig.python-jss.plist'
DESCRIPTION = ("Report on all unused packages and scripts on a JSS. "
               "Optionally, remove them. Use the '--report_clean' "
               "option to report and remove in one go (emergency prompt "
               "included!).\nIf you would like to review and edit the "
               "list, use the '--report' option to output the report "
               "only; then use the '--remove' option with a file "
               "listing those packages and scripts you wish to remove. "
               "Uses configured AutoPkg/JSSImporter settings first; "
               "Then falls back to python-jss settings.")

__version__ = '0.1.0'


class Plist(dict):
    """Abbreviated plist representation (as a dict) with methods for
    reading, writing, and creating blank plists.

    """
    def __init__(self, filename=None):
        """Parses an XML file into a Recipe object."""
        super(Plist, self).__init__()
        self._xml = {}

        if filename:
            self.read_recipe(filename)
        else:
            self.new_plist()

    def __getitem__(self, key):
        return self._xml[key]

    def __setitem__(self, key, value):
        self._xml[key] = value

    def __delitem__(self, key):
        del self._xml[key]

    def __iter__(self):
        return iter(self._xml)

    def __len__(self):
        return len(self._xml)

    def __repr__(self):
        return dict(self._xml).__repr__()

    def __str__(self):
        return dict(self._xml).__str__()

    def read_recipe(self, path):
        """Read a recipe into a dict."""
        path = os.path.expanduser(path)
        if not os.path.isfile(path):
            raise Exception("File does not exist: %s" % path)
        # pylint: disable=unused-variable
        info, pformat, error = \
            NSPropertyListSerialization.propertyListWithData_options_format_error_(
                NSData.dataWithContentsOfFile_(path),
                NSPropertyListMutableContainers,
                None,
                None
            )
        # pylint: enable=unused-variable
        if error:
            raise Exception("Can't read %s: %s" % (path, error))

        self._xml = info

    def write_recipe(self, path):
        """Write a recipe to path."""
        path = os.path.expanduser(path)
        plist_data, error = NSPropertyListSerialization.dataWithPropertyList_format_options_error_(
            self._xml,
            NSPropertyListXMLFormat_v1_0,
            0,
            None
        )
        if error:
            raise Exception(error)
        else:
            if plist_data.writeToFile_atomically_(path, True):
                return
            else:
                raise Exception("Failed writing data to %s" % path)

    def new_plist(self):
        """Generate a barebones recipe plist."""
        pass


def configure_jss(env):
    """Configure a JSS object."""
    repo_url = env["JSS_URL"]
    auth_user = env["API_USERNAME"]
    auth_pass = env["API_PASSWORD"]
    ssl_verify = env.get("JSS_VERIFY_SSL", True)
    suppress_warnings = env.get("JSS_SUPPRESS_WARNINGS", False)
    # No get method for Plist.
    if "JSS_REPOS" in env:
        repos = env["JSS_REPOS"]
    else:
        repos = None
    j = jss.JSS(url=repo_url, user=auth_user, password=auth_pass,
                ssl_verify=ssl_verify, repo_prefs=repos,
                suppress_warnings=suppress_warnings)
    return j


def map_python_jss_env(env):
    """Convert python-jss preferences to JSSImporter preferences."""
    env['JSS_URL'] = env['jss_url']
    env['API_USERNAME'] = env["jss_user"]
    env['API_PASSWORD'] = env["jss_pass"]
    env['JSS_VERIFY_SSL'] = env.get("ssl_verify", True)
    env['JSS_SUPPRESS_WARNINGS'] = env.get("suppress_warnings", False)
    env['JSS_REPOS'] = env.get("repos")

    return env


def remove(j, items):
    """Remove packages and scripts from a JSS as passed in iterable
    'items'.

    """
    for item in items:
        # Remove the JSS Object for item:
        if os.path.splitext(item)[1].upper() in ['.PKG', '.DMG']:
            j.Package(item).delete()
        else:
            # Must be a script.
            j.Script(item).delete()

        # Delete the actual file:
        j.distribution_points.delete(item)
        print "Deleted: %s" % item


def report(j, verbose=False):
    """Populate a set of packages and scripts that are in use, and return
    the difference with a set of all packages and scripts.

    """
    all_policies = j.Policy().retrieve_all()
    all_packages = {package['name'] for package in j.Package()}
    all_scripts = {script['name'] for script in j.Script()}
    used_packages = {package.text for policy in all_policies for
                     package in policy.findall(
                         'package_configuration/packages/package/name')}
    used_scripts = {script.text for policy in all_policies for
                    script in policy.findall('scripts/script/name')}

    unused_packages = all_packages.difference(used_packages)
    unused_scripts = all_scripts.difference(used_scripts)

    results = [("Unused packages", unused_packages),
               ("Unused scripts", unused_scripts)]
    if verbose:
        results.append(("All packages", all_packages))
        results.append(("Used packages", used_packages))
        results.append(("All scripts", all_scripts))
        results.append(("Used scripts", used_scripts))
    for result_set in results:
        output(result_set)

    return (unused_packages, unused_scripts)


def report_clean(j, verbose=False):
    """Populate a set of packages and scripts that are in use, and
    return the difference with a set of all packages and scripts.
    Prompt user to confirm, then remove all unused scripts and
    packages.

    """
    unused_packages, unused_scripts = report(j, verbose)
    response = raw_input('Do you want to remove these unused packages? (Y|N) ')
    if response.upper() == 'Y':
        remove(j, unused_packages)
    else:
        print "Skipping package removal."
    response = raw_input('Do you want to remove these unused scripts? (Y|N) ')
    if response.upper() == 'Y':
        remove(j, unused_scripts)
    else:
        print "Skipping script removal."


def load_file(filename):
    """Given a filename to a file, comprised of a single package or
    script per line, return a list of those objects.

    The file may contain comments and WS. Any line starting with a '#',
    a tab, newline, or a blank space will be ignored.

    """
    with open(os.path.expanduser(filename), 'r') as ifile:
        result_set = [line.rstrip('\n') for line in ifile if not
                      line.startswith((' ', '#', '\t', '\n'))]
    return result_set


def output(data_set):
    """Nicely format and print to STDOUT a heading, followed by data.
    data_set should be a tuple of (heading, set or list data)

    """
    print 10 * '#' + ' %s:' % data_set[0]
    for line in sorted(data_set[1]):
        print line

    print ''


def build_argparser():
    """Create our argument parser."""
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    phelp = ('Include a list of all packages, all scripts, used packages, and '
             'used scripts in the --report ' 'and --report_clean output.')
    parser.add_argument('-v', '--verbose', help=phelp, action='store_true')
    group = parser.add_mutually_exclusive_group(required=True)

    phelp = 'Output unused packages and scripts to STDOUT.'
    group.add_argument('--report', help=phelp, action='store_true')
    group.add_argument('--report_clean', help='Output unused packages and '
                       'scripts. Then, prompt user to remove them all.',
                       action='store_true')

    phelp = ('Remove packages and scripts listed in supplied file. The file '
             'should list one package or script per line (as output by '
             '--report)')
    group.add_argument('--remove', help=phelp)

    return parser


def main():
    """Commandline processing."""
    # Ensure we have the right version of python-jss.
    python_jss_version = StrictVersion(PYTHON_JSS_VERSION)
    if python_jss_version < REQUIRED_PYTHON_JSS_VERSION:
        print ("Requires python-jss version: %s. Installed: %s" %
               (REQUIRED_PYTHON_JSS_VERSION, python_jss_version))
        sys.exit()

    # Handle command line arguments.
    parser = build_argparser()
    args = parser.parse_args()

    # Get AutoPkg configuration settings for JSSImporter, and barring
    # that, get python-jss settings.
    if os.path.exists(os.path.expanduser(AUTOPKG_PREFERENCES)):
        autopkg_env = Plist(AUTOPKG_PREFERENCES)
        j = configure_jss(autopkg_env)
    elif os.path.exists(os.path.expanduser(PYTHON_JSS_PREFERENCES)):
        python_jss_env = map_python_jss_env(Plist(PYTHON_JSS_PREFERENCES))
        j = configure_jss(python_jss_env)
    else:
        raise jss.exceptions.JSSPrefsMissingFileError(
            "No python-jss or AutoPKG/JSSImporter configuration file!")

    if args.report:
        report(j, args.verbose)
    elif args.report_clean:
        report_clean(j, args.verbose)
    elif args.remove:
        removal_set = load_file(args.remove)
        remove(j, removal_set)


if __name__ == '__main__':
    main()
