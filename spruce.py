#!/usr/bin/python
# Copyright (C) 2015-2018 Shea G Craig
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

"""Spruce is a tool to help you clean up your filthy JSS."""


import argparse
from collections import Counter, namedtuple
import datetime
from distutils.version import StrictVersion
from HTMLParser import HTMLParser
import os
import re
import subprocess
import sys
import textwrap
from xml.etree import ElementTree as ET

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
# Requests is installed by python-jss.
import requests

REQUIRED_PYTHON_JSS_VERSION = StrictVersion("1.3.0")


# Globals
# Edit these if you want to change their default values.
AUTOPKG_PREFERENCES = "~/Library/Preferences/com.github.autopkg.plist"
PYTHON_JSS_PREFERENCES = (
    "~/Library/Preferences/com.github.sheagcraig.python-jss.plist")
DESCRIPTION = ("Spruce is a tool to help you clean up your filthy JSS."
               "\n\nUsing the various reporting options, you can see "
               "unused packages, printers, scripts,\ncomputer groups, "
               "configuration profiles, mobile device groups, and "
               "mobile\ndevice configuration profiles.\n\n"
               "Reports are by default output to stdout, and may "
               "optionally be output as\nXML for later use in "
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
__version__ = "2.0.1"


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
    def setup(cls, connection=None):
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
        if not connection:
            connection = {"jss_prefs": jss.JSSPrefs()}
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

    def __init__(self, results, verbose, heading, description=""):
        """Init our data structure.

        Args:
            results: A set of strings of some JSSObject names.
            include_in_non_verbose: Bool whether or not report will be
                included in non-verbose output.
            heading: String heading summarizing the results.
            description: Longer string describing the meaning of the
                results.
        """
        self.results = results
        self.include_in_non_verbose = verbose
        self.heading = heading
        self.description = description

    def __len__(self):
        """Return the length of the results list."""
        return len(self.results)


class Report(object):
    """Represents a collection of Result objects."""

    def __init__(self, obj_type, results, heading, metadata):
        """Init our data structure.

        Args:
            obj_type: String object type name (as returned by
                device_type)
            results: A list of Result objects to include in the
                report.
            heading: String heading describing the report.
            metadata: Dictionary of other data you want to output.
                key: Heading name.
                val Another dictionary, with:
                    key: Subheading name.
                    val: String of data to print.
        """
        self.obj_type = obj_type
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


class AppStoreVersionParser(HTMLParser):
    """Subclasses HTMLParser to scrape current app version number."""

    def __init__(self):
        HTMLParser.__init__(self)
        self.version = "Version Not Found"
        self.in_version_span = False

    def reset(self):
        """Manage data state to know when we are in the version span."""
        HTMLParser.reset(self)
        self.in_version_span = False

    def handle_starttag(self, tag, attrs):
        """Override handling of tags to find version metadata."""
        # <span itemprop="softwareVersion">3.0.3
        attrs_dict = dict(attrs)
        if (tag == "span" and "itemprop" in attrs_dict and
                attrs_dict["itemprop"] == "softwareVersion"):
            self.in_version_span = True

    def handle_data(self, data):
        if self.in_version_span:
            self.version = data
            self.in_version_span = False


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


def build_container_report(containers_with_search_paths, jss_objects):
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
    used_object_sets = []
    for containers, search in containers_with_search_paths:
        used_object_sets.append(
            {(int(obj.findtext("id")), obj.findtext("name"))
             for container in containers
             for obj in container.findall(search)
             if obj.findtext("id") is not None})

    if used_object_sets:
        used = used_object_sets.pop()
        for used_object_set in used_object_sets:
            used = used.union(used_object_set)
    unused = set(jss_objects).difference(used)

    # Use the xpath's second to last part to determine object type.
    obj_type = containers_with_search_paths[0][1].split(
        "/")[-1].replace("_", " ").title()

    all_result = Result(jss_objects, False, "All", "All %ss on the JSS." %
                        obj_type)
    used_result = Result(used, False, "Used")
    unused_result = Result(unused, True, "Unused")
    report = Report(obj_type, [all_result, used_result, unused_result],
                    "", {"Cruftiness": {}})
    cruftiness = calculate_cruft(report.get_result_by_name("Unused").results,
                                 report.get_result_by_name("All").results)
    cruft_strings = get_cruft_strings(cruftiness)

    report.metadata["Cruftiness"] = {"Unscoped %s Cruftiness" % obj_type:
                                     cruft_strings}

    return report


def build_device_report(check_in_period, devices):
    """Build a report of out-of-date or unresponsive devices.

    Finds the newest OS version and looks for devices which are out
    of date. (Builds a histogram of installed OS versions).

    Compiles a list of devices which have not checked in for
    'check_in_period' days.

    Finally, does a report on the hardware models present.

    Args:
        check_in_period: Integer number of days since last check-in to
            include in report. Defaults to 30.
        devices: List of all Computer or MobileDevice objects from the
            JSS. These lists can be subsetted to include only the
            sections needed for this report.

    Returns:
        A Report object.
    """
    check_in_period = validate_check_in_period(check_in_period)
    device_name = device_type(devices)
    report = Report(device_name, [], "%s Report" % device_name,
                    {"Cruftiness": {}})

    # Out of Date results.
    out_of_date_results = get_out_of_date_devices(check_in_period, devices)
    report.results.append(out_of_date_results[0])
    report.metadata["Cruftiness"][
        "%ss Not Checked In Cruftiness" % device_name] = out_of_date_results[1]

    # Orphaned device results.
    orphaned_device_results = get_orphaned_devices(devices)
    report.results.append(orphaned_device_results[0])
    report.metadata["Cruftiness"]["%ss With no Group Membership Cruftiness" %
                                  device_name] = orphaned_device_results[1]

    # Version and model results.
    report.metadata["Version Spread"], report.metadata[
        "Hardware Model Spread"] = get_version_and_model_spread(devices)

    # All Devices
    all_devices = [(device.id, device.name) for device in devices]
    report.results.append(Result(all_devices, False, "All %ss" % device_name))

    return report


def get_out_of_date_devices(check_in_period, devices):
    """Produce a report on devices not checked in since check_in_period.

    Args:
        check_in_period: Number of days to consider out of date.
        devices: List of all Computer or MobileDevice objects on the
            JSS.

    Returns:
        Tuple of (Result object, cruftiness)
    """
    device_name = device_type(devices)
    strptime = datetime.datetime.strptime
    out_of_date = datetime.datetime.now() - datetime.timedelta(check_in_period)
    # Example computer contact time format: 2015-08-06 10:46:51
    # Example mobile device time format:Friday, August 07 2015 at 3:51 PM
    if isinstance(devices[0], jss.Computer):
        fmt_string = "%Y-%m-%d %H:%M:%S"
        check_in = "general/last_contact_time"
    else:
        fmt_string = "%A, %B %d %Y at %H:%M %p"
        check_in = "general/last_inventory_update"
    out_of_date_devices = []
    for device in devices:
        last_contact = device.findtext(check_in)
        # Fix incorrectly formatted Mobile Device times.
        if last_contact and isinstance(device, jss.MobileDevice):
            last_contact = hour_pad(last_contact)
        if not last_contact or (strptime(last_contact, fmt_string) <
                                out_of_date):
            out_of_date_devices.append((device.id, device.name))

    description = ("This report collects %ss which have not checked in for "
                   "more than %i days (%s) based on their %s property." % (
                       device_name, check_in_period, out_of_date,
                       check_in.split("/")[1]))
    out_of_date_report = Result(
        out_of_date_devices, True, "Out of Date %ss" % device_name,
        description)

    out_of_date_cruftiness = calculate_cruft(
        out_of_date_report.results, devices)
    cruftiness = get_cruft_strings(out_of_date_cruftiness)

    return (out_of_date_report, cruftiness)


def get_orphaned_devices(devices):
    """Generate Result of devices with no group memberships.

    Also, include a cruftiness result.

    Args:
        devices: List of all Computer or MobileDevice objects on the
            JSS.

    Returns:
        Tuple of (Result object, cruftiness)
    """
    device_name = device_type(devices)
    orphaned_devices = [(device.id, device.name) for device in devices if
                        has_no_group_membership(device)]
    description = ("This report collects %ss which do not belong to any "
                   "static or smart groups." % device_name)
    orphan_report = Result(orphaned_devices, True,
                           "%ss With no Group Membership" % device_name,
                           description)

    orphan_cruftiness = calculate_cruft(orphan_report.results, devices)
    cruftiness = get_cruft_strings(orphan_cruftiness)

    return (orphan_report, cruftiness)


def device_type(devices):
    """Return a string type name for a list of devices."""
    num_of_types = len({type(device) for device in devices})
    if num_of_types == 1:
        return devices[0].list_type.replace("_", " ").title()
    elif num_of_types == 0:
        return None
    else:
        raise ValueError


def get_version_and_model_spread(devices):
    """Generate version spread metadata for device reports.

    Args:
        devices: List of all Computer or MobileDevice objects on the
            JSS.

    Returns:
        Dictionary appropriate for use in Report.metadata.
    """
    if isinstance(devices[0], jss.Computer):
        os_type_search = "hardware/os_name"
        os_type = "Mac OS X"
        os_version_search = "hardware/os_version"
        model_search = "hardware/model"
        model_identifier_search = "hardware/model_identifier"
    else:
        os_type_search = "general/os_type"
        os_type = "iOS"
        os_version_search = "general/os_version"
        model_search = "general/model"
        model_identifier_search = "general/model_identifier"
    versions, models = [], []

    for device in devices:
        if device.findtext(os_type_search) == os_type:
            versions.append(device.findtext(os_version_search) or
                            "No Version Inventoried")
            models.append("%s / %s" % (
                device.findtext(model_search) or "No Model",
                device.findtext(model_identifier_search,) or
                "No Model Identifier"))
    version_counts = Counter(versions)
    # Standardize version number format.
    version_counts = fix_version_counts(version_counts)
    model_counts = Counter(models)

    total = len(devices)

    # Report on OS version spread
    strings = sorted(get_histogram_strings(version_counts, padding=8))
    version_metadata = {"%s Version Histogram (%s)" % (os_type, total):
                        strings}

    # Report on Model Spread
    # Compare on the model identifier since it is an easy numerical
    # sort.
    strings = sorted(get_histogram_strings(model_counts, padding=8),
                     cmp=model_identifier_cmp)
    model_metadata = {"Hardware Model Histogram (%s)" % total: strings}

    return (version_metadata, model_metadata)


def model_identifier_cmp(model_string_one, model_string_two):
    """Compare model identifier strings.

    Args:
        model_one, model_two: Model string from "modle / model_identifier"
            concatenation. The identifier string is made up of model
            name, numeric major, minor version. e.g. the string
            "iMac Intel (27-inch, Early 2013) / iMac13,3" is compared
            by "iMac", then "13", then "3".

    Returns:
        -1 for less than, 0 for equal, or 1 for greater than.
    """
    # pylint: disable=invalid-name
    VersionIdentifier = namedtuple("VersionIdentifier",
                                   ("model", "major", "minor"))
    # pylint: enable=invalid-name
    model_string_one = model_string_one.split("/")[1].lstrip()
    model_string_two = model_string_two.split("/")[1].lstrip()
    pattern = re.compile(r"(?P<model>\D+)(?P<major>\d+),(?P<minor>\d+)")

    search_one = re.search(pattern, model_string_one)
    if search_one:
        model_one = VersionIdentifier(*search_one.groups())
    else:
        model_one = VersionIdentifier(0, 0, 0)

    search_two = re.search(pattern, model_string_two)
    if search_two:
        model_two = VersionIdentifier(*search_two.groups())
    else:
        model_two = VersionIdentifier(0, 0, 0)

    if model_one.model == model_two.model:
        if model_one.major == model_two.major:
            result = cmp(int(model_one.minor), int(model_two.minor))
        else:
            result = cmp(int(model_one.major), int(model_two.major))
    else:
        result = cmp(model_one.model, model_two.model)

    return result


def build_computers_report(check_in_period, **kwargs):
    """Build a report of out-of-date or unresponsive computers.

    Finds the newest OS version and looks for computers which are out
    of date. (Builds a histogram of installed OS versions).

    Also, compiles a list of computers which have not checked in for
    'check_in_period' days.

    Finally, does a report on the hardware models present.

    Args:
        check_in_period: Integer number of days since last check-in to
            include in report. Defaults to 30.

    Returns:
        A Report object.
    """
    # All report functions support kwargs to support a unified interface,
    # even if they don't use them.
    _ = kwargs
    jss_connection = JSSConnection.get()
    all_computers = jss_connection.Computer().retrieve_all(
        subset=["general", "hardware", "groups_accounts"])

    if all_computers:
        report = build_device_report(check_in_period, all_computers)
    else:
        report = Report("Computer", [], "Computer Report", {})

    return report


def build_mobile_devices_report(check_in_period, **kwargs):
    """Build a report of out-of-date or unresponsive mobile devices.

    Finds the newest OS version and looks for devices which are out
    of date. (Builds a histogram of installed OS versions).

    Also, compiles a list of computers which have not checked in for
    'check_in_period' days.

    Finally, does a report on the hardware models present.

    Args:
        check_in_period: Integer number of days since last check-in to
            include in report. Defaults to 30.

    Returns:
        A Report object.
    """
    # All report functions support kwargs to support a unified interface,
    # even if they don't use them.
    _ = kwargs
    jss_connection = JSSConnection.get()
    mobile_devices = jss_connection.MobileDevice().retrieve_all(
        subset=["general", "mobile_device_groups", "mobiledevicegroups"])

    if mobile_devices:
        report = build_device_report(check_in_period, mobile_devices)
    else:
        report = Report("MobileDevice", [], "Mobile Device Report", {})

    return report


def validate_check_in_period(check_in_period):
    """Ensure check_in_period argument is correct.

    Args:
        check_in_period: Number of days to consider out of date.

    Returns:
        A valid int check-in-period number of days.
    """
    if not check_in_period:
        check_in_period = 30
    if not isinstance(check_in_period, int):
        try:
            check_in_period = int(check_in_period)
        except ValueError:
            print "Incorrect check-in period given. Setting to 30."
            check_in_period = 30

    return check_in_period


def hour_pad(datetime_string):
    """Fix time strings' zero padding.

    JAMF's dates don't always properly zero pad the hour. Do so.

    Args:
        datetime_string: A time string as referenced in MobileDevice's
            last_inventory_time field.

    Returns:
        The string plus any zero padding required.
    """
    # Example mobile device time format:
    # Friday, August 07 2015 at 3:51 PM
    # Monday, February 10 2014 at 8:42 AM<
    components = datetime_string.split()
    if len(components[5]) == 1:
        components[5] = "0" + components[5]
    return " ".join(components)


def build_packages_report(**kwargs):
    """Report on package usage.

    Looks for packages which are not installed by any policies or
    computer configurations.

    Returns:
        A Report object.
    """
    # All report functions support kwargs to support a unified interface,
    # even if they don't use them.
    _ = kwargs
    jss_connection = JSSConnection.get()
    # We have to support the functioning subset and the (hopefully) fixed
    # future subset name.
    all_policies = jss_connection.Policy().retrieve_all(
        subset=["general", "package_configuration", "packages"])
    all_configs = jss_connection.ComputerConfiguration().retrieve_all()
    all_packages = [(pkg.id, pkg.name) for pkg in jss_connection.Package()]
    if not all_packages:
        report = Report("Package", [], "Package Usage Report", {})
    else:
        policy_xpath = "package_configuration/packages/package"
        config_xpath = "packages/package"
        report = build_container_report(
            [(all_policies, policy_xpath), (all_configs, config_xpath)],
            all_packages)
        report.get_result_by_name("Used").description = (
            "All packages which are installed by policies or imaging "
            "configurations.")
        report.get_result_by_name("Unused").description = (
            "All packages which are not installed by any policies or imaging "
            "configurations.")

        report.heading = "Package Usage Report"

    return report


def build_printers_report(**kwargs):
    """Report on printer usage.

    Looks for printers which are not installed by any policies or
    computer configurations.

    Returns:
        A Report object.
    """
    # All report functions support kwargs to support a unified interface,
    # even if they don't use them.
    _ = kwargs
    jss_connection = JSSConnection.get()
    # We have to support the functioning subset and the (hopefully) fixed
    # future subset name.
    all_policies = jss_connection.Policy().retrieve_all(
        subset=["general", "printers"])
    all_configs = jss_connection.ComputerConfiguration().retrieve_all()
    all_printers = [(printer.id, printer.name) for printer in jss_connection.Printer()]
    if not all_printers:
        report = Report("Printer", [], "Printer Usage Report", {})
    else:
        policy_xpath = "printers/printer"
        config_xpath = "printers/printer"
        report = build_container_report(
            [(all_policies, policy_xpath), (all_configs, config_xpath)],
            all_printers)
        report.get_result_by_name("Used").description = (
            "All printers which are installed by policies or imaging "
            "configurations.")
        report.get_result_by_name("Unused").description = (
            "All printers which are not installed by any policies or imaging "
            "configurations.")

        report.heading = "Printer Usage Report"

    return report


def build_scripts_report(**kwargs):
    """Report on script usage.

    Looks for scripts which are not executed by any policies or
    computer configurations.

    Returns:
        A Report object.
    """
    # All report functions support kwargs to support a unified interface,
    # even if they don't use them.
    _ = kwargs
    jss_connection = JSSConnection.get()
    all_policies = jss_connection.Policy().retrieve_all(
        subset=["general", "scripts"])
    all_configs = jss_connection.ComputerConfiguration().retrieve_all()
    all_scripts = [(script.id, script.name) for script in
                   jss_connection.Script()]
    if not all_scripts:
        report = Report("Script", [], "Script Usage Report", {})
    else:
        policy_xpath = "scripts/script"
        config_xpath = "scripts/script"
        report = build_container_report(
            [(all_policies, policy_xpath), (all_configs, config_xpath)],
            all_scripts)
        report.get_result_by_name("Used").description = (
            "All scripts which are installed by policies or imaging "
            "configurations.")
        report.get_result_by_name("Unused").description = (
            "All scripts which are not installed by any policies or imaging "
            "configurations.")

        report.heading = "Script Usage Report"

    return report


def build_group_report(container_searches, groups_names, full_groups):
    """Report on group usage.

    Looks for computer or mobile device groups with no members. This
    does not mean they neccessarily are in-need-of-deletion.

    Args:
        container_searches: List of tuples to be passed to
            build_container_report.
        groups: List of (id, name) tuples for all groups on the JSS.
        full_groups: List of full JSSObject data for groups.

    Returns:
        A Report object.
    """
    obj_type = device_type(full_groups)
    # Build results for groups which aren't scoped.
    report = build_container_report(container_searches, groups_names)

    # More work to be done, since Smart Groups can nest other groups.
    # We want to remove any groups nested (at any level) within a group
    # that is used.

    # For convenience, pull out unused and used sets.
    unused_groups = report.get_result_by_name("Unused").results
    used_groups = report.get_result_by_name("Used").results
    used_full_group_objects = get_full_groups_from_names(used_groups,
                                                         full_groups)

    full_used_nested_groups = get_nested_groups(used_full_group_objects,
                                                full_groups)
    used_nested_groups = get_names_from_full_objects(full_used_nested_groups)

    # Remove the nested groups from the unused list and add to the used.
    unused_groups.difference_update(used_nested_groups)
    # There's no harm in doing a union with the nested used groups vs.
    # adding _just_ the ones removed from unused_groups.
    used_groups.update(used_nested_groups)

    # Recalculate cruftiness
    unused_cruftiness = calculate_cruft(unused_groups, groups_names)
    report.metadata["Cruftiness"][
        "Unscoped %s Cruftiness" % obj_type] = (
            get_cruft_strings(unused_cruftiness))

    # Build Empty Groups Report.
    empty_groups = get_empty_groups(full_groups)
    report.results.append(empty_groups)
    # Calculate empty cruftiness.
    empty_cruftiness = calculate_cruft(empty_groups, groups_names)
    report.metadata["Cruftiness"]["Empty Group Cruftiness"] = (
        get_cruft_strings(empty_cruftiness))

    return report


def build_computer_groups_report(**kwargs):
    """Report on computer groups usage.

    Looks for computer groups with no members. This does not mean
    they neccessarily are in-need-of-deletion.

    Returns:
        A Report object.
    """
    # All report functions support kwargs to support a unified interface,
    # even if they don't use them.
    _ = kwargs
    jss_connection = JSSConnection.get()
    group_list = jss_connection.ComputerGroup()
    if not group_list:
        return Report("ComputerGroup", [], "Computer Group Report", {})

    all_computer_groups = [(group.id, group.name) for group in group_list]
    full_groups = group_list.retrieve_all()

    all_policies = jss_connection.Policy().retrieve_all(
        subset=["general", "scope"])
    all_configs = jss_connection.OSXConfigurationProfile().retrieve_all(
        subset=["general", "scope"])
    scope_xpath = "scope/computer_groups/computer_group"
    scope_exclusions_xpath = (
        "scope/exclusions/computer_groups/computer_group")

    # Build results for groups which aren't scoped.
    report = build_group_report(
        [(all_policies, scope_xpath),
         (all_policies, scope_exclusions_xpath),
         (all_configs, scope_xpath),
         (all_configs, scope_exclusions_xpath)],
        all_computer_groups, full_groups)

    report.heading = "Computer Group Usage Report"
    report.get_result_by_name("Used").description = (
        "All groups which participate in scoping. Computer groups are "
        "considered to be in-use if they are designated in the scope or the "
        "exclusions of a policy or a configuration profile. This report "
        "includes all groups which are nested inside of smart groups using "
        "the 'member_of' criterion.")
    report.get_result_by_name("Unused").description = (
        "All groups which do not participate in scoping. Computer groups are "
        "considered to be in-use if they are designated in the scope or the "
        "exclusions of a policy or a configuration profile. This report "
        "includes all groups which are nested inside of smart groups using "
        "the 'member_of' criterion.")

    return report


def build_device_groups_report(**kwargs):
    """Report on mobile device groups usage.

    Looks for mobile device groups with no members. This does not mean
    they neccessarily are in-need-of-deletion.

    Returns:
        A Report object.
    """
    # All report functions support kwargs to support a unified interface,
    # even if they don't use them.
    _ = kwargs
    jss_connection = JSSConnection.get()
    group_list = jss_connection.MobileDeviceGroup()
    if not group_list:
        return Report("MobileDeviceGroup", [], "Mobile Device Group Report",
                      {})

    all_mobile_device_groups = [(group.id, group.name) for group in group_list]
    full_groups = group_list.retrieve_all()

    all_configs = (
        jss_connection.MobileDeviceConfigurationProfile().retrieve_all(
            subset=["general", "scope"]))
    all_provisioning_profiles = (
        jss_connection.MobileDeviceProvisioningProfile().retrieve_all(
            subset=["general", "scope"]))
    all_apps = (
        jss_connection.MobileDeviceApplication().retrieve_all(
            subset=["general", "scope"]))
    all_ebooks = (
        jss_connection.EBook().retrieve_all(subset=["general", "scope"]))
    xpath = "scope/mobile_device_groups/mobile_device_group"
    exclusion_xpath = (
        "scope/exclusions/mobile_device_groups/mobile_device_group")

    # Build results for groups which aren't scoped.
    report = build_group_report(
        [(all_configs, xpath), (all_configs, exclusion_xpath),
         (all_provisioning_profiles, xpath),
         (all_provisioning_profiles, exclusion_xpath),
         (all_apps, xpath), (all_apps, exclusion_xpath),
         (all_ebooks, xpath), (all_ebooks, exclusion_xpath)],
        all_mobile_device_groups, full_groups)
    report.heading = "Mobile Device Group Usage Report"
    report.get_result_by_name("Used").description = (
        "All groups which participate in scoping. Mobile device groups are "
        "considered to be in-use if they are designated in the scope or the "
        "exclusions of a configuration profile, provisioning profile, app, "
        "or ebook. This report includes all groups which are nested inside "
        "of smart groups using the 'member_of' criterion.")
    report.get_result_by_name("Unused").description = (
        "All groups which do not participate in scoping. Mobile device groups "
        "are considered to be in-use if they are designated in the scope or "
        "the exclusions of a configuration profile, provisioning profile, "
        "app, or ebook. This report includes all groups which are nested "
        "inside of smart groups using the 'member_of' criterion.")

    return report


def build_policies_report(**kwargs):
    """Report on policy usage.

    Looks for policies which are not scoped to anything or are disabled.

    Returns:
        A Report object.
    """
    # All report functions support kwargs to support a unified interface,
    # even if they don't use them.
    _ = kwargs
    jss_connection = JSSConnection.get()
    all_policies = jss_connection.Policy().retrieve_all(
        subset=["general", "scope"])
    if not all_policies:
        return Report("Policy", [], "Policy Usage Report", {})

    all_policies_result = Result([(policy.id, policy.name) for policy in
                                  all_policies], False, "All Policies")
    unscoped_policies = [(policy.id, policy.name) for policy in all_policies if
                         policy.findtext("scope/all_computers") == "false" and
                         not policy.findall("scope/computers/computer") and
                         not policy.findall(
                             "scope/computer_groups/computer_group") and
                         not policy.findall("scope/buildings/building") and
                         not policy.findall("scope/departments/department")]
    desc = ("Policies which are not scoped to any computers, computer groups, "
            "buildings, departments, or to the all_computers meta-scope.")
    unscoped = Result(unscoped_policies, True, "Policies not Scoped", desc)
    unscoped_cruftiness = calculate_cruft(unscoped_policies, all_policies)

    disabled_policies = [(policy.id, policy.name) for policy in all_policies if
                         policy.findtext("general/enabled") == "false"]
    disabled = Result(disabled_policies, True, "Disabled Policies",
                      "Policies which are currently disabled "
                      "(Policy/General/Enabled toggle).")
    disabled_cruftiness = calculate_cruft(disabled_policies, all_policies)

    report = Report("Policy", [unscoped, disabled, all_policies_result],
                    "Policy Report", {"Cruftiness": {}})

    report.metadata["Cruftiness"]["Unscoped Policy Cruftiness"] = (
        get_cruft_strings(unscoped_cruftiness))
    report.metadata["Cruftiness"]["Disabled Policy Cruftiness"] = (
        get_cruft_strings(disabled_cruftiness))

    return report


def build_config_profiles_report(**kwargs):
    """Report on computer configuration profile usage.

    Looks for profiles which are not scoped to anything.

    Returns:
        A Report object.
    """
    # All report functions support kwargs to support a unified interface,
    # even if they don't use them.
    _ = kwargs
    jss_connection = JSSConnection.get()
    all_configs = jss_connection.OSXConfigurationProfile().retrieve_all(
        subset=["general", "scope"])
    if not all_configs:
        return Report("Computer Configuration Profile", [],
                      "Computer Configuration Profile Report", {})

    all_configs_result = Result([(config.id, config.name) for config in
                                 all_configs], False, "All OSX Configuration "
                                "Profiles")

    unscoped_configs = [(config.id, config.name) for config in all_configs if
                        config.findtext("scope/all_computers") == "false" and
                        not config.findall("scope/computers/computer") and
                        not config.findall("scope/computer_groups/"
                                           "computer_group") and
                        not config.findall("scope/buildings/building") and
                        not config.findall("scope/departments/department")]
    desc = ("Computer configuration profiles which are not scoped to any "
            "computers, computer groups, buildings, departments, or to the "
            "all_computers meta-scope.")
    unscoped = Result(unscoped_configs, True,
                      "Computer Configuration Profiles not Scoped", desc)
    unscoped_cruftiness = calculate_cruft(unscoped_configs, all_configs)


    report = Report("Computer Configuration Profile",
                    [unscoped, all_configs_result],
                    "Computer Configuration Profile Report",
                    {"Cruftiness": {}})
    report.metadata["Cruftiness"]["Unscoped Profile Cruftiness"] = (
        get_cruft_strings(unscoped_cruftiness))

    return report


def build_md_config_profiles_report(**kwargs):
    """Report on mobile device configuration profile usage.

    Looks for profiles which are not scoped to anything.

    Returns:
        A Report object.
    """
    # All report functions support kwargs to support a unified interface,
    # even if they don't use them.
    _ = kwargs
    jss_connection = JSSConnection.get()
    all_configs = (
        jss_connection.MobileDeviceConfigurationProfile().retrieve_all(
            subset=["general", "scope"]))
    if not all_configs:
        return Report("Mobile Device Configuration Profile", [],
                      "Mobile Device Configuration Profile Report", {})
    all_configs_result = Result([(config.id, config.name) for config in
                                 all_configs], False, "All iOS Configuration "
                                "Profiles")
    unscoped_configs = [(config.id, config.name) for config in all_configs if
                        config.findtext("scope/all_mobile_devices") ==
                        "false" and not
                        config.findall("scope/mobile_devices/mobile_device")
                        and not config.findall(
                            "scope/mobile_device_groups/mobile_device_group")
                        and not config.findall("scope/jss_users/user") and
                        not config.findall(
                            "scope/jss_user_groups/user_group")
                        and not config.findall("scope/buildings/building") and
                        not config.findall("scope/departments/department")]
    desc = ("Mobile device configuration profiles which are not scoped to any "
            "devices, device groups, users, user groups, buildings, "
            "departments, or to the all_mobile_devices meta-scope.")
    unscoped = Result(unscoped_configs, True,
                      "Mobile Device Configuration Profiles not Scoped", desc)
    unscoped_cruftiness = calculate_cruft(unscoped_configs, all_configs)


    report = Report("Mobile Device Configuration Profile",
                    [unscoped, all_configs_result],
                    "Mobile Device Configuration Profile Report",
                    {"Cruftiness": {}})
    report.metadata["Cruftiness"]["Unscoped Profile Cruftiness"] = (
        get_cruft_strings(unscoped_cruftiness))

    return report


def build_apps_report(**kwargs):
    """Report on out of date and unscoped mobile apps.

    Returns:
        A Report object.
    """
    # All report functions support kwargs to support a unified interface,
    # even if they don't use them.
    _ = kwargs
    jss_connection = JSSConnection.get()
    all_apps = (
        jss_connection.MobileDeviceApplication().retrieve_all(
            subset=["general", "scope"]))
    if not all_apps:
        return Report("Mobile Application", [],
                      "Mobile Device Application Report", {})

    all_apps_result = Result([(app.id, app.name) for app in all_apps], False,
                             "All Mobile Device Applications")
    # Find apps not scoped anywhere.
    unscoped_apps = [(app.id, app.name) for app in all_apps if
                     app.findtext("scope/all_mobile_devices") == "false" and
                     app.findtext("scope/all_jss_users") == "false" and not
                     app.findall("scope/mobile_devices/mobile_device") and
                     not app.findall(
                         "scope/mobile_device_groups/mobile_device_group") and
                     app.findall("scope/jss_users/user") and
                     not app.findall(
                         "scope/jss_user_groups/user_group") and
                     not app.findall("scope/buildings/building") and not
                     app.findall("scope/departments/department")]
    desc = ("Mobile Applications which are not scoped to any "
            "devices, device groups, users, user groups, buildings, "
            "departments, or to the all_mobile_devices or all_jss_users "
            "meta-scopes.")
    unscoped = Result(unscoped_apps, True,
                      "Mobile Device Applications not Scoped", desc)
    unscoped_cruftiness = calculate_cruft(unscoped_apps, all_apps)

    report = Report("Mobile Application", [unscoped, all_apps_result],
                    "Mobile Device Application Report", {"Cruftiness": {}})
    report.metadata["Cruftiness"]["Unscoped App Cruftiness"] = (
        get_cruft_strings(unscoped_cruftiness))

    # Find out-of-date and discontinued apps.
    out_of_date = {}
    discontinued = []
    # Start a requests session.
    session = requests.session()
    for app in all_apps:
        external_url = app.findtext("general/external_url")
        if external_url:
            page = session.get(external_url).text
            version_parser = AppStoreVersionParser()
            version_parser.feed(page)
            current_version = version_parser.version
            if app.findtext("general/version") != current_version:
                out_of_date[app.name] = (app.findtext("general/version"),
                                         current_version)
            if current_version == "Version Not Found":
                discontinued.append((app.id, app.name))

    report.metadata["Out-of-Date Apps"] = {}
    report.metadata["Out-of-Date Apps"]["Out-of-Date Apps"] = (
        get_out_of_date_strings(out_of_date))

    desc = ("Mobile applications which are no longer available from the Apple "
            " App Store.")
    discontinued_result = Result(discontinued, True,
                                 "Apps No Longer Available", desc)
    report.results.append(discontinued_result)

    out_of_date_cruftiness = calculate_cruft(out_of_date, all_apps)
    report.metadata["Cruftiness"]["Out-of-Date App Cruftiness"] = (
        get_cruft_strings(out_of_date_cruftiness))

    discontinued_cruftiness = calculate_cruft(discontinued, all_apps)
    report.metadata["Cruftiness"]["Discontinued App Cruftiness"] = (
        get_cruft_strings(discontinued_cruftiness))

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
        criterion.findtext("name") in ("Computer Group", "Mobile Device Group")
        and criterion.findtext("search_type") == "member of")


def get_full_groups_from_names(groups, full_groups):
    """Given a list a of group names, get the full objects.

    Args:
        groups: A list of names.
        full_groups: A list of all jss.ComputerGroup or
            jss.MobileDeviceGroup objects.

    Returns:
        A list of jss.ComputerGroup or jss.MobileDeviceGroup objects
        corresponding to the names given by the groups argument.
    """
    return [full_group for group in groups for full_group in
            full_groups if full_group.name == group]


def get_names_from_full_objects(objects):
    """Return a list of object names provided list of full objects."""
    return [obj.name for obj in objects]


def get_empty_groups(full_groups):
    """Return all groups with no members as a Result.

    Args:
        full_groups: list of all groups from jss; i.e.
            jss_connection.ComputerGroup().retrieve_all()

    Returns:
        Result object.
    """
    if isinstance(full_groups[0], jss.ComputerGroup):
        obj_type = ("computers", "Computer")
    elif isinstance(full_groups[0], jss.MobileDeviceGroup):
        obj_type = ("mobile_devices", "Mobile Device")
    else:
        raise TypeError("Incorrect group type.")
    groups_with_no_members = {(group.id, group.name) for group in full_groups
                              if group.findtext("%s/size" % obj_type[0]) ==
                              "0"}
    return Result(groups_with_no_members, True,
                  "Empty %s Groups" % obj_type[1],
                  "%s groups which have no members." % obj_type[1])


def has_no_group_membership(device):
    """Test whether a computer or mobile device belongs to any groups.

    This test does not count membership in the default smart groups:
        "All Managed Clients",
        "All Managed Servers",
        "All Managed iPads",
        "All Managed iPhones",
        "All Managed iPod touches"

    Args:
        device: A jss.Computer or jss.MobileDevice object.

    Returns:
        Bool.
    """
    excluded_groups = ("All Managed Clients",
                       "All Managed Servers",
                       "All Managed iPads",
                       "All Managed iPhones",
                       "All Managed iPod touches")
    if isinstance(device, jss.Computer):
        xpath = "groups_accounts/computer_group_memberships/group"
        group_membership = [group.text for group in device.findall(xpath) if
                            not group.text in excluded_groups]
    elif isinstance(device, jss.MobileDevice):
        xpath = "mobile_device_groups/mobile_device_group"
        group_membership = [group.findtext("name") for group in
                            device.findall(xpath) if not group.findtext("name")
                            in excluded_groups]
    else:
        raise TypeError

    if group_membership:
        result = False
    else:
        result = True

    return result


def calculate_cruft(dividend, divisor):
    """Zero-safe find percentage of a subgroup within a larger group."""
    if divisor:
        result = float(len(dividend)) / len(divisor)
    else:
        result = 0.0
    return result


def print_output(report, verbose=False):
    """Print report data.

    Args:
        reports: Report object.
        verbose: Bool, whether to print all results or just unused
            results.
    """
    # Indent is a space and a spruce emoji wide (so 3).
    indent_size = 3 * " "
    forest_length = (64 - len(report.heading)) / 2
    print "%s  %s %s " % (SPRUCE, report.heading, SPRUCE * forest_length)
    if not report.results:
        print "%s  No Results %s" % (SPRUCE, SPRUCE)
    else:
        for result in report.results:
            if not result.include_in_non_verbose and not verbose:
                continue
            else:
                print "\n%s  %s (%i)" % (
                    SPRUCE, result.heading, len(result.results))
                if result.description:
                    print textwrap.fill(result.description,
                                        initial_indent=indent_size,
                                        subsequent_indent=indent_size)
                print
                for line in sorted(result.results,
                                key=lambda s: s[1].upper().strip()):
                    if line[1].strip() == "":
                        text = "(***NO NAME: ID is %s***)" % line[0]
                    else:
                        text = line[1]
                    print "\t%s" % text

        for heading, subsection in report.metadata.iteritems():
            print "\n%s  %s %s" % (SPRUCE, heading, SPRUCE)
            for subheading, strings in subsection.iteritems():
                print "%s  %s" % (SPRUCE, subheading)
                for line in strings:
                    print "\t%s" % line


def get_cruftmoji(percentage):
    """Return one of 10 possible emojis depending on how crufty.

    Args:
        percentage: A float between 0 and 1.

    Returns:
        An emoji string.
    """
    level = [
        # Master
        ("\xf0\x9f\x99\x8f \xf0\x9f\x8d\xbb \xf0\x9f\x8d\x95 \xf0\x9f\x91\xbe"
         "\xf0\x9f\x8d\x95 \xf0\x9f\x8d\xbb \xf0\x9f\x99\x8f"),
        # Snakes on a Plane
        "\xf0\x9f\x90\x8d \xf0\x9f\x90\x8d \xe2\x9c\x88\xef\xb8\x8f",
        # Furry Hat Pizza Party
        "\xf0\x9f\x8d\x95 \xf0\x9f\x92\x82 \xf0\x9f\x8d\x95",
        "\xf0\x9f\x91\xbb", # Ghost
        "\xf0\x9f\x92\xa3", # The Bomb
        "\xf0\x9f\x90\xa9 \xf0\x9f\x92\xa8", # Poodle Fart
        "\xf0\x9f\x92\x80", # Skull
        "\xf0\x9f\x93\xbc", # VHS Cassette
        "\xf0\x9f\x8c\xb5", # Cactus
        "\xf0\x9f\x92\xa9", # Smiling Poo
        "\xf0\x9f\x92\xa9 " * 3] # Smiling Poo (For 100%)
    return level[int(percentage * 10)].decode("utf-8")


def get_cruft_strings(cruft):
    """Generate a list of strings for cruft reports."""
    return ["{:.2%}".format(cruft), "Rank: %s" % get_cruftmoji(cruft)]


def get_terminal_size():
    """Get the size of the terminal window."""
    rows, columns = subprocess.check_output(["stty", "size"]).split()
    return (int(rows), int(columns))


def fix_version_counts(version_counts):
    """Fix too short version names by appending a '.0'.

    Args:
        version_counts: Dict of key: version name val: Count of clients.

    Returns:
        The updated version_counts dict.
    """
    result = {}
    ignored = ("", "No Version Inventoried")
    for version in version_counts:
        if version.count(".") < 2 and version not in ignored:
            updated_version = "%s.0" % version
        else:
            updated_version = version
        result[updated_version] = version_counts[version]

    return result


def get_histogram_strings(data, padding=0, hist_char="\xf0\x9f\x8d\x95"):
    """Generate a horizontal text histogram.

    Given a dictionary of items, generate a list of column aligned,
    padded strings.

    Args:
        data: Dict with
            key: string heading/name
            val: Float between 0 and 1 for histogram value.
        padding: int number of characters to subtract from max bar
            size. Defaults to zero. (If you intend on indenting, the
            indent level should be specified to make sure large bars
            don't overflow the length of the terminal.
        hist_char: Single character string to use as bar fill. Defaults
            to '#'.
    Returns:
        List of strings ready to print.
    """
    max_key_width = max([len(key) for key in data])
    max_val_width = max([len(str(val)) for val in data.values()])
    max_value = max(data.values())
    _, width = get_terminal_size()
    # Find the length we have left for the histogram bars.
    # Magic number 6 is the _():_ parts of the string, and the
    # guaranteed value of one that gets added.
    histogram_width = width - padding - max_key_width - max_val_width - 6
    result = []
    for key, val in data.iteritems():
        preamble = "{:>{max_key}} ({:>{max_val}}): ".format(
            key, val, max_key=max_key_width, max_val=max_val_width)
        #percentage = float(val) / osx_clients
        percentage = float(val) / max_value
        histogram_bar = int(percentage * histogram_width + 1) * hist_char
        result.append((preamble + histogram_bar).decode("utf-8"))
    return result


def get_out_of_date_strings(data):
    """Build a list of strings for data with three items.

    Given a dictionary of items, generate a list of column aligned,
    padded strings.

    Args:
        data: Dict with
            key: string heading/name
            val: 2-Tuple of data to fill in string.

    Returns:
        List of strings ready to print.
    """
    result = []
    if data:
        max_key_width = max([len(key) for key in data])
        max_val1_width = max([len(str(val[0])) for val in data.values()])
        max_val2_width = max([len(str(val[1])) for val in data.values()])
        for key, val in data.iteritems():
            output_string = (u"{:>{max_key}} JSS Version:{:>{max_val1}} App "
                             "Store Version: {:>{max_val2}}".format(
                                 key, val[0], val[1], max_key=max_key_width,
                                 max_val1=max_val1_width,
                                 max_val2=max_val2_width))
            result.append(output_string)
    return result


def add_output_metadata(root):
    """Build the main metadata and tags for an XML report.

    Args:
        root: Element to be used as the root for the report.
    """
    jss_connection = JSSConnection.get()
    report_date = ET.SubElement(root, "ReportDate")
    report_date.text = datetime.datetime.strftime(datetime.datetime.now(),
                                                  "%Y%m%d-%H%M%S")
    report_server = ET.SubElement(root, "Server")
    report_server.text = jss_connection.base_url
    api_user = ET.SubElement(root, "APIUser")
    api_user.text = jss_connection.user
    report_user = ET.SubElement(root, "LocalUser")
    report_user.text = os.getenv("USER")
    spruce_version = ET.SubElement(root, "SpruceVersion")
    spruce_version.text = __version__
    python_jss_version = ET.SubElement(root, "python-jssVersion")
    python_jss_version.text = jss.__version__
    ET.SubElement(root, "Removals")


def add_report_output(root, report):
    """Write the results to an xml file.

    Args:
        results: A Result object.
        ofile: String path to desired output filename.
    """
    report_element = ET.SubElement(root, tagify(report.heading))
    # Results
    for result in report.results:
        if not result.include_in_non_verbose:
            continue
        subreport_element = ET.SubElement(report_element,
                                          tagify(result.heading))
        subreport_element.attrib["length"] = str(len(result))
        desc = ET.SubElement(subreport_element, "Description")
        desc.text = result.description
        for id_, name in sorted(result.results, key=lambda x: x[1]):
            item = ET.SubElement(subreport_element, tagify(report.obj_type))
            item.text = name
            item.attrib["id"] = str(id_)

    # Metadata
    for metadata, val in report.metadata.iteritems():
        metadata_element = ET.SubElement(report_element, tagify(metadata))
        #subreport_element.attrib["length"] = str(len(result))
        for submeta, submeta_val in val.iteritems():
            item = ET.SubElement(metadata_element, tagify(submeta))
            for line in submeta_val:
                value = ET.SubElement(item, "Value")
                #value.text = line.encode("ascii", errors="replace").strip()
                value.text = line.strip()


def tagify(text):
    """Make a string appropriate for XML tag names."""
    if "(" in  text:
        text = text.split("(")[0]
    return text.title().replace(" ", "")


def indent(elem, level=0, more_sibs=False):
    """Indent an xml element object to prepare for pretty printing.

    Method is internal to discourage indenting the self._root
    Element, thus potentially corrupting it.

    """
    i = "\n"
    pad = '    '
    if level:
        i += (level - 1) * pad
    num_kids = len(elem)
    if num_kids:
        if not elem.text or not elem.text.strip():
            elem.text = i + pad
            if level:
                elem.text += pad
        count = 0
        for kid in elem:
            if kid.tag == "data":
                kid.text = "*DATA*"
            indent(kid, level+1, count < num_kids - 1)
            count += 1
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
            if more_sibs:
                elem.tail += pad
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i
            if more_sibs:
                elem.tail += pad


def build_argparser():
    """Create our argument parser."""
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    # Global Args
    phelp = ("Include a list of all objects and used objects in addition to "
             "unused objects in reports.")
    parser.add_argument("-v", "--verbose", help=phelp, action="store_true")
    phelp = ("For computer and mobile device reports, the number of "
             "days since the last check-in to consider device "
             "out-of-date.")
    parser.add_argument("--check_in_period", help=phelp)
    phelp = ("Path to preference file. ")
    parser.add_argument("--prefs", help=phelp)
    # General Reporting Args
    general_group = parser.add_argument_group("General Reporting Arguments")
    phelp = ("Output results to OFILE, in plist format (also usable as "
             "input to the --remove option).")
    general_group.add_argument("-o", "--ofile", help=phelp)
    phelp = ("Generate all reports. With no other arguments, this is "
             "the default.")
    general_group.add_argument("-a", "--all", help=phelp, action="store_true")

    # Computers
    group = parser.add_argument_group("Computer Reporting Arguments")
    phelp = "Generate computer report."
    group.add_argument("-c", "--computers", help=phelp, action="store_true")
    phelp = "Generate unused computer-groups report (Static and Smart)."
    group.add_argument("-g", "--computer_groups", help=phelp,
                       action="store_true")
    phelp = "Generate unused package report."
    group.add_argument("-p", "--packages", help=phelp, action="store_true")
    phelp = "Generate unused printer report."
    group.add_argument("--printers", help=phelp, action="store_true")
    phelp = "Generate unused script report."
    group.add_argument("-s", "--scripts", help=phelp, action="store_true")
    phelp = "Generate unused policy report."
    group.add_argument("-t", "--policies", help=phelp, action="store_true")
    phelp = "Generate unused computer configuration profile report."
    group.add_argument("-u", "--computer_configuration_profiles", help=phelp,
                       action="store_true")

    # Mobile Devices
    md_group = parser.add_argument_group("Mobile Device Reporting Arguments")
    phelp = "Generate mobile device report."
    md_group.add_argument("-d", "--mobile_devices", help=phelp,
                          action="store_true")
    phelp = "Generate unused mobile-device-groups report (Static and Smart)."
    md_group.add_argument("-r", "--mobile_device_groups", help=phelp,
                          action="store_true")
    phelp = "Generate unused mobile-device-profiles report."
    md_group.add_argument("-m", "--mobile_device_configuration_profiles",
                          help=phelp, action="store_true")
    phelp = "Generate out-of-date and unused mobile apps report."
    md_group.add_argument("-b", "--apps",
                          help=phelp, action="store_true")

    # Removal Args
    removal_group = parser.add_argument_group("Removal Arguments")
    phelp = ("Remove all objects specified in supplied XML file REMOVE from "
             "the subelement 'Removals'. If this option is used, all "
             "reporting is skipped. The input file is most easily created by "
             "editing the results of a report done with the -o/--ofile "
             "option.")
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
    # TODO: Roll this data structure into the Reports class.
    reports = {}
    reports["computers"] = {"heading": "Computer Report",
                            "func": build_computers_report,
                            "report": None}
    reports["mobile_devices"] = {"heading": "Mobile Device Report",
                                 "func": build_mobile_devices_report,
                                 "report": None}
    reports["computer_groups"] = {"heading": "Computer Groups Report",
                                  "func": build_computer_groups_report,
                                  "report": None}
    reports["packages"] = {"heading": "Package Report",
                           "func": build_packages_report,
                           "report": None}
    reports["printers"] = {"heading": "Printers Report",
                           "func": build_printers_report,
                           "report": None}
    reports["scripts"] = {"heading": "Scripts Report",
                          "func": build_scripts_report,
                          "report": None}
    reports["policies"] = {"heading": "Policy Report",
                           "func": build_policies_report,
                           "report": None}
    reports["computer_configuration_profiles"] = {
        "heading": "Computer Configuration Profile Report",
        "func": build_config_profiles_report,
        "report": None}

    reports["mobile_device_configuration_profiles"] = {
        "heading": "Mobile Device Configuration Profile Report",
        "func": build_md_config_profiles_report,
        "report": None}
    reports["mobile_device_groups"] = {
        "heading": "Mobile Device Group Report",
        "func": build_device_groups_report,
        "report": None}
    reports["apps"] = {
        "heading": "Mobile Apps",
        "func": build_apps_report,
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
        # TODO: THis is dumb... Just puts the name in so I can later
        # pull it again with dict.
        requested_reports = [report for report in reports]

    # Build the reports
    results = []
    for report_name in requested_reports:
        report_dict = reports[report_name]
        print "%s  Building: %s... %s" % (SPRUCE, report_dict["heading"],
                                          SPRUCE)
        func = reports[report_name]["func"]
        results.append(func(**args_dict))

    # Output the reports
    output_xml = ET.Element("SpruceReport")
    add_output_metadata(output_xml)

    for report in results:
        # Print output to stdout.
        if not args.ofile:
            print
            print_output(report, args.verbose)
        else:
            add_report_output(output_xml, report)

    if args.ofile:
        indent(output_xml)
        tree = ET.ElementTree(output_xml)
        #print ET.tostring(output_xml, encoding="UTF-8")
        try:
            tree.write(os.path.expanduser(args.ofile), encoding="UTF-8",
                    xml_declaration=True)
            print "%s  Wrote output to %s" % (SPRUCE, args.ofile)
        except IOError:
            print "Error writing output to %s" % args.ofile
            sys.exit(1)


def remove(removal_tree):
    """Remove desired objects from the JSS and distribution points.

    Given an XML file with subelement "Removals", remove each child
    object from the JSS. The child Element must have a tag name
    corresponding to the JSSObject class to delete (e.g. "Computer", or
    "Policy"), with an attribute of "id" containing the object's ID.

    The name is not used, as this is not always a guarantor of
    identity.

    Packages and Scripts (when applicable) will be removed from all
    distribution points and servers that support delete methods.

    Args:
        ElementTree instance with Element "Removals", as detailed
        above.
    """
    if not check_with_user():
        sys.exit(0)
    jss_connection = JSSConnection.get()
    # Tag map is a dictionary mapping our Element tags to JSS factory
    # methods.
    tag_map = {"Computer": jss_connection.Computer,
               "ComputerGroup": jss_connection.ComputerGroup,
               "Package": jss_connection.Package,
               "Printer": jss_connection.Printer,
               "Script": jss_connection.Script,
               "Policy": jss_connection.Policy,
               "ComputerConfigurationProfile":
                   jss_connection.OSXConfigurationProfile,
               "MobileDevice": jss_connection.MobileDevice,
               "MobileDeviceGroup": jss_connection.MobileDeviceGroup,
               "MobileDeviceConfigurationProfile":
                   jss_connection.MobileDeviceConfigurationProfile,
               "MobileApplication": jss_connection.MobileDeviceApplication}

    root = removal_tree.getroot()
    removals = root.find("Removals")

    # JDS and CDP distribution points do not require files to be deleted
    # in addition to the objects being deleted (i.e. they handle it).
    # AFP/SMB DP's on the other hand do, so first test to see if any
    # File Share Distribution Points exist.
    if (hasattr(jss_connection.distribution_points, "dp_info") and
            jss_connection.distribution_points.dp_info):

        # See if we are trying to delete any packages or scripts.
        # JSS's which have been migratedd store their scripts in the
        # database, and thus do not need to have them deleted.
        needs_file_removal = ["Package"]
        if not jss_connection.jss_migrated:
            needs_file_removal.append("Script")

        file_type_removals = any([removal.tag for removal in removals if
                                  removal.tag in needs_file_removal])

        if file_type_removals:
            # Mount the shares now in preparation.
            jss_connection.distribution_points.mount()
    else:
        file_type_removals = False

    # Remove duplicate items.
    removals_set = ET.Element("Removals")
    for item in removals:
        if not item.attrib["id"] in [obj.get("id") for obj in
                                     removals_set.findall(item.tag)]:
            removals_set.append(item)

    for item in removals_set:
        # Only try to delete members of the tag_map types.
        search_func = tag_map.get(item.tag)
        if not search_func:
            continue
        else:
            try:
                # Get the item from the JSS.
                obj = search_func(item.attrib["id"])
            except jss.JSSGetError as error:
                # Object probably no longer exists.
                if hasattr(error, "status_code"):
                    print ("%s object %s with ID %s is not available or does "
                           "not exist.\nStatus Code: %s\nError: %s" % (
                               item.tag, item.text, item.attrib["id"],
                               error.status_code, error.message))
                else:
                    print ("%s object %s with ID %s is not available or does "
                           "not exist.\nError: %s" % (
                               item.tag, item.text, item.attrib["id"],
                               error.message))
                continue

        # Try to delete the item.
        try:
            obj.delete()
            print "%s object %s: %s deleted." % (item.tag, obj.id, obj.name)
        except jss.JSSDeleteError as error:
            print ("%s object %s with ID %s failed to delete.\n"
                   "Status Code:%s Error: %s" % (
                       item.tag, item.text, item.attrib["id"],
                       error.status_code, error.message))
            continue

        # If the item is a Package, or a Script on a non-migrated
        # JSS, delete the file from the distribution points.
        if file_type_removals and item.tag in needs_file_removal:
            # The name property of a script or package is called
            # "Display Name" in the gui, and it can differ from the
            # actual filename, so get the filename rather than use name.
            # However, if there is a DistributionServer type repo
            # configured, it tries to delete the db object, which needs
            # "name". Since this has already been done, it's going to
            # throw a JSSGetError regardless. In the event that a user has
            # a Display Name that matches another package's filename, bad
            # things could happen!
            # Get filename, but fall back to name.
            filename = obj.findtext("filename", item.text)
            try:
                jss_connection.distribution_points.delete(filename)
                print "%s file %s deleted." % (item.tag, obj.name)
            except OSError as error:
                print ("Unable to delete %s: %s with error: %s" %
                       (item.tag, filename, error.message))
            except jss.JSSGetError:
                # User has a DistributionServer of some kind and
                # A.) The db object has already been deleted above
                # and possibly also B.) The "Display Name" and
                # "Filename" do not match, and the GET is failing due
                # to no db objects named "Filename" existing.
                pass


def check_with_user():
    jss_connection = JSSConnection.get()
    response = raw_input("Are you sure you want to continue deleting objects "
                         "from %s? (Y or N): " % jss_connection.base_url)
    if response.strip().upper() in ["Y", "YES"]:
        result = True
    else:
        result = False
    return result


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

    # Allow override to prefs file
    if args.prefs:
        if os.path.exists(os.path.expanduser(args.prefs)):
            user_supplied_prefs = Plist(args.prefs)
            connection = map_jssimporter_prefs(user_supplied_prefs)
            print "Preferences used: %s" % args.prefs
    # Otherwise, get AutoPkg configuration settings for JSSImporter,
    # and barring that, get python-jss settings.
    elif os.path.exists(os.path.expanduser(AUTOPKG_PREFERENCES)):
        autopkg_env = Plist(AUTOPKG_PREFERENCES)
        connection = map_jssimporter_prefs(autopkg_env)
    else:
        try:
            connection = jss.JSSPrefs()
        except jss.exceptions.JSSPrefsMissingFileError:
            sys.exit("No python-jss or AutoPKG/JSSImporter configuration "
                     "file!")

    JSSConnection.setup(connection)

    # Determine actions based on supplied arguments.

    # The remove argument is mutually exclusive with the others.
    if args.remove:
        removal_tree = ET.parse(os.path.expanduser(args.remove))
        remove(removal_tree)
    else:
        run_reports(args)


if __name__ == "__main__":
    main()
