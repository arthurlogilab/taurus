# Command-Line Tool

Command-line tool is named `bzt` and invoked like `bzt <options> [configs]`. Possible options are:

  - `-h, --help` - show help message and exit
  - `-q, --quiet` - only errors and warnings printed to console
  - `-v, --verbose` - prints all logging messages to console (sometimes _a lot_)
  - `-l LOG, --log=LOG` - change log file location, by default is `bzt.log` in current directory
  - `-d DATADIR, --datadir=DATADIR` - change base directory for the artifact directories, by default it is current directory
  - `-o OPTION, --option=OPTION` override some of config settings from command line, may be used multiple times

## Configuration Files Processing
Taurus tool consumes configuration files as input format (start learning its syntax [here](ConfigSyntax.md)), it automatically detects YAML and JSON formats. Internally, all configuration files are merged into single configuration object (see merged.config artifact), and each following config overrides/appends previous. There are some special config locations that allows having per-machine and per-user configs, that will be loaded for every tool run. In general, configs load sequence is:

  1. `/etc/bzt.d` directory, contains per-machine configs, its contents are first in the configs list
  1. `~/.bzt-rc` file, contained in user's home directory (holds per-user preferences) is added to list after per-machine configs
  1. all command-line passed configs (like `bzt config-1.yml config-2.json`) are added to list after per-user config
  1. all JMX shorthand configs generated and added to list (to support `bzt my-existing.jmx` launching)
  1. all command-line option overrides (like `bzt -o execution.0.scenario=my-test`) are placed into temporary file and added to the end of the list
  1. files list is loaded according to the [merge rules](ConfigSyntax.md#multiple-files-merging-rules)
  1. [aliases](#aliases) applied

Note that per-user config will not be copied into artifact directories, so those files are recommended to put API keys and tokens to improve security. Also it is convenient place to set paths to tools and your favorite preferences.

There is special shorthand for JMeter JMX test plans: if a config filename ends with `.jmx`, an execution for JMeter with existing script will be generated. This allows using Taurus just like `bzt test1.jmx test2.jmx`.

## Command-Line Options Override
 
Any configuration option can be overridden from command line by using `-o`
switch. Like this:
```
bzt stress.json -o modules.jmeter.path=alternate/jmeter/bin/jmeter -o provisioning=remote
```
 
You can even start whole test without config files, just from switches. 
Like this to launch existing JMX with no modifications:
```
bzt -o execution.scenario.jmx=my_plan.jmx
```

Rule for composing the override path is simple: it is built from dictionary keys and array indexes, separated by dot (`.`). If the array index is `-1` then list is appended.

## Aliases

There is a way to create some config chunks and apply them from command-line like this: `bzt -gui-mode -scenario1`
Those aliases then searched in the config, in the section `cli-aliases` and applied over the configuration. Example:

```yaml
---
cli-aliases:
  gui-mode:
    modules:
      jmeter:
        gui: true
  scenario1:
    scenarios:
      my-scen:
        script: jmx2.jmx
```

## Artifacts

Each tool start creates _artifacts directory_ under base dir (see `-d` command-line option). This directory is used to collect all files that were used with execution: configs (except personal), logs, generated scripts and everything else. Some of important artifacts are:
 - `bzt.log` - Taurus log, very detailed, great source for troubleshooting the tool
 - `merged.yml` and `merged.json` - configuration how it looks after merging all user's configuration files into one, saved in two formats
 - `effective.yml` and `effective.json` - configuration how it looks after applying defaults, shorthand rules and any othe modifications during execution, saved in two formats. This is how Taurus sees its configuration instructions and how YAML maps to JSON


## Some Ways to Shoot Your Leg
__Advice 1__: Don't interrupt graceful shutdown after hitting `Ctrl+C` once, let the tool finish its cleanup. The tool is made to be obedient, so if you will insist on interrupting by pressing `Ctrl+C` for the second time, it will exit immediately, leaving background processes unterminated, remote APIs will not be informed of the interrupt and, with little chance, some puppies or kitten might start crying in the world. So let the tool shutdown gracefully, _just be patient, please_.

