![Picea Abies](http://www.imagines-plantarum.de/img/0711907.jpg)

Spruce
=====================
Over time, and, especially with the use of AutoPkg, your JSS has probably
accumlated some cruft: piles of test scripts and out-of-date Chrome updates,
for example. Spruce looks for packages and scripts that have no current
usage in any policies. 

- This information can be simply output to STDOUT
(```--report```).
- You can go ahead and remove all of those unused scripts and
packages (```--report_clean```; prompts prior to package removal and prior to
script removal).
- Or you can take the safer route and redirect the output to a file, e.g.:
```./Spruce --report > output.txt``` ...then edit the file to contain only the
items to remove (vim...)...
- ...then feed that file to Spruce: ```./Spruce
--remove output.txt```

Obviously this is a powerful and dangerous tool. You've been warned!

Setup and Situation
==================
You need a couple of things to get this working:
- [python-jss](https://github.com/sheagcraig/python-jss)
- Either a functioning
  [AutoPkg](https://github.com/autopkg/autopkg)/[JSSImporter](https://github.com/sheagcraig/JSSImporter)
  preferences file, or a [python-jss](https://github.com/sheagcraig/python-jss)
  preferences file.
	- Spruce will try to use the Autopkg preferences first!

Input File Format for ```--remove```
====================================
The file format for the ```--remove``` option is simple:
- One filename (no path) per line
- Lines that start with a '#' (comments), ' ', tab, or newline characters are
  ignored.

Like this:
```
# Packages I need to get rid of:
AdobeFlashPlayer-14.0.0.176.pkg
AdobeFlashPlayer-15.0.0.152.pkg
AdobeFlashPlayer-15.0.0.189.pkg
AdobeFlashPlayer-15.0.0.223.pkg
AdobeFlashPlayer-15.0.0.239.pkg
AdobeFlashPlayer-16.0.0.235.pkg
AdobeFlashPlayer-16.0.0.257.pkg
AdobeFlashPlayer-16.0.0.287.pkg

# Scripts I don't need:
installMERP.sh
kickstart_ard.sh
killPrinters.sh
```
The Future
==========
As I devise more tactics for simplifying, cleaning, and reorganizing, Spruce
will be updated with added functions. Here are some planned features:
- Merge in [Recategorizer](https://github.com/sheagcraig/Recategorizer), since
  it is another organizational tool
- Check for unused static mobile and computer groups, both in lack of
  membership and lack of being scoped.
- Check for unused policies (not scoped).
- Check for unused categories.
- Check for unused icons, although that's currently very involved.
- Check for unused ebooks.
- Check for unused "Apps".
- Check for unused iOS/OSX Configuration Profiles.
- Check for unused Managed Preferences.
- Check for unused Restricted Software.

Happy cleansing!
