import json
import os
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
from urllib import request

REGISTRY_BASE = "https://registry-1.docker.io/v2/library"
AUTH_BASE = "https://auth.docker.io"


def get(url, headers):
    req = request.Request(url, method="GET", headers=headers)
    response = request.urlopen(req)
    return json.loads(response.read().decode())


def extract(tar_path, output_dir):
    tarfile.open(tar_path).extractall(output_dir, filter="tar")


def get_auth_token(service):
    url = os.path.join(
        AUTH_BASE,
        "token?service=registry.docker.io&scope=repository:library",
        f"{service}:pull"
    )
    return get(url, {})["token"]


def get_image_blobs(service, tag, auth_token):
    url = os.path.join(REGISTRY_BASE, service, "manifests", tag)
    resp = get(url, headers={"Authorization": f"Bearer {auth_token}"})
    return [layer["blobSum"] for layer in resp["fsLayers"]]


def pull_image_layers(service, blobs, auth_token, output_dir):
    for blob in blobs:
        url = os.path.join(REGISTRY_BASE, service, "blobs", blob)
        req = request.Request(url, method="GET", headers={"Authorization": f"Bearer {auth_token}"})

        with TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, f"{blob}.tar"), "wb") as f:
                with request.urlopen(req) as resp:
                    f.write(resp.read())

            for file in os.listdir(tmpdir):
                extract(os.path.join(tmpdir, file), output_dir)


def main():
    image = sys.argv[2]
    tag = "latest" if ":" not in image else image.split(":")[1]
    command = sys.argv[3]
    args = sys.argv[4:]

    with TemporaryDirectory() as tmpdir:
        auth_token = get_auth_token(image)
        blobs = get_image_blobs(image, tag, auth_token)
        pull_image_layers(image, blobs, auth_token, tmpdir)

        cmd = os.path.basename(command)
        unshare_command = ["unshare", "--pid", "--fork", "--mount-proc", "--"]
        subprocess.run(unshare_command)
        os.chroot(tmpdir)

        completed_process = subprocess.run([cmd, *args], capture_output=True)

        sys.stdout.buffer.write(completed_process.stdout)
        sys.stderr.buffer.write(completed_process.stderr)
        sys.exit(completed_process.returncode)


if __name__ == "__main__":
    main()
