![Picea Abies](http://www.imagines-plantarum.de/img/0711907.jpg)

# Spruce
Over time, and, especially with the use of AutoPkg, your JSS has probably
accumulated some cruft: piles of test scripts and out-of-date Chrome updates,
for example. Spruce looks for objects on your JSS which have no current usage, are out of date, or are otherwise "crufty".

## Usage
- Simply running Spruce with no arguments like this: `spruce.py` runs _all_ of
  the reports.
- Either individual reports, or a subset of reports can be run by using any combination of report arguments.
	- For example, run the packages and scripts reports: `spruce.py --packages --scripts`
- Reports have a short and a long argument form.
	- Run packages and scripts, the short way: `spruce.py -p -s` or `spruce.py -ps`
- See all of the options:
	- `spruce.py -h`
- Spruce outputs to STDOUT by default. Instead, to seed an XML file for editing and later use in `--remove`, use the `-o` option:
	- `spruce.py --packages --scripts -o CruftyPackagesAndScripts.xml`
- Remove objects by providing a properly formatted XML file to the `--remove` argument:
	- `spruce.py --remove ~/Desktop/StuffIWantCleanedUp.xml`

Obviously this is a powerful and dangerous tool. You've been warned!

## Setup and Situation
You need a couple of things to get this working:
- python-jss 2.0.0 or greater. This is most easily obtained by installing
  [JSSImporter](https://github.com/jssimporter/JSSImporter). The JSSImporter path is added to the
  beginning of the python_path during script execution, so this version will be found first.
- One of the following:
  - A functioning
    [AutoPkg](https://github.com/autopkg/autopkg)/[JSSImporter](https://github.com/jssimporter/JSSImporter)
    preferences file,
  - A [python-jss](https://github.com/jssimporter/python-jss)
    preferences file.
  - Alternatively, use the `--prefs` option to supply a path to a different preferences file.
    This must contain the `JSS_URL`, `API_USERNAME` and `API_PASSWORD` keys in the same format as an AutoPkg preferences file.

Spruce will use file specified in a `--prefs` option first. If none exists, it will try to use the AutoPkg preferences. If they don't exist, it will try to use the `python-jss` preferences.

## XML Input File Format for `--remove`
To remove objects from your JSS, you'll need to create a removal file. This file is a simple XML file which has a list of objects to remove and their ID's. Spruce uses the ID instead of name because some object types (like Computers) allow multiple objects to have the same name.

Don't craft this file completely from scratch! Use Spruce's `-o/--ofile` argument to output your reports to an XML file, and then cut and paste from the various reports into the `Removals` section. For example, `spruce.py --packages --ofile packages_to_remove.xml`
The file format for the ```--remove``` option is simple. For removal purposes, Spruce is expecting to see a element with a tag of `Removals` a child of the root tag. You may only have one `Removals` tag.

The `Removals` tag should contain one child element for each object to be deleted.

Each object to be removed's element should have a tag name corresponding to their type, with capitalization exactly as below:
- `Computer`
- `ComputerGroup`
- `Package`
- `Script`
- `Policy`
- `ComputerConfigurationProfile`
- `MobileDevice`
- `MobileDeviceGroup`
- `MobileDeviceConfigurationProfile`
- `MobileApplication`

The element has a required attributed of `id` that corresponds to the object's JSS ID property. Finally, the element may have text of whatever you like; the XML output of Spruce's reports puts the object's name here.

An example file would look something like this (includes extra metadata from the original reports; you can remove this if you want; it's not used in the removal):
```
<?xml version='1.0' encoding='UTF-8'?>
<SpruceReport>
    <ReportDate>20150831-085912</ReportDate>
    <Server>https://toschestation.org:8443</Server>
    <APIUser>Spruce_User</APIUser>
    <LocalUser>scraig</LocalUser>
    <SpruceVersion>2.0.0</SpruceVersion>
    <python-jssVersion>1.3.0</python-jssVersion>
    <Removals>
            <Package id="891">Atom-1.0.5.pkg</Package>
            <Package id="905">Atom-1.0.7.pkg</Package>
            <Package id="951">Atom-1.0.8.pkg</Package>
            <Package id="953">Atom-1.0.9.pkg</Package>
            <Package id="251">AirServer-5.0.6.pkg</Package>
            <Package id="632">AirServer-5.2.pkg</Package>
            <Package id="693">AirServer-5.3.1.pkg</Package>
            <Package id="739">AirServer-5.3.2.pkg</Package>
    </Removals>
</SpruceReport>
```

## The Future
Development is basically on hold as the original and very capable developer Shea Craig is no longer involved.
Help with further development is very welcome! Some suggestions for improvements:
- Check for unused categories.
- Check for unused icons, although that's currently very involved.
- Check for unused ebooks.
- Check for unused Managed Preferences.
- Check for unused Restricted Software.

Happy cleansing!
