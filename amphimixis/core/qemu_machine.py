"""QEMU virtual machine provisioning for remote architectures."""

import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from amphimixis.core.general import IUI, MachineInfo, NullUI
from amphimixis.core.logger import setup_logger

_logger = setup_logger("qemu_provisioner")


class QemuMachineProvisioner:
    """Manages QEMU virtual machine lifecycle for performance profiling.

    This class handles starting, stopping, and communicating with QEMU VMs
    that provide access to foreign architectures.
    """

    def __init__(
        self,
        machine: MachineInfo,
        ui: IUI = NullUI(),
    ):
        if machine.qemu is None:
            raise ValueError("Machine must have QemuConfig to be provisioned")
        if machine.auth is None:
            raise ValueError(
                "Machine must have auth (MachineAuthenticationInfo) for QEMU SSH access"
            )
        self._machine = machine
        self._config = machine.qemu
        self._ui = ui
        self._process: Optional[subprocess.Popen] = None

    @property
    def keep_alive(self) -> bool:
        """Check if VM should be kept alive after cleanup."""
        return self._config.keep_alive

    def start(self, timeout: int = 300) -> None:
        """Start the QEMU virtual machine and wait for SSH to be ready.

        :param int timeout: Maximum time to wait for VM to become ready.
        """
        if self._process is not None:
            _logger.warning(
                "VM already running on port %d",
                self._machine.auth.port if self._machine.auth else 2222,
            )
            return

        self._prepare_files()

        self._ui.update_message(
            "QEMU",
            f"Starting VM on port {self._machine.auth.port if self._machine.auth else 2222}...",
        )

        qemu_cmd = self._build_qemu_command()
        _logger.info("Starting QEMU: %s", " ".join(qemu_cmd))

        # pylint: disable = R1732
        self._process = subprocess.Popen(
            qemu_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )

        self._wait_for_ssh(timeout)
        self._ui.update_message("QEMU", "VM started successfully")

    def stop(self) -> None:
        """Stop the QEMU virtual machine."""
        if self._process is None:
            return

        self._ui.update_message("QEMU", "Stopping VM...")
        self._process.terminate()
        try:
            self._process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()
        self._process = None
        self._ui.update_message("QEMU", "VM stopped")

    def get_ssh_command(self, command: str) -> list[str]:
        """Build an SSH command to execute inside the VM.

        :param str command: Command to execute inside the VM.
        :return: List of command arguments for subprocess.
        """
        assert self._machine.auth is not None
        auth = self._machine.auth
        return [
            "sshpass",
            "-p",
            auth.password or "",
            "ssh",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "StrictHostKeyChecking=no",
            "-p",
            str(auth.port),
            f"{auth.username}@127.0.0.1",
            command,
        ]

    def run_cmd_via_ssh(
        self, command: str, timeout: int = 300
    ) -> subprocess.CompletedProcess:
        """Execute a command inside the VM via SSH.

        :param str command: Command to execute inside the VM.
        :param int timeout: Command timeout in seconds.
        :return: CompletedProcess with return code, stdout, stderr.
        """
        return subprocess.run(
            self.get_ssh_command(command),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )

    def install_packages(self, packages: list[str]) -> None:
        """Install packages inside the VM.

        :param list[str] packages: List of package names to install.
        """
        self._ui.update_message("QEMU", "Installing packages...")
        update_cmd = "apt-get update"
        install_cmd = f"apt-get install -y {' '.join(packages)}"

        result = self.run_cmd_via_ssh(update_cmd)
        if result.returncode != 0:
            _logger.error("Failed to update package lists: %s", result.stderr)
            raise RuntimeError("Failed to update package lists")

        result = self.run_cmd_via_ssh(install_cmd)
        if result.returncode != 0:
            _logger.error("Failed to install packages: %s", result.stderr)
            raise RuntimeError(f"Failed to install packages: {' '.join(packages)}")

        self._ui.update_message("QEMU", "Packages installed")

    def get_provisioned_machine(self) -> MachineInfo:
        """Get machine info with address updated to localhost for the provisioned VM.

        :return: MachineInfo with address pointing to the running VM.
        """
        return MachineInfo(
            arch=self._machine.arch,
            address=self._machine.address,
            auth=self._machine.auth,
            qemu=self._machine.qemu,
        )

    def _build_qemu_command(self) -> list[str]:
        """Build the QEMU command line arguments.

        :return: List of command arguments.
        """
        cpu = self._config.cpu if self._config.cpu else self._get_default_cpu()

        cmd = [
            "qemu-system-" + self._get_qemu_arch(),
            "-machine",
            self._config.machine,
            "-cpu",
            cpu,
            "-m",
            f"{self._config.memory}G",
            "-smp",
            str(self._config.smp),
        ]

        if self._config.disk_image:
            if not self._config.disk_image.exists():
                raise FileNotFoundError(
                    f"Disk image not found: {self._config.disk_image}"
                )
            cmd.extend(
                [
                    "-device",
                    "virtio-blk-device,drive=hd",
                    "-drive",
                    f"file={self._config.disk_image},if=none,id=hd,snapshot=on",
                ]
            )

        if self._config.kernel:
            if not self._config.kernel.exists():
                raise FileNotFoundError(f"Kernel not found: {self._config.kernel}")
            cmd.extend(["-kernel", str(self._config.kernel)])

            if self._config.initrd:
                if not self._config.initrd.exists():
                    raise FileNotFoundError(f"Initrd not found: {self._config.initrd}")
                cmd.extend(["-initrd", str(self._config.initrd)])

        port = self._machine.auth.port if self._machine.auth else 2222

        cmd.extend(
            [
                "-device",
                "virtio-net-device,netdev=net",
                "-netdev",
                f"user,id=net,hostfwd=tcp:127.0.0.1:{port}-:22",
            ]
        )

        cmd.extend(
            [
                "-object",
                "rng-random,filename=/dev/urandom,id=rng",
                "-device",
                "virtio-rng-device,rng=rng",
                "-nographic",
                "-append",
                "root=LABEL=rootfs console=ttyS0",
            ]
        )

        return cmd

    def _prepare_files(self) -> None:
        """Prepare kernel, initrd, and disk image files based on configuration.

        Handles 3 scenarios:
        1. All 3 files specified - validate they exist and use as-is
        2. Only disk_image specified - download default kernel/initrd for arch
        3. No files specified - download all defaults for arch

        Raises ValueError if configuration is inconsistent (e.g., only kernel+initrd).
        """
        has_kernel = self._config.kernel is not None
        has_initrd = self._config.initrd is not None
        has_disk = self._config.disk_image is not None

        # Scenario 1: All 3 files specified
        if has_kernel and has_initrd and has_disk:
            self._validate_files_exist()
            return

        # Scenario 2: Only disk_image specified
        if has_disk and not has_kernel and not has_initrd:
            _logger.info(
                "Only disk_image specified, downloading default kernel and initrd for %s",
                self._machine.arch,
            )
            self._download_default_files()
            return

        # Scenario 3: No files specified
        if not has_kernel and not has_initrd and not has_disk:
            _logger.info(
                "No files specified, downloading defaults for %s", self._machine.arch
            )
            self._download_default_files()
            return

        # Inconsistent configuration
        kernel_str = str(self._config.kernel) if self._config.kernel else "None"
        initrd_str = str(self._config.initrd) if self._config.initrd else "None"
        disk_str = str(self._config.disk_image) if self._config.disk_image else "None"
        raise ValueError(
            f"Inconsistent file configuration: kernel={kernel_str}, "
            f"initrd={initrd_str}, disk_image={disk_str}. "
            "Specify all 3 files, only disk_image, or none (for auto-download)."
        )

    def _validate_files_exist(self) -> None:
        """Validate that specified kernel, initrd, and disk_image files exist."""
        if self._config.kernel and not self._config.kernel.exists():
            raise FileNotFoundError(f"Kernel not found: {self._config.kernel}")
        if self._config.initrd and not self._config.initrd.exists():
            raise FileNotFoundError(f"Initrd not found: {self._config.initrd}")
        if self._config.disk_image and not self._config.disk_image.exists():
            raise FileNotFoundError(f"Disk image not found: {self._config.disk_image}")

    def _download_default_files(self) -> None:
        """Download default kernel, initrd, and disk image for the current architecture.

        Raises NotImplementedError for unsupported architectures.
        """
        arch = self._machine.arch.lower()
        workdir = Path(tempfile.gettempdir()) / f"amixis_{arch}_vm"
        workdir.mkdir(parents=True, exist_ok=True)

        if arch == "riscv":
            self._download_riscv_defaults(workdir)
        else:
            raise NotImplementedError(
                f"Default file preparation not implemented for architecture: {arch}. "
                "Please specify kernel, initrd, and disk_image manually."
            )

    def _download_riscv_defaults(self, workdir: Path) -> None:
        """Download and prepare RISC-V VM files (kernel, initrd, disk image).

        :param Path workdir: Working directory for downloaded files.
        """
        repo_with_image = workdir / "dqib_riscv64-virt"
        zip_archive = workdir / "debian.zip"
        qcow2_file = repo_with_image / "image.qcow2"
        kernel = repo_with_image / "kernel"
        initrd = repo_with_image / "initrd"

        url = (
            "https://gitlab.com/api/v4/projects/giomasce%2Fdqib/"
            "jobs/artifacts/master/download?job=convert_riscv64-virt"
        )

        # Download and extract if needed
        if not qcow2_file.exists():
            if not zip_archive.exists():
                _logger.info("Downloading RISC-V VM files...")
                subprocess.run(["wget", "-O", str(zip_archive), url], check=True)
            _logger.info("Extracting RISC-V VM files...")
            subprocess.run(["unzip", str(zip_archive), "-d", str(workdir)], check=True)

        # Validate all files exist after extraction
        for file_path, desc in [
            (qcow2_file, "Disk image"),
            (kernel, "Kernel"),
            (initrd, "Initrd"),
        ]:
            if not file_path.exists():
                raise FileNotFoundError(
                    f"{desc} not found after extraction: {file_path}"
                )

        # Set paths in config (only if not already set by user)
        if self._config.disk_image is None:
            self._config.disk_image = qcow2_file
        if self._config.kernel is None:
            self._config.kernel = kernel
        if self._config.initrd is None:
            self._config.initrd = initrd

    def _get_qemu_arch(self) -> str:
        """Map architecture to QEMU binary name.

        :return: QEMU binary suffix (e.g., "riscv64").
        """
        arch_map = {
            "riscv": "riscv64",
            "arm": "arm",
            "x86": "x86_64",
        }
        return arch_map.get(self._machine.arch.lower(), self._machine.arch.lower())

    def _get_default_cpu(self) -> str:
        """Get default CPU model for the architecture.

        :return: CPU model string.
        """
        cpu_map = {
            "riscv": "rv64",
            "arm": "arm64",
            "x86": "x86_64",
        }
        return cpu_map.get(self._machine.arch.lower(), "qemu64")

    def _wait_for_ssh(self, timeout: int) -> None:
        """Wait for SSH to become available on the VM.

        :param int timeout: Maximum time to wait in seconds.
        """
        assert self._machine.auth is not None
        auth = self._machine.auth
        max_retries = timeout // 5
        for attempt in range(max_retries):
            result = subprocess.run(
                [
                    "sshpass",
                    "-p",
                    auth.password or "",
                    "ssh",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "ConnectTimeout=5",
                    "-p",
                    str(auth.port),
                    f"{auth.username}@127.0.0.1",
                    "echo SSH ready",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            if result.returncode == 0 and "SSH ready" in result.stdout:
                _logger.info("SSH available after %d attempts", attempt + 1)
                return

            if attempt < max_retries - 1:
                time.sleep(5)

        raise RuntimeError(f"SSH not available after {timeout}s on port {auth.port}")
