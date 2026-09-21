"""QemuMachineProvisioner unit tests (subprocess is mocked)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amphimixis.core.general import (
    Arch,
    MachineAuthenticationInfo,
    MachineInfo,
    QemuConfig,
)
from amphimixis.core.qemu_machine import QemuMachineProvisioner


def _machine(arch: Arch, qemu: QemuConfig | None, port: int = 2222) -> MachineInfo:
    """Build a MachineInfo with loopback auth for tests."""
    auth = MachineAuthenticationInfo("root", "root", port)
    return MachineInfo(arch=arch, address="127.0.0.1", auth=auth, qemu=qemu)


@pytest.mark.unit
class TestProvisionerInit:
    """Tests for QemuMachineProvisioner constructor validation."""

    def test_requires_qemu_config(self):
        """Machine without qemu config raises ValueError."""
        machine = MachineInfo(
            arch=Arch.X86,
            address="127.0.0.1",
            auth=MachineAuthenticationInfo("root", "root", 2222),
            qemu=None,
        )
        with pytest.raises(ValueError):
            QemuMachineProvisioner(machine)

    def test_requires_auth(self):
        """Machine without auth raises ValueError."""
        machine = MachineInfo(
            arch=Arch.X86, address="127.0.0.1", auth=None, qemu=QemuConfig()
        )
        with pytest.raises(ValueError):
            QemuMachineProvisioner(machine)


@pytest.mark.unit
class TestBuildQemuCommand:
    """Tests for _build_qemu_command unconditional and conditional options."""

    def test_x86_base_command(self):
        """x86 uses pc/qemu64 and pci network/rng devices."""
        provisioner = QemuMachineProvisioner(_machine(Arch.X86, QemuConfig()))
        cmd = provisioner._build_qemu_command()

        assert cmd[0] == "qemu-system-x86_64"
        assert "-machine" in cmd and "pc" in cmd
        assert "-cpu" in cmd and "qemu64" in cmd
        assert "-m" in cmd and "4G" in cmd
        assert "-smp" in cmd and "4" in cmd
        assert "virtio-net-pci,netdev=net" in cmd
        assert "user,id=net,hostfwd=tcp:127.0.0.1:2222-:22" in cmd
        assert "rng-random,filename=/dev/urandom,id=rng" in cmd
        assert "virtio-rng-pci,rng=rng" in cmd
        assert "-nographic" in cmd

    def test_riscv_base_command(self):
        """riscv uses virt/rv64 and non-pci network/rng devices."""
        provisioner = QemuMachineProvisioner(_machine(Arch.RISCV, QemuConfig()))
        cmd = provisioner._build_qemu_command()

        assert cmd[0] == "qemu-system-riscv64"
        assert "virt" in cmd
        assert "rv64" in cmd
        assert "virtio-net-device,netdev=net" in cmd
        assert "virtio-rng-device,rng=rng" in cmd

    def test_custom_resources_and_port(self):
        """Custom machine/cpu/memory/smp/port are reflected in the command."""
        config = QemuConfig(machine="custom", cpu="custom-cpu", memory=8, smp=2)
        provisioner = QemuMachineProvisioner(_machine(Arch.X86, config, port=3333))
        cmd = " ".join(provisioner._build_qemu_command())

        assert "-machine custom" in cmd
        assert "-cpu custom-cpu" in cmd
        assert "-m 8G" in cmd
        assert "-smp 2" in cmd
        assert "hostfwd=tcp:127.0.0.1:3333-:22" in cmd

    def test_disk_image_adds_snapshot_drive(self, tmp_path):
        """disk_image adds a snapshot=on drive; missing file raises."""
        disk = tmp_path / "image.qcow2"
        disk.write_bytes(b"fake")
        config = QemuConfig(disk_image=disk)
        cmd = " ".join(
            QemuMachineProvisioner(_machine(Arch.X86, config))._build_qemu_command()
        )

        assert f"file={disk},if=none,id=hd,snapshot=on" in cmd

        missing = QemuConfig(disk_image=tmp_path / "nope.qcow2")
        with pytest.raises(FileNotFoundError):
            QemuMachineProvisioner(_machine(Arch.X86, missing))._build_qemu_command()

    def test_kernel_and_initrd(self, tmp_path):
        """kernel/initrd add -kernel/-initrd; missing files raise."""
        kernel = tmp_path / "vmlinux"
        kernel.write_bytes(b"fake")
        initrd = tmp_path / "initrd"
        initrd.write_bytes(b"fake")
        config = QemuConfig(disk_image=tmp_path / "d.qcow2", kernel=kernel)
        (tmp_path / "d.qcow2").write_bytes(b"fake")
        cmd = QemuMachineProvisioner(_machine(Arch.X86, config))._build_qemu_command()

        assert "-kernel" in cmd and str(kernel) in cmd
        assert "-initrd" not in cmd

        config.initrd = initrd
        cmd = QemuMachineProvisioner(_machine(Arch.X86, config))._build_qemu_command()
        assert "-initrd" in cmd and str(initrd) in cmd

        config.kernel = tmp_path / "missing"
        with pytest.raises(FileNotFoundError):
            QemuMachineProvisioner(_machine(Arch.X86, config))._build_qemu_command()

    def test_append_only_for_riscv_defaults(self):
        """-append is added only for riscv with default files."""
        riscv = QemuMachineProvisioner(_machine(Arch.RISCV, QemuConfig()))
        riscv._uses_default_files = True
        assert "-append" in riscv._build_qemu_command()

        riscv._uses_default_files = False
        assert "-append" not in riscv._build_qemu_command()

        x86 = QemuMachineProvisioner(_machine(Arch.X86, QemuConfig()))
        x86._uses_default_files = True
        assert "-append" not in x86._build_qemu_command()

    def test_extra_args_appended_last(self):
        """extra_args are shell-split and appended at the end."""
        config = QemuConfig(extra_args=["-enable-kvm", "--foo bar"])
        cmd = QemuMachineProvisioner(_machine(Arch.X86, config))._build_qemu_command()

        assert cmd[-3:] == ["-enable-kvm", "--foo", "bar"]


@pytest.mark.unit
class TestPrepareFiles:
    """Tests for _prepare_files scenarios and uses_default_files flag."""

    def test_no_files_uses_defaults(self, tmp_path):
        """No files -> uses_default_files, downloads defaults."""
        provisioner = QemuMachineProvisioner(_machine(Arch.X86, QemuConfig()))
        with patch.object(provisioner, "_download_default_files") as mock_download:
            provisioner._prepare_files()

        assert provisioner.uses_default_files is True
        mock_download.assert_called_once()

    def test_only_disk_image(self, tmp_path):
        """Only disk_image -> custom files, no download."""
        disk = tmp_path / "image.qcow2"
        disk.write_bytes(b"fake")
        provisioner = QemuMachineProvisioner(
            _machine(Arch.X86, QemuConfig(disk_image=disk))
        )
        with patch.object(provisioner, "_download_default_files") as mock_download:
            provisioner._prepare_files()

        assert provisioner.uses_default_files is False
        mock_download.assert_not_called()

    def test_all_files_validated(self, tmp_path):
        """All three existing files -> used as-is."""
        kernel = tmp_path / "vmlinux"
        kernel.write_bytes(b"fake")
        initrd = tmp_path / "initrd"
        initrd.write_bytes(b"fake")
        disk = tmp_path / "image.qcow2"
        disk.write_bytes(b"fake")
        provisioner = QemuMachineProvisioner(
            _machine(
                Arch.X86, QemuConfig(kernel=kernel, initrd=initrd, disk_image=disk)
            )
        )
        with patch.object(provisioner, "_download_default_files") as mock_download:
            provisioner._prepare_files()

        assert provisioner.uses_default_files is False
        mock_download.assert_not_called()

    def test_inconsistent_files_raise(self, tmp_path):
        """kernel without disk_image raises ValueError."""
        kernel = tmp_path / "vmlinux"
        kernel.write_bytes(b"fake")
        provisioner = QemuMachineProvisioner(
            _machine(Arch.X86, QemuConfig(kernel=kernel))
        )
        with pytest.raises(ValueError):
            provisioner._prepare_files()

    def test_missing_all_files_raises(self, tmp_path):
        """All three files with a missing one raises FileNotFoundError."""
        provisioner = QemuMachineProvisioner(
            _machine(
                Arch.X86,
                QemuConfig(
                    kernel=tmp_path / "missing",
                    initrd=tmp_path / "initrd",
                    disk_image=tmp_path / "image.qcow2",
                ),
            )
        )
        with pytest.raises(FileNotFoundError):
            provisioner._prepare_files()


@pytest.mark.unit
class TestSshAndLifecycle:
    """Tests for SSH command building and start/stop edge cases."""

    def test_get_ssh_command(self):
        """SSH command carries port, user and no-host-check options."""
        machine = _machine(Arch.X86, QemuConfig(), port=3333)
        assert machine.auth is not None
        machine.auth.username = "user"
        cmd = QemuMachineProvisioner(machine).get_ssh_command("echo hi")

        assert "-p" in cmd and "3333" in cmd
        assert "user@127.0.0.1" in cmd
        assert "StrictHostKeyChecking=no" in cmd
        assert cmd[-1] == "echo hi"

    def test_stop_without_process_is_noop(self):
        """stop() on a non-started VM does nothing."""
        provisioner = QemuMachineProvisioner(_machine(Arch.X86, QemuConfig()))
        provisioner.stop()
        assert provisioner._process is None

    def test_start_when_running_warns(self):
        """start() on a running VM keeps the existing process."""
        provisioner = QemuMachineProvisioner(_machine(Arch.X86, QemuConfig()))
        running = MagicMock()
        provisioner._process = running
        with patch("amphimixis.core.qemu_machine.subprocess.Popen") as mock_popen:
            provisioner.start()

        mock_popen.assert_not_called()
        assert provisioner._process is running

    def test_is_default_image_property(self):
        """is_default_image reflects the internal flag."""
        provisioner = QemuMachineProvisioner(_machine(Arch.X86, QemuConfig()))
        assert provisioner.is_default_image is False
        provisioner._default_image = True
        assert provisioner.is_default_image is True

    def test_keep_alive_property(self):
        """keep_alive reflects the config value."""
        assert (
            QemuMachineProvisioner(_machine(Arch.X86, QemuConfig())).keep_alive is False
        )
        assert (
            QemuMachineProvisioner(
                _machine(Arch.X86, QemuConfig(keep_alive=True))
            ).keep_alive
            is True
        )

    def test_qemu_arch_mapping(self):
        """Architecture maps to the qemu binary suffix."""
        assert (
            QemuMachineProvisioner(_machine(Arch.X86, QemuConfig()))._get_qemu_arch()
            == "x86_64"
        )
        assert (
            QemuMachineProvisioner(_machine(Arch.RISCV, QemuConfig()))._get_qemu_arch()
            == "riscv64"
        )

    def test_default_machine_and_cpu(self):
        """Defaults are arch-specific."""
        x86 = QemuMachineProvisioner(_machine(Arch.X86, QemuConfig()))
        assert x86._get_default_machine() == "pc"
        assert x86._get_default_cpu() == "qemu64"
        riscv = QemuMachineProvisioner(_machine(Arch.RISCV, QemuConfig()))
        assert riscv._get_default_machine() == "virt"
        assert riscv._get_default_cpu() == "rv64"

    def test_get_provisioned_machine(self):
        """Provisioned machine keeps arch, address and auth."""
        machine = _machine(Arch.RISCV, QemuConfig(), port=3333)
        result = QemuMachineProvisioner(machine).get_provisioned_machine()

        assert result.arch == Arch.RISCV
        assert result.address == "127.0.0.1"
        assert result.auth is not None
        assert result.auth.port == 3333


@pytest.mark.unit
class TestQemuConfigPaths:
    """Tests for the default images directory resolution."""

    def test_uses_xdg_data_home(self, tmp_path, monkeypatch):
        """XDG_DATA_HOME is respected when set."""
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        provisioner = QemuMachineProvisioner(_machine(Arch.X86, QemuConfig()))

        assert provisioner._get_default_images_dir("x86") == (
            Path(str(tmp_path)) / "amphimixis" / "images" / "x86"
        )
