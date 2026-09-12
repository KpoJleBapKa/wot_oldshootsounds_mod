import re
import subprocess


VERSION_PATTERN = re.compile(r"^v([0-9]+\.[0-9]+(?:\.[0-9]+)?(?:[-+][0-9A-Za-z.-]+)?)")


def branch_name(project_root):
    process = subprocess.run(["git", "branch", "--show-current"], cwd=str(project_root), capture_output=True, text=True)
    if process.returncode != 0:
        raise RuntimeError("Unable to read the current Git branch")
    branch = process.stdout.strip()
    if not branch:
        raise RuntimeError("A named Git branch is required to determine the mod version")
    return branch


def read_version(project_root):
    branch = branch_name(project_root)
    match = VERSION_PATTERN.match(branch)
    if match is None:
        raise RuntimeError("Git branch must start with v<version>: " + branch)
    return match.group(1)


def sync_version_file(project_root, version):
    (project_root / "VERSION").write_bytes((version + "\n").encode("utf-8"))
