# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased][unreleased]

### CHANGED
- Renamed python source to `spruce.py` to follow PEP8 recommendations.
- Removed report and clean combo function.
- Restructured arguments to prevent reporting and removal from happening at the same time.
- Refactored to support running individual subreports (e.g. `--packages`, `--scripts`).
- With no arguments, spruce runs as if `--all` had been specified (meaning run all reports).

## [1.0.1] - 2015-05-04 Chihuahua Spruce
### CHANGED
- Just code style updates.

## [0.1.0] - 2015-02-05 Norwegian Spruce
Initial Release.

[unreleased]: https://github.com/sheagcraig/yo/compare/1.0.1...HEAD
[1.0.1]: https://github.com/sheagcraig/auto_logout/compare/0.1.0...1.0.1
