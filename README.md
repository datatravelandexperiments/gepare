# gepare

`gepare` is a small utility to read sets of repositories. It is deliberately
limited and self-contained to make it easier to use to set up bare systems.

## Usage

`gepare` \[[_options_](#options)\] [_configuration_`.toml`](#configuration) ...

## Configuration

Configuration is by TOML file(s).

### Global

`[global]`

Normally contains _name_=_value_ pairs.
These are available in all templates.

Note that since values are expanded lazily, the `global` table can
provide templates for other sections. For example,
```
[global]
dst = '/usr/local/src/{name}'
```
would apply to any package that does not specify a `dst`,
using its own package `name`.

The tool provides predefined names corresponding to XDG directories:
- `CONFIG_HOME`, defaulting to `$HOME/.config`.
- `DATA_HOME`, defaulting to `$HOME/.local/share`.
- `STATE_HOME`, defaulting to `$HOME/.local/state`.
- `CACHE_HOME`, defaulting to `$HOME/.cache`.

### Package

`[package.`_key_`]`

A package describes a remote origin repository (or directory) and its local
location.

Each package table must defines at least the following:

- `src`, the origin (e.g. repository or directory).
- `dst`, the target installation directory.
- `vcs`, the type of origin (**v**ersion **c**ontrol **s**ystem),
  which must be one of `git`, `hg`, or `ln`. As a special case,
  if `src` ends with `.git`, `vcs` can be omitted.
- `load`, which determines how the packages will be used; see
  [Loading](#loading).

In addition, `name` is set by the tool to the value of _key_
if it is not otherwise defined.

### List

`[list.`_type_`]`

A list defines a type of configurable output file.
Each must contain a `file`, the output file name.

It can contain `global` and `package` sub-entries.
The former is included once in the output, and can only refer to global items.
The latter is included once for each package,
and evaluated in the package context.

The `global` and `package` sub-entries can contain:
- `keys`, a list of existing names expanded into the output.
- `items`, a table of name-value pairs expanded into the output.

For lists, each result is written on a line in the output file.

Lists contain information for a package only if it is [loaded.](#loading)

### Structured output

`[output]`

This section defines what the tool prints under the `--json` option.
The purpose of structured output is to allow a separate tool to
handle configured information.

It can contain `global` and `package` sub-entries.
The former is included once in the output, and can only refer to global items.
The latter is included once for each package,
and evaluated in the package context.

The `global` and `package` sub-entries can contain:
- `keys`, a list of existing names expanded into the output.
- `items`, a table of name-value pairs expanded into the output.

For structured output, the global keys
`CONFIG_HOME`, `DATA_HOME`, `STATE_HOME`, and `CACHE_HOME`
are always included, and the package keys
`name`, `src`, `dst`, `vcs`, and `load`
are always included; they do not need to be mentioned explicitly.

Structured output contains package information regardless of its
[loading](#loading) status.

### Loading

The package `load` property determines whether (most) actions apply to
a package. It defaults to `true`, so basic uses don't have to care.

The `load` value can be - Boolean `true` or `false`, a string, or a list
of strings. If it is anything but `false`, then origin actions
(`--refresh`, `--status`, `--bootstrap`) apply to the package.

If the value is a string or list of strings, names [`[list]`](#list)
types that will contain entries for the package.

### Example

The motivating case for `gepare` was managing overlapping sets of packages
for [vim](https://www.vim.org/) and [neovim](http://neovim.io/).

Here, the `list` declarations and package `load` properties
are such that `vim-packages.vim` contains commands to
enable `editorconfig-vim` and `rust-vim`,
while `neo-packages.vim` enables
enable `nvim-lspconfig` and `rust-vim`.

```
[global]
config_dir = '{CONFIG_HOME}/vim'
dst = '{config_dir}/pack/{vcs}/opt/{name}'

[list.neo]
file = '{config_dir}/neo-packages.vim'
package.items.packadd = 'packadd! {name}'

[list.vim]
file = '{config_dir}/vim-packages.vim'
package.items.packadd = 'packadd! {name}'

[package.editorconfig-vim]
load = 'vim'
src = 'https://github.com/editorconfig/editorconfig-vim.git'

[package.nvim-lspconfig]
load = 'neo'
src = 'https://github.com/neovim/nvim-lspconfig.git'

[package.rust-vim]
src = 'https://github.com/rust-lang/rust.vim.git'
```

## Options

#### `--define` _name_ _value_, `-D` _name_ _value_

Define a value, overriding TOML files

### Package selection

#### `--all`, `-a`

Normally, [repository operations](#repository-operations)
apply only to [loaded](#loading) packages.
With `--all`, they apply to all configured packages.

#### `--package` _name_, `-p` _name_

Limit operations to named packages.
This option may be given more than once.

### Repository operations

#### `--bootstrap`, `-b`

Instead of performing any repository operations, this option causes `gepare`
to print shell commands to clone the active packages.

This option can be used to generate a shell script to help set up a new
system, in the case that some of the configured packages themselves
contain package configurations or other dependencies.

#### `--refresh`, `-r`

Clone or update packages.

#### `--status`, `-s`

Report status of packages.

### Lists

#### `--list`, `-l`

Write all configured [list](#list) files.

#### `--list-type` _type_, `-L` _type_

Write only the names [list](#list) files.

### Structured output

#### `--json`, `-j`

Print package information as JSON.
