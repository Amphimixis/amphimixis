# Troubleshooting

This page covers common issues and their solutions when using Amphimixis.

## Installation

### `pip install` fails with a Python version error

Amphimixis requires **Python 3.12 or later**. Check your version:

```bash
python3 --version
```

If your system Python is older, install a newer version or use `uv` to manage Python versions:

```bash
uv venv --python 3.12
uv pip install git+https://github.com/Amphimixis/amphimixis.git@stable
```

Or you can install Python 3.12 or newer from your distribution or from python.org, then create a virtual environment and install Amphimixis with `pip`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install git+https://github.com/Amphimixis/amphimixis.git@stable
```

### The `amixis` command is not found after installation

The entry point may not be on your `PATH`. Activate the virtual environment where you installed the package:

```bash
source .venv/bin/activate
amixis --help
```

If you are using `uv`, you can also run `amixis` without activating the environment:

```bash
uv run amixis --help
```

If you installed with `pip install --user`, ensure `~/.local/bin` is on your `PATH`.

## System Dependencies

> **Note:** The commands in this section require root privileges. Run them with `sudo` or as root.

### `perf` command not found

`perf` is part of the Linux kernel tools package. Install it **on each machine** where profiling will run:

- **Debian / Ubuntu:**

```bash
apt install linux-tools-common linux-tools-generic
```

- **Arch Linux:**

```bash
pacman -S perf
```

- **Fedora:**

```bash
dnf install perf
```

### `perf archive` is not available

Some distributions (notably Ubuntu) ship `perf` without `perf archive`. This script is required to resolve build IDs after profiling. Fix it by downloading the script from the Linux kernel repository:

```bash
mkdir -p /usr/libexec/perf-core
curl -s https://raw.githubusercontent.com/torvalds/linux/master/tools/perf/perf-archive.sh > /usr/libexec/perf-core/perf-archive
chmod +x /usr/libexec/perf-core/perf-archive
```

See the [original discussion](https://linux-perf-users.vger.kernel.narkive.com/gjAAds7D/perf-archive-is-not-a-perf-command).

### `rsync` not found on remote machine

`rsync` must be installed **on each machine** referenced in your `input.yml`:

- **Debian / Ubuntu:**

```bash
apt install rsync
```

- **Arch Linux:**

```bash
pacman -S rsync
```

- **Fedora:**

```bash
dnf install rsync
```

### `sshpass` not found

`sshpass` is required only when connecting to remote machines with password authentication. Install it on the machine where you run Amphimixis:

- **Debian / Ubuntu:**

```bash
apt install sshpass
```

- **Arch Linux:**

```bash
pacman -S sshpass
```

- **Fedora:**

```bash
dnf install sshpass
```

If your configuration uses remote machines authenticated with SSH keys instead of passwords, start `ssh-agent` and add your private key **before** running Amphimixis:

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/<your_private_key_name>
```

## Build Failures

### CMake configuration fails

Common causes:

- Missing `CMakeLists.txt` in the project root
- Missing dependencies (libraries, headers) referenced in `CMakeLists.txt`
- Toolchain not available on the build machine

Check the build log in `amphimixis.log` for the exact error.

### Build succeeds but no executable is found

In `builds`, you can optionally specify an `executables` list for each build. Each path must be relative to that build's output directory, for example `bin/my_app`. If `executables` is omitted, Amphimixis profiles the first executable file it finds in the build directory. To ensure the correct binary is profiled, specify it explicitly:

```yaml
builds:
  - build_machine: 1
    run_machine: 1
    recipe_id: 1
    executables:
      - bin/my_app
```

## Configuration Failures

### `input.yml` validation fails

Run the validator to see the exact error:

```bash
amixis validate /path/to/input.yml
```

Common mistakes:

- Missing required fields: `platforms`, `recipes`, `builds` must be non-empty lists
- `build_machine` or `run_machine` references a `platform`:`id` that does not exist
- `recipe_id` references a recipe that does not exist
- `port` outside the valid range (1-65535)

### `build_system` or `runner` was not specified

Amphimixis will auto-detect them from the target project. If the project has a `CMakeLists.txt`, CMake is selected. Else if a `Makefile` is found, Make is used. The runner defaults to Ninja if the build system is CMake.

### `executables` list is duplicated across builds

Use YAML anchors and aliases to avoid duplication:

```yaml
executables: &my_executables
  - bin/my_app
  - tests/my_benchmark

builds:
  - build_machine: 1
    run_machine: 1
    recipe_id: 1
    executables: *my_executables
  - build_machine: 1
    run_machine: 1
    recipe_id: 2
    executables: *my_executables
```

## Profiling Failures

> **Note:** Commands that modify kernel parameters require root privileges. Run them with `sudo` or as root.

### `perf` produces no data or reports "Permission denied"

This can happen if:

- The executable runs too quickly for `perf` to collect meaningful samples
- The perf events specified with `--events` are not supported on the current hardware
- `perf_event_paranoid` is set too high

Check supported events **on the `run_machine`**:

```bash
perf list
```

Lower the paranoid level if needed (requires root). This must be done **on each `run_machine`**.

Temporary change (until next reboot):

```bash
echo '-1' > /proc/sys/kernel/perf_event_paranoid
```

Persistent change (survives reboots, recommended on modern Linux systems): create a configuration file in `/etc/sysctl.d/` and apply it:

```bash
echo 'kernel.perf_event_paranoid = -1' > /etc/sysctl.d/99-amphimixis-perf.conf
sysctl --system
```

### Comparing outputs from different machines

The `amixis compare` command works with `.scriptout` files regardless of which machine they were collected on. Ensure both files use the same perf events for meaningful comparison:

```bash
amixis compare build1.scriptout build2.scriptout --max-rows 10
```
