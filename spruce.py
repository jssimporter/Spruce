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

"""spruce.py
#TODO: Put usage in.

"""


import argparse
from distutils.version import StrictVersion
import os.path
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
SPRUCE = "\xF0\x9F\x8C\xB2"
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


class Result(object):
    """Encapsulates the metadata and results from a report."""

    def __init__(self, results, verbose, heading):
        """Init our data structure.

        Args:
            results: A set of strings of some JSSObject names.
            include_in_non_verbose: Bool whether or not report will be
                included in non-verbose output.
            heading: String heading describing the results.
        """
        self.results = results
        self.include_in_non_verbose = verbose
        self.heading = heading

    def __len__(self):
        """Return the length of the results list."""
        return len(self.results)


class Report(object):
    """Represents a collection of Result objects."""

    def __init__(self, results, heading, metadata={}):
        """Init our data structure.

        Args:
            results: An iterable of Result objects to include in the
                report.
            heading: String heading describing the report.
            metadata: Dictionary of other data you want to output. Keys
                are titlecased and used for output!
        """
        self.results = results
        self.heading = heading
        self.metadata = metadata

    def get_result_by_name(self, name):
        """Return a result with argument name.

        Args:
            name: String name to find in results.

        Returns:
            A Result object or None.
        """
        found = None
        for result in self.results:
            if result.heading == name:
                found = result
                break
        return found


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


def build_report(containers_with_search_paths, jss_objects):
    """Report on the usage of objects contained in container objects.

    Find the used and unused jss_objects across a list of containing
    JSSContainerObjects.

    For example, Computers can have packages or scripts scoped to
    policies or configurations.

    Args:
        containers_with_search_paths: A list of 2-tuples of:
            ([list of JSSContainerObjects], xpath to search for
            contained objects)
        jss_objects: A list of JSSObject names to search for in
            the containers_with_search_paths.

    Returns:
        A Report object with results and "cruftiness" metadata
        added, but no heading.
    """
    # TODO: Update return docs on all reports (Report object).
    used_object_sets = []
    for containers, search in containers_with_search_paths:
        used_object_sets.append({obj.text for container in containers for obj
                                 in container.findall(search)})

    if used_object_sets:
        used = used_object_sets.pop()
        for used_object_set in used_object_sets:
            used = used.union(used_object_set)
    unused = set(jss_objects).difference(used)

    results = [Result(jss_objects, False, "All"),
               Result(used, False, "Used"),
               Result(unused, True, "Unused")]
    report = Report(results, "")
    cruftiness = calculate_cruft(report.get_result_by_name("Unused").result,
        report.get_result_by_name("All").results)
    report.metadata["cruftiness"] = {"Unscoped Object Cruftiness": cruftiness}

    return report


def build_packages_report():
    """Report on package usage.

    Looks for packages which are not installed by any policies or
    computer configurations.

    Returns:
        A Report object.
    """
    jss_connection = JSSConnection.get()
    all_policies = jss_connection.Policy().retrieve_all()
    all_configs = jss_connection.ComputerConfiguration().retrieve_all()
    all_packages = [package.name for package in jss_connection.Package()]
    policy_xpath = "package_configuration/packages/package/name"
    config_xpath = "packages/package/name"
    report = build_report(
        [(all_policies, policy_xpath), (all_configs, config_xpath)],
        all_packages)

    report.heading = "Package Usage Report"

    return report


def build_scripts_report():
    """Report on script usage.

    Looks for scripts which are not executed by any policies or
    computer configurations.

    Returns:
        A Report object.
    """
    jss_connection = JSSConnection.get()
    all_policies = jss_connection.Policy().retrieve_all()
    all_configs = jss_connection.ComputerConfiguration().retrieve_all()
    all_scripts = [script.name for script in jss_connection.Script()]
    policy_xpath = "scripts/script/name"
    config_xpath = "scripts/script/name"
    report = build_report(
        [(all_policies, policy_xpath), (all_configs, config_xpath)],
        all_scripts)
    report.heading = "Script Usage Report"

    return report


def build_computer_groups_report():
    """Report on computer groups usage.

    Looks for computer groups with no members. This does not mean
    they neccessarily are in-need-of-deletion.

    Returns:
        A 3-item dict consisting of sets of Computer Group names with
        keys:
            all
            policy_used
            config_used
            unused
    """
    jss_connection = JSSConnection.get()
    all_policies = jss_connection.Policy().retrieve_all()
    all_configs = jss_connection.OSXConfigurationProfile().retrieve_all()
    all_computer_groups = [group.name for group in
                           jss_connection.ComputerGroup()]
    policy_xpath = "scope/computer_groups/computer_group/name"
    config_xpath = "scope/computer_groups/computer_group/name"

    # Build results for groups which aren't scoped.
    report = build_report(
        [(all_policies, policy_xpath), (all_configs, config_xpath)],
        all_computer_groups)

    # More work to be done, since Smart Groups can nest other groups.
    # We want to remove any groups nested (at any level) within a group
    # that is used.

    # For convenience, pull out unused and used sets.
    unused_groups = report.get_result_by_name("Unused").results
    used_groups = report.get_result_by_name("Used").results
    full_groups = jss_connection.ComputerGroup().retrieve_all()
    used_full_group_objects = get_full_groups_from_names(used_groups,
                                                         full_groups)

    full_used_nested_groups = get_nested_groups(used_full_group_objects,
                                                full_groups)
    used_nested_groups = get_names_from_full_objects(full_used_nested_groups)

    # TODO: Remove debug lines.
    print "DEBUG: Used nested groups to remove from unused groups (intersect)"
    for g in unused_groups.intersection(used_nested_groups):
        print g
    print ("DEBUG: These are the groups found nested within used "
           "groups (groups to add to used-list).")
    for g in used_nested_groups:
        print g

    # Remove the nested groups from the unused list and add to the used.
    unused_groups.difference_update(used_nested_groups)
    # There's no harm in doing a union with the nested used groups vs.
    # adding _just_ the ones removed from unused_groups.
    used_groups.update(used_nested_groups)

    # TODO: Look for groups with no members as a seperate non-verbose report.
    report.results.append(get_empty_groups(full_groups))

    # Recalculate cruftiness
    cruftiness = calculate_cruft(unused_groups, all_computer_groups)

    report.heading = "Computer Group Usage Report"
    report.metadata["cruftiness"]["Empty Group Cruftiness"] = cruftiness

    return report


def build_policies_report():
    """Report on policy usage.

    Looks for policies which are not scoped to anything or are disabled.

    Returns:
        A Report object.
    """
    jss_connection = JSSConnection.get()
    all_policies = jss_connection.Policy().retrieve_all()
    unscoped_policies = [policy.name for policy in all_policies if
                         policy.findtext("scope/all_computers") == "false" and
                         not policy.findall("scope/computers/computer") and
                         not policy.findall(
                             "scope/computer_groups/computer_group") and
                         not policy.findall("scope/buildings/building") and
                         not policy.findall("scope/departments/department")]
    unscoped = Result(unscoped_policies, True, "Policies not Scoped")
    unscoped_cruftiness = calculate_cruft(unscoped_policies, all_policies)

    disabled_policies = [policy.name for policy in all_policies if
                         policy.findtext("general/enabled") == "false"]
    disabled = Result(disabled_policies, True, "Disabled Policies")
    disabled_cruftiness = calculate_cruft(disabled_policies, all_policies)

    report = Report([unscoped, disabled], "Policy Report",
                    {"cruftiness": {}})
    report.metadata["cruftiness"]["Unscoped Policy Cruftiness"] = (
        unscoped_cruftiness)
    report.metadata["cruftiness"]["Disabled Policy Cruftiness"] = (
        disabled_cruftiness)

    return report


def build_config_profiles_report():
    """Report on computer configuration profile usage.

    Looks for profiles which are not scoped to anything.

    Returns:
        A Report object.
    """
    jss_connection = JSSConnection.get()
    all_configs = jss_connection.OSXConfigurationProfile().retrieve_all()
    unscoped_configs = [config.name for config in all_configs if
                         config.findtext("scope/all_computers") == "false" and
                         not config.findall("scope/computers/computer") and
                         not config.findall(
                             "scope/computer_groups/computer_group") and
                         not config.findall("scope/buildings/building") and
                         not config.findall("scope/departments/department")]
    unscoped = Result(unscoped_configs, True,
                      "Computer Configuration Profiles not Scoped")
    unscoped_cruftiness = calculate_cruft(unscoped_configs, all_configs)


    report = Report([unscoped], "Computer Configuration Profile Report",
                    {"cruftiness": {}})
    report.metadata["cruftiness"]["Unscoped Policy Cruftiness"] = (
        unscoped_cruftiness)

    return report


def get_nested_groups(groups, full_groups):
    """Get all of the groups 'nested' in an iterable of groups.

    A smart group may include other groups with a Computer Group
    criterion. This function will find all of the groups nested within
    a provided iterable of jss.ComputerGroup objects (including nested
    groups that _also_ nest groups).

    Args:
        groups: An iterable of jss.ComputerGroup objects to search
            for nested groups within.
        full_groups: A list of all computer groups. This will hopefully
            be deprecated once a connection caching procedure is
            devised.

    Returns:
        A set of groups nested within the original groups argument.
    """
    results = set()
    for group in groups:
        # Get the names of any nested groups.
        nested_groups_names = get_nested_groups_names(group)
        if nested_groups_names:
            # Function needs full objects, and criteria only specify
            # the name, so we need to "convert" names to full objects.
            nested_groups = get_full_groups_from_names(nested_groups_names,
                                                       full_groups)
            # Add the nested groups to the results.
            results.update(nested_groups)
            # Recursively look for any groups nested in the nested
            # groups.
            results.update(get_nested_groups(nested_groups, full_groups))

        # If no groups are nested, we are done.
    return results


def get_nested_groups_names(group):
    """Get the names of any nested groups in a group, or an empty set.

    Args:
        group: A jss.ComputerGroup object to search for nested groups.

    Returns:
        A tuple of the group names nested in the provided group.
        Returns an empty set if no nested groups are present.
    """
    return (
        criterion.findtext("value")
        for criterion in group.findall("criteria/criterion") if
        criterion.findtext("name") == "Computer Group" and
        criterion.findtext("search_type") == "member of")


def get_full_groups_from_names(groups, full_groups):
    """Given a list a of group names, get the full objects.

    Args:
        groups: A list of names.
        full_groups: A list of all jss.ComputerGroup objects

    Returns:
        A list of jss.ComputerGroup objects corresponding to the names
        given by the groups argument.
    """
    return [full_group for group in groups for full_group in
            full_groups if full_group.name == group]


def get_names_from_full_objects(objects):
    """Return a list of object names provided list of full objects."""
    return [obj.name for obj in objects]


def get_empty_groups(full_groups):
    """TODO"""
    groups_with_no_members = {group.name for group in full_groups if
                              group.findtext("computers/size") == "0"}
    return Result(groups_with_no_members, True, "Empty Computer Groups")


def calculate_cruft(dividend, divisor):
    """Zero-safe find percentage of a subgroup within a larger group."""
    if divisor:
        result = float(len(dividend)) / len(divisor)
    else:
        result = 0.0
    return result


# TODO: Computers
# Should have an argument for how long the last check-in was
# Should have a spread shown for OS version


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


def print_output(report, verbose=False):
    """Print report data.

    Args:
        reports: List of Report objects
        verbose: Bool, whether to print all results or just unused
            results.
    """
    print "%s  %s %s" % (10 * SPRUCE, report.heading, 50 * SPRUCE)
    for result in report.results:
        if not result.include_in_non_verbose and not verbose:
            continue
        else:
            print "\n%s  %s" % (SPRUCE, result.heading)
            for line in sorted(result.results, key=lambda s: s.upper()):
                print line
    # TODO: Handle more metadata, better.
    for metadata in report.metadata:
        print "\n%s  %s  %s" % (SPRUCE, metadata.title(), SPRUCE)
        for key, val in report.metadata[metadata].iteritems():
            print "%s  %s" % (SPRUCE, key.title())
            if type(val) is float:
                print "{:.2%}".format(val)
            else:
                print "{:.2%}".format(val)


def build_argparser():
    """Create our argument parser."""
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    phelp = ("Include a list of all objects and used objects in addition to "
             "unused objects in reports.")
    parser.add_argument("-v", "--verbose", help=phelp, action="store_true")

    group = parser.add_argument_group("Reporting Arguments")
    phelp = ("Output results to OFILE, in plist format (also usable as "
             "input to the --remove option).")
    group.add_argument("-o", "--ofile", help=phelp)
    phelp = ("Generate all reports. With no other arguments, this is "
             "the default.")
    group.add_argument("-a", "--all", help=phelp, action="store_true")
    phelp = "Generate unused package report."
    group.add_argument("-p", "--packages", help=phelp, action="store_true")
    phelp = "Generate unused script report."
    group.add_argument("-s", "--scripts", help=phelp, action="store_true")
    phelp = "Generate unused computer-groups report (Static and Smart)."
    group.add_argument("-g", "--computer_groups", help=phelp,
                        action="store_true")
    phelp = "Generate unused policy report."
    group.add_argument("-t", "--policies", help=phelp,
                        action="store_true")
    phelp = "Generate unused computer configuration profile report."
    group.add_argument("-u", "--computer_configuration_profiles", help=phelp,
                        action="store_true")
    phelp = "Generate unused mobile-device-groups report (Static and Smart)."
    group.add_argument("-r", "--mobile_device_groups", help=phelp,
                        action="store_true")
    phelp = "Generate unused mobile-device-profiles report."
    group.add_argument("-m", "--mobile_device_configuration_profiles",
                        help=phelp, action="store_true")

    removal_group = parser.add_argument_group("Removal Arguments")
    phelp = ("Remove objects specified in supplied plist REMOVE. If "
             "this option is used, all reporting is skipped. The input "
             "file is most easily created by editing the results of a "
             "report with the -o/--ofile option.")
    removal_group.add_argument("--remove", help=phelp)

    return parser


def run_reports(args):
    """Runs reports specified as commandline args to spruce.

    Runs each report specified as a commandline arguement, and outputs
    by default to stdout, or to a plist file specified with -o/--ofile.

    Shows report construction progress, and prints report after all
    data is crunched.

    Args:
        args: parsed argparser namespace object for spruce.
    """
    # Define the types of reports we can accept.
    reports = {}
    reports["packages"] = {"heading": "Package Report",
                           "func": build_packages_report,
                           "report": None}
    reports["scripts"] = {"heading": "Scripts Report",
                          "func": build_scripts_report,
                          "report": None}
    reports["computer_groups"] = {"heading": "Computer Groups Report",
                          "func": build_computer_groups_report,
                          "report": None}
    reports["policies"] = {"heading": "Policy Report",
                          "func": build_policies_report,
                          "report": None}
    reports["computer_configuration_profiles"] = {
        "heading": "Computer Configuration Profile Report",
        "func": build_config_profiles_report,
        "report": None}

    args_dict = vars(args)
    # Build a list of report key names, requested by user, which are
    # tightly coupled, despite the smell, to arg names.
    requested_reports = [report for report in reports if
                         args_dict[report]]

    # If either the --all option has been provided, OR none of the
    # other reports options have been specified, assume user wants all
    # reports (filtering out --remove is handled elsewhere).
    if args.all or not requested_reports:
        # Replace report list with all known report names.
        requested_reports = [report for report in reports]

    # Build the reports
    for report_name in requested_reports:
        report_dict = reports[report_name]
        print "%s  Building: %s..." % (SPRUCE, report_dict["heading"])
        report_dict["report"] = report_dict["func"]()

    # Output the reports
    #for report in [reports[report]["report"] for report in reports if
    #               reports[report]["report"]]:
    for report in requested_reports:
        if reports[report]["report"]:
            report = reports[report]["report"]
            if not args.ofile:
                print
                print_output(report, args.verbose)
            else:
                # write_plist_output(reports)
                pass


def main():
    """Commandline processing."""
    # Ensure we have the right version of python-jss.
    python_jss_version = StrictVersion(PYTHON_JSS_VERSION)
    if python_jss_version < REQUIRED_PYTHON_JSS_VERSION:
        sys.exit("Requires python-jss version: %s. Installed: %s\n"
                 "Please update" % (REQUIRED_PYTHON_JSS_VERSION,
                                    python_jss_version))

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
            sys.exit("No python-jss or AutoPKG/JSSImporter configuration "
                     "file!")

    j = JSSConnection.setup(connection)

    # Determine actions based on supplied arguments.

    # The remove argument is mutually exclusive with the others.
    if args.remove:
        if os.path.exists(os.path.expanduser(args.remove)):
            removal_set = load_removal_file(args.remove)
            remove(j, removal_set)
            # We're done, exit.
            sys.exit()
        else:
            parser.error("Removal file '%s' does not exist." % args.remove)

    else:
        run_reports(args)


if __name__ == "__main__":
    main()
