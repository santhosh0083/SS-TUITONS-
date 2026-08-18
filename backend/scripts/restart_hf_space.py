"""Restart the Hugging Face Space via the API, bypassing the web UI.

    set HF_TOKEN=hf_your_write_token   (if not still set)
    ./.venv/Scripts/python -m scripts.restart_hf_space
"""

import os
import sys

from huggingface_hub import HfApi

SPACE_ID = "sstutions/ss-tuitions-api"


def main() -> int:
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        print("Set HF_TOKEN first:  set HF_TOKEN=hf_your_write_token")
        return 1
    api = HfApi(token=token)
    # factory_reboot rebuilds the container fresh, picking up all secrets.
    api.restart_space(repo_id=SPACE_ID, factory_reboot=True)
    print("Restart requested (factory rebuild). It will build for a few minutes.")
    rt = api.get_space_runtime(repo_id=SPACE_ID)
    print("Current stage:", rt.stage)
    return 0


if __name__ == "__main__":
    sys.exit(main())
