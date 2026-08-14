# Configuration file guide

This guide explains how to create and configure your project’s configuration file.

See an example configuration file [here](./input.yml).

## General structure

The YAML configuration file consists of the following **top-level fields**:

|                     Field                     |         Type         | Description                                                          |
| :-------------------------------------------: | :------------------: | -------------------------------------------------------------------- |
| build_system[^1] |        string        | (**Optional**) Name of the build system                              |
|    runner[^2]    |        string        | (**Optional**) Name of the runner (low-level build system)           |
|                   platforms                   | list of dictionaries | Describes the platforms used for building and running the project    |
|                    recipes                    | list of dictionaries | Build configuration parameters                                       |
|                    builds                     | list of dictionaries | Describes builds tasks                                               |

---

```yaml
build_system: CMake
runner: Make
platforms: [{}]
recipes: [{}]
builds: [{}]
```

### Platforms

The **platforms** section describes the machines on which the project will be built and run.

|                   Field                   |  Type   | Description                                    |
| :---------------------------------------: | :-----: | ---------------------------------------------- |
|                    id                     | integer | Unique id of the platform                      |
|                   arch                    | string  | Architecture (e.g. x86, riscv)                 |
|                  address                  | string  | (**Optional**) IP address or domain name       |
|                 username                  | string  | (**Optional**) Username of the remote machine  |
|   port[^3]   | integer | (**Optional**) Port of the remote machine      |
| password[^4] | string  | (**Optional**) Password for the remote machine |
| events[^5]   | list[str] or string | (**Optional**) CPU events name for the machine |

---

> **Note:**
>
> - If the `address` field is not specified, the local machine is assumed.
> - For a local machine, `username`, `password`, and `port` do not need to be specified.
> - If an `address` is specified, the machine is treated as remote, and the fields `username`, `password`, and `port` must be provided.
> - If you connect with SSH keys instead of a password, run `eval "$(ssh-agent -s)"` and then add the keys for the target machines manually, for example `ssh-add ~/.ssh/id_remote_machine`, before starting Amphimixis.
> - If events are passed as a string, they must be separated by whitespace.

### Recipes

The **recipes** section describes the build configuration and compiler flags.

|                  Field                          |  Type   | Description                                                                               |
| :---------------------------------------------: | :-----: | ----------------------------------------------------------------------------------------- |
| id                                              | integer | Unique ID of the recipe                                                                   |
| config_flags                                    | string  | (**Optional**) Build configuration options                                                |
| compiler_flags[^5] | dict    | (**Optional**) Compiler flags used during the build process                               |
| toolchain[^6]      |  dict   | (**Optional**) Path to the toolchain used for building the project                        |
| sysroot                                         | string  | (**Optional**) Path to the folder with system headers and libraries used by the toolchain |
| jobs                                            | integer | (**Optional**) Number of parallel jobs used by the build system                           |

### Builds

The **builds** section links platforms and recipes, defining which configurations should be built on which machines.

|     Field                                      |  Type   | Description                                                                |
| :--------------------------------------------: | :-----: | -------------------------------------------------------------------------- |
| build_machine                                  | integer | `platform_id` of the machine where the project will be built               |
| run_machine                                    | integer | `platform_id` of the machine where the built project will be executed      |
| recipe_id                                      | integer | ID of the `recipe`                                                         |
| executables[^7]   |  list   | (**Optional**) List of executables to profile for this build               |

---

Example:

```yaml
builds:
  - build_machine: 1
    run_machine: 1
    recipe_id: 1
    executables:
      - bin/my_app
      - tests/my_benchmark
```

Example:

```yaml
# Define a reusable list of executables
executables: &my_executables
  - bin/my_app
  - tests/my_benchmark

builds:
  - build_machine: 1
    run_machine: 1
    recipe_id: 1
    executables: *my_executables   # reference the list above
```

> **Note:**
>
> - YAML references (& and *) let you reuse the same `executables` list across multiple builds, reducing duplication.

[^1]: `CMake` and `Make` are supported as build systems. If not specified, it is automatically selected from the set of build systems supported by the project.

[^2]: `Make` and `Ninja` are supported as runners (low-level build system). If not specified, it is automatically selected from the supported runners of the selected build system.

[^3]: Default value: 22. The `port` must be within the range 1-65535.

[^4]: If the user uses SSH keys, start `ssh-agent` in the current shell and add the required keys for each remote machine manually with `ssh-add` before running Amphimixis. In this case, the password does not need to be provided. **Please note that passwords are passed to SSH through sshpass, which is not secure.**

[^5]: Possible compiler flags:

    <details>
    <summary>All supported flags:</summary>

    - c_flags
    - cxx_flags
    - csharp_flags
    - cuda_flags
    - objc_flags
    - objcxx_flags
    - fortran_flags
    - hip_flags
    - ispc_flags
    - swift_flags
    - asm_flags
    - asm_nasm_flags
    - asm_marmasm_flags
    - asm_masm_flags
    - asm_att_flags

    </details>

[^6]: Possible toolchain attributes:

    <details>
    <summary>All supported tools:</summary>

    - ar
    - as
    - ld
    - nm
    - objcopy
    - objdump
    - ranlib
    - readelf
    - strip
    - c_compiler
    - cxx_compiler
    - csharp_compiler
    - cuda_compiler
    - objc_compiler
    - objcxx_compiler
    - fortran_compiler
    - hip_compiler
    - ispc_compiler
    - swift_compiler
    - asm_compiler
    - asm_nasm_compiler
    - asm_marmasm_compiler
    - asm_masm_compiler
    - asm_att_compiler

    </details>

    <details>
    <summary>You can also specify flags to the toolchain:</summary>

    - c_flags
    - cxx_flags
    - csharp_flags
    - cuda_flags
    - objc_flags
    - objcxx_flags
    - fortran_flags
    - hip_flags
    - ispc_flags
    - swift_flags
    - asm_flags
    - asm_nasm_flags
    - asm_marmasm_flags
    - asm_masm_flags
    - asm_att_flags

    </details>

[^7]: Each path in `executables` must be specified relative to the build directory created for this build. For example, use `bin/app` rather than an absolute path. If `executables` is not specified, Amphimixis will profile the first executable file it finds in the build directory.
