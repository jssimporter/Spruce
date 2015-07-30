#!/usr/bin/python
# Copyright (C) 2015 Shea G Craig
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Spruce.py

Find all unused packages and scripts on a JSS and offer to remove them.

usage: Spruce.py [-h] [-v] (--report | --report_clean | --remove REMOVE)

Report on all unused packages and scripts on a JSS. Optionally, remove
them.

Use the '--report_clean' option to report and remove in one go
(emergency prompt included!). If you would like to review and edit the
list, use the '-- report' option to output the report only; then use the
'--remove' option with a file listing those packages and scripts you
wish to remove. Uses configured AutoPkg/JSSImporter settings first; Then
falls back to python-jss settings.

optional arguments:
  -h, --help       show this help message and exit
  -v, --verbose    Include a list of all packages, all scripts, used
                   packages, and used scripts in the --report and
                   --report_clean output.
  --report         Output unused packages and scripts to STDOUT.
  --report_clean   Output unused packages and scripts. Then, prompt user
                   to remove them all.
  --remove REMOVE  Remove packages and scripts listed in supplied file.
                   The file should list one package or script per line
                   (as output by --report)
"""


import argparse
from distutils.version import StrictVersion
import os.path
import readline  # pylint: disable=unused-import
import sys

# pylint: disable=no-name-in-module
from Foundation import (NSData,
                        NSPropertyListSerialization,
                        NSPropertyListMutableContainersAndLeaves,
                        NSPropertyListXMLFormat_v1_0)
# pylint: enable=no-name-in-module

import jss
# Ensure that python-jss dependency is at minimum version.
try:
    from jss import __version__ as PYTHON_JSS_VERSION
except ImportError:
    PYTHON_JSS_VERSION = "0.0.0"

REQUIRED_PYTHON_JSS_VERSION = StrictVersion("1.2.1")


# Globals
# Edit these if you want to change their default values.
AUTOPKG_PREFERENCES = "~/Library/Preferences/com.github.autopkg.plist"
PYTHON_JSS_PREFERENCES = (
    "~/Library/Preferences/com.github.sheagcraig.python-jss.plist")
DESCRIPTION = ("Spruce is a tool to help you clean up your filthy JSS."
               "\n\nUsing the various reporting options, you can see "
               "unused packages, scripts,\ncomputer groups, "
               "configuration profiles, mobile device groups, and "
               "mobile\ndevice configuration profiles.\n\n"
               "Reports are by default output to stdout, and may "
               "optionally be output as\na plist for later use in "
               "automated removal.\n\n"
               "Spruce uses configured AutoPkg/JSSImporter settings "
               "first. If those are\nmissing, Spruce falls back to "
               "python-jss settings.\n\nThe recommended workflow is to "
               "begin by running the reports you find\ninteresting. "
               "After becoming familiar with the scale of unused "
               "things,\nreports can be output with the -o/--ofile "
               "option. This file can then be\nedited down to include "
               "only those things which you wish to remove.\nFinally, "
               "pass this filename as an option to the --remove "
               "argument to\nremove the specified objects.")

__version__ = "1.1.0"


class Error(Exception):
    """Module base exception."""
    pass


class PlistParseError(Error):
    """Error parsing a plist file."""
    pass


class PlistDataError(Error):
    """Data can not be serialized to plist."""
    pass


class PlistWriteError(Error):
    """Error writing a plist file."""
    pass


class Plist(dict):
    """Abbreviated plist representation (as a dict)."""

    def __init__(self, filename=None):
        """Init a Plist, optionally from parsing an existing file.

        Args:
            filename: String path to a plist file.
        """
        if filename:
            dict.__init__(self, self.read_file(filename))
        else:
            dict.__init__(self)
            self.new_plist()

    def read_file(self, path):
        """Replace internal XML dict with data from plist at path.

        Args:
            path: String path to a plist file.

        Raises:
            PlistParseError: Error in reading plist file.
        """
        # pylint: disable=unused-variable
        info, pformat, error = (
            NSPropertyListSerialization.propertyListWithData_options_format_error_(
                NSData.dataWithContentsOfFile_(os.path.expanduser(path)),
                NSPropertyListMutableContainersAndLeaves,
                None,
                None
            ))
        # pylint: enable=unused-variable
        if info is None:
            if error is None:
                error = "Invalid plist file."
            raise PlistParseError("Can't read %s: %s" % (path, error))

        return info

    def write_plist(self, path):
        """Write plist to path.

        Args:
            path: String path to desired plist file.

        Raises:
            PlistDataError: There was an error in the data.
            PlistWriteError: Plist could not be written.
        """
        plist_data, error = NSPropertyListSerialization.dataWithPropertyList_format_options_error_(
            self,
            NSPropertyListXMLFormat_v1_0,
            0,
            None)
        if plist_data is None:
            if error is None:
                error = "Failed to serialize data to plist."
            raise PlistDataError(error)
        else:
            if not plist_data.writeToFile_atomically_(
                    os.path.expanduser(path), True):
                raise PlistWriteError("Failed writing data to %s" % path)

    def new_plist(self):
        """Generate a barebones recipe plist."""
        # Not implemented at this time.
        pass


class JSSConnection(object):
    """Class for providing a single JSS connection."""
    _jss_prefs = None
    _jss = None

    @classmethod
    def setup(cls, connection={"jss_prefs": jss.JSSPrefs()}):
        """Set up the jss connection class variable.

        If no connection argument is provided, setup will use the
        standard JSSPrefs preferences
        (com.github.sheagcraig.python-jss).

        Args:
            connection: Dictionary with JSS connection info, keys:
                jss_prefs: String path to a preference file.
                url: Path with port to a JSS.
                user: API Username.
                password: API Password.
                repo_prefs: A list of dicts with repository names and
                    passwords. See JSSPrefs.
                ssl_verify: Boolean indicating whether to verify SSL
                    certificates.  Defaults to True.
                verbose: Boolean indicating the level of logging.
                    (Doesn't do much.)
                jss_migrated: Boolean indicating whether scripts have
                    been migrated to the database. Used for determining
                    copy_script type.
                suppress_warnings:
                    Turns off the urllib3 warnings. Remember, these
                    warnings are there for a reason! Use at your own
                    risk.
        """
        cls._jss_prefs = connection
        if isinstance(connection, jss.JSSPrefs):
            cls._jss = jss.JSS(jss_prefs=cls._jss_prefs)
        else:
            cls._jss = jss.JSS(**cls._jss_prefs)

    @classmethod
    def get(cls):
        """Return the shared JSS object."""
        if not cls._jss:
            cls.setup()
        return cls._jss


def map_jssimporter_prefs(prefs):
    """Convert python-jss preferences to JSSImporter preferences."""
    connection = {}
    connection["url"] = prefs["JSS_URL"]
    connection["user"] = prefs["API_USERNAME"]
    connection["password"] = prefs["API_PASSWORD"]
    connection["ssl_verify"] = prefs.get("JSS_VERIFY_SSL", True)
    connection["suppress_warnings"] = prefs.get("JSS_SUPPRESS_WARNINGS", True)
    connection["jss_migrated"] = prefs.get("JSS_MIGRATED", True)
    connection["repo_prefs"] = prefs.get("JSS_REPOS")

    return connection


def remove(j, items):
    """Remove packages and scripts from a JSS.

    Args:
        items: Iterable of string object names to remove. May be a
            package or a script.
    """
    pass
    #for item in items:
    #    # Remove the JSS Object for item:
    #    if os.path.splitext(item)[1].upper() in [".PKG", ".DMG"]:
    #        j.Package(item).delete()
    #    else:
    #        # Must be a script.
    #        j.Script(item).delete()

    #    # Delete the actual file:
    #    j.distribution_points.delete(item)
    #    print "Deleted: %s" % item


def build_computer_scoped_report(jss_objects, policy_xpath, config_xpath):
    """Report on objects used in computer scoping-objects.

    Computers can have packages or scripts scoped to policies or
    configurations.

    Args:
        jss_objects: A list of JSSObject names to find in policies
            and computer imaging configurations.
        policy_xpath: Strong xpath to the nested object's name in a
            policy.
        config_xpath: Strong xpath to the nested object's name in a
            computer imaging configuration.

    Returns:
        A 3-item dict consisting of sets of search-object names with keys:
            all
            policy_used
            config_used
            unused
    """
    jss_connection = JSSConnection.get()
    all_policies = jss_connection.Policy().retrieve_all()
    all_configurations = jss_connection.ComputerConfiguration().retrieve_all()

    objs_used_in_policies = {obj.text for policy in all_policies for obj in
                             policy.findall(policy_xpath)}
    objs_used_in_configs = {obj.text for config in all_configurations for obj
                            in config.findall(config_xpath)}

    used = objs_used_in_policies.union(objs_used_in_configs)
    unused = set(jss_objects).difference(used)

    #TODO: The returns needn't be sets.
    results = {"all": jss_objects,
               "policy_used": objs_used_in_policies,
               "config_used": objs_used_in_configs,
               "unused": unused}
    #if verbose:
    #    results.append(("All packages", all_packages))
    #    results.append(("Used packages", used_packages))
    #    results.append(("All scripts", all_scripts))
    #    results.append(("Used scripts", used_scripts))
    #for result_set in results:
    #    output(result_set)

    return results


def build_packages_report():
    """Report on package usage.

    Returns:
        A 3-item dict consisting of sets of Package names with keys:
            all
            policy_used
            config_used
            unused
    """
    jss_connection = JSSConnection.get()
    all_packages = [package.name for package in jss_connection.Package()]
    policy_xpath = "package_configuration/packages/package/name"
    config_xpath = "packages/package/name"
    results = build_computer_scoped_report(all_packages, policy_xpath,
                                           config_xpath)

    return results


def build_scripts_report():
    """Report on script usage.

    Returns:
        A 3-item dict consisting of sets of Script names with keys:
            all
            policy_used
            config_used
            unused
    """
    jss_connection = JSSConnection.get()
    all_scripts = [script.name for script in jss_connection.Script()]
    policy_xpath = "scripts/script/name"
    config_xpath = "scripts/script/name"
    results = build_computer_scoped_report(all_scripts, policy_xpath,
                                           config_xpath)

    return results


def load_removal_file(filename):
    """Get a set of files to remove from a file.

    Args:
        filename: String path to a plaintext file, comprised of a
            single package or script filename per line.

            The file may contain comments and WS. Any line starting
            with a '#', a tab, newline, or a blank space will be
            ignored.

    Returns:
        A set of the files and scripts to remove.
    """
    with open(os.path.expanduser(filename), "r") as ifile:
        result_set = [line.rstrip("\n") for line in ifile if not
                      line.startswith((" ", "#", "\t", "\n"))]
    return result_set


def output(data_set):
    """Print a heading and report data.

    Args:
        data_set: Tuple of (heading, set or list data)
    """
    print 10 * "#" + " %s:" % data_set[0]
    for line in sorted(data_set[1], key=lambda s: s.upper()):
        print line

    print


def build_argparser():
    """Create our argument parser."""
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    phelp = ("Include a list of all objects and used objects in addition to "
             "unused objects in reports.")
    parser.add_argument("-v", "--verbose", help=phelp, action="store_true")

    phelp = ("Output results to OFILE, in plist format (also usable as "
             "input to the --remove option).")
    parser.add_argument("-o", "--ofile", help=phelp)
    phelp = ("Generate all reports. With no other arguments, this is "
             "the default.")
    parser.add_argument("-a", "--all", help=phelp, action="store_true")
    phelp = "Generate unused package report."
    parser.add_argument("-p", "--packages", help=phelp, action="store_true")
    phelp = "Generate unused script report."
    parser.add_argument("-s", "--scripts", help=phelp, action="store_true")
    phelp = "Generate unused computer-groups report (Static and Smart)."
    parser.add_argument("-g", "--computer_groups", help=phelp,
                        action="store_true")
    phelp = "Generate unused mobile-device-groups report (Static and Smart)."
    parser.add_argument("-r", "--mobile_device_groups", help=phelp,
                        action="store_true")
    phelp = "Generate unused configuration-profiles report."
    parser.add_argument("-c", "--configuration_profiles", help=phelp,
                        action="store_true")
    phelp = "Generate unused mobile-device-profiles report."
    parser.add_argument("-m", "--mobile_device_configuration_profiles",
                        help=phelp, action="store_true")

    phelp = ("Remove objects specified in supplied plist REMOVE. If "
             "this option is used, all reporting is skipped. The input "
             "file is most easily created by editing the results of a "
             "report with the -o/--ofile option.")
    parser.add_argument("--remove", help=phelp)

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
        connection = map_jssimporter_prefs(autopkg_env)
    else:
        try:
            connection = jss.JSSPrefs()
        except jss.exceptions.JSSPrefsMissingFileError:
            print "No python-jss or AutoPKG/JSSImporter configuration file!"

    j = JSSConnection.setup(connection)

    # Determine actions based on supplied arguments.
    # If all has been set, or if no other args, assume a full report is
    # desired.
    if args.all or not any(vars(args).values()):
        # Run all of the reports.
        results = []
        all_reports = (build_packages_report, build_scripts_report)

        for report in all_reports:
            results.append(report())

    if args.remove:
        if os.path.exists(os.path.expanduser(args.remove)):
            removal_set = load_removal_file(args.remove)
            remove(j, removal_set)
        else:
            sys.exit("Removal file '%s' does not exist." % args.remove)

    #if args.
    #elif args.report:
    #    report(j, args.verbose)
    #elif args.report_clean:
    #    report_clean(j, args.verbose)


if __name__ == "__main__":
    main()
