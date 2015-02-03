JSSUnusedFilesCleaner
=====================
Over time, and especially with the use of AutoPkg, your JSS has probably accumlated some cruft. The JSSUnusedFilesCleaner looks for packages and scripts that have no current usage in any policies. This information can be simply output to STDOUT (```--report```). You can go ahead and remove all of those unused scripts and packages (```--report_clean```; prompts prior to package removal and prior to script removal).

Or you can take the safer route and redirect the output to a file, e.g.:
```./JSSUnusedFilesCleaner --report > output.txt```
...then edit the file to contain only the items to remove (vim...), then feed that file to the JSSUnusedFilesCleaner:
```./JSSUnusedFilesCleaner --remove output.txt```

Obviously this is a powerful and dangerous tool. You've been warned!

Setup and Situation
==================
You need a couple of things to get this working:
- [python-jss](https://github.com/sheagcraig/python-jss)
- Either a functioning [AutoPkg](https://github.com/autopkg/autopkg)/[JSSImporter](https://github.com/sheagcraig/JSSImporter) preferences file, or a [python-jss](https://github.com/sheagcraig/python-jss) preferences file.
	- JSSUnusedFilesCleaner will try to use the Autopkg preferences first!

Depending on your JSS, this may not be as useful as it initially seems. If you are using a JDS, there is no support in python-jss yet for deleting a package, so JSSUnusedFilesCleaner won't be able to remove unused packages (scripts should still work). And there's just no support for CDP's yet.

The file format for the ```--remove``` option is simple:
- One filename (no path) per line
- Lines that start with a '#' (comments), ' ', tab, or newline characters are ignored.

Happy cleansing!