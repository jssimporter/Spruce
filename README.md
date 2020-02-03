![Spruce 3 - Bruce Lee](http://cbsnews1.cbsistatic.com/hub/i/2014/03/08/2653257f-848f-4e81-8db9-b9a8bfdcd00e/bruce-lee-big-boss-47.jpg)

Spruce 3
========

Spruce is a command line tool that looks for objects on your Jamf Pro server which have no current usage, are out of date, or are otherwise "crufty". It can optionally remove objects from its findings.

Instructions for use
--------------------

**For details on how to use Spruce, please visit our [Wiki](https://github.com/jssimporter/Spruce/wiki).**

**IMPORTANT:**
Spruce 3 requires python-jss 2.1.0 and python3, with the `Foundation` module. The simplest way to achieve this is to install AutoPkg 2.0 and JSSImporter 1.1.0, and then run Spruce using the python that is supplied with AutoPkg:

```
/Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3 ./spruce.py -h
```

Acknowledgements
----------------

Huge thanks to Shea Craig, who wrote the bulk of this work and is still providing advice, though not currently involved in Jamf administration.

The world of Mac administration evolves fast, and continued functionality of Spruce and python-jss requires active engagement from the Jamf-using Mac Admin community. If you think you can help and have ideas, please go ahead and file issues and pull requests, or contact us in the MacAdmins Slack `#jss-importer` channel.


License
-------

See the [LICENSE](https://github.com/grahampugh/Spruce/blob/master/LICENSE.txt) file.
