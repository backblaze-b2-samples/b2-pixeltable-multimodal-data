"""Backblaze B2 configuration helpers for the Pixeltable notebook."""

from __future__ import annotations

from dataclasses import dataclass
from getpass import getpass
import os
import re
from typing import MutableMapping
from urllib.parse import urlparse, urlunparse


B2_SAMPLE_USER_AGENT = "b2-pixeltable-multimodal-data (backblaze-b2-samples)"
STANDARD_ENV_NAMES = (
    "B2_APPLICATION_KEY_ID",
    "B2_APPLICATION_KEY",
    "B2_BUCKET_NAME",
    "B2_REGION",
    "B2_PUBLIC_URL_BASE",
)

_LEGACY_APPLICATION_KEY_ID_ENV = "B2_" + "KEY_ID"
_LEGACY_BUCKET_NAME_ENV = "B2_" + "BUCKET"
_REGION_RE = re.compile(r"^[a-z]{2}(?:-[a-z]+)+-[0-9]{3}$")
_BUCKET_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")


class B2ConfigError(ValueError):
    """Raised when B2 notebook configuration is invalid or incomplete."""


@dataclass(frozen=True)
class B2NotebookConfig:
    application_key_id: str
    application_key: str
    region: str
    bucket_name: str
    endpoint_url: str
    public_url_base: str


def _read_setting(
    name: str,
    prompt: str,
    *,
    env: MutableMapping[str, str],
    aliases: tuple[str, ...] = (),
    secret: bool = False,
    allow_prompts: bool = True,
) -> str:
    for env_name in (name, *aliases):
        value = env.get(env_name, "").strip()
        if value:
            return value

    if not allow_prompts:
        names = ", ".join((name, *aliases))
        raise B2ConfigError(f"Missing required B2 setting. Export one of: {names}.")

    reader = getpass if secret else input
    try:
        return reader(prompt).strip()
    except (EOFError, KeyboardInterrupt) as exc:
        raise B2ConfigError(
            f"Missing required B2 setting {name}. Export the standard B2_* "
            "environment variables before non-interactive runs."
        ) from exc


def validate_region(region: str) -> str:
    region = region.strip()
    if not _REGION_RE.fullmatch(region):
        raise B2ConfigError(
            "B2_REGION must look like a Backblaze region slug, for example "
            "two letters followed by hyphen-separated words and three digits."
        )
    return region


def validate_bucket_name(bucket_name: str) -> str:
    bucket_name = bucket_name.strip()
    if not _BUCKET_RE.fullmatch(bucket_name):
        raise B2ConfigError(
            "B2_BUCKET_NAME must contain only lowercase letters, digits, and "
            "hyphens, and must start and end with a letter or digit."
        )
    return bucket_name


def build_endpoint_url(region: str) -> str:
    return f"https://s3.{region}.backblazeb2.com"


def validate_public_url_base(
    public_url_base: str,
    *,
    endpoint_url: str,
    bucket_name: str,
) -> str:
    value = public_url_base.strip().rstrip("/")
    parsed = urlparse(value)
    endpoint = urlparse(endpoint_url)

    if parsed.scheme != "https":
        raise B2ConfigError("B2_PUBLIC_URL_BASE must use https.")
    if parsed.username or parsed.password:
        raise B2ConfigError("B2_PUBLIC_URL_BASE must not contain userinfo.")
    try:
        parsed_port = parsed.port
    except ValueError as exc:
        raise B2ConfigError(
            "B2_PUBLIC_URL_BASE must not include a non-numeric port."
        ) from exc
    if parsed.params or parsed.query or parsed.fragment or parsed_port:
        raise B2ConfigError(
            "B2_PUBLIC_URL_BASE must not include params, query strings, "
            "fragments, or custom ports."
        )
    if parsed.hostname != endpoint.hostname:
        raise B2ConfigError(
            "B2_PUBLIC_URL_BASE host must match the selected Backblaze B2 region."
        )

    expected_path = f"/{bucket_name}"
    if parsed.path.rstrip("/") != expected_path:
        raise B2ConfigError(
            "B2_PUBLIC_URL_BASE path must be the selected bucket root."
        )

    return urlunparse(("https", endpoint.hostname or "", expected_path, "", "", ""))


def build_b2_config(
    *,
    env: MutableMapping[str, str] | None = None,
    allow_prompts: bool = True,
) -> B2NotebookConfig:
    env = os.environ if env is None else env

    application_key_id = _read_setting(
        "B2_APPLICATION_KEY_ID",
        "   B2_APPLICATION_KEY_ID: ",
        env=env,
        aliases=(_LEGACY_APPLICATION_KEY_ID_ENV,),
        allow_prompts=allow_prompts,
    )
    application_key = _read_setting(
        "B2_APPLICATION_KEY",
        "   B2_APPLICATION_KEY: ",
        env=env,
        secret=True,
        allow_prompts=allow_prompts,
    )
    region = validate_region(
        _read_setting(
            "B2_REGION",
            "   B2_REGION: ",
            env=env,
            allow_prompts=allow_prompts,
        )
    )
    bucket_name = validate_bucket_name(
        _read_setting(
            "B2_BUCKET_NAME",
            "   B2_BUCKET_NAME: ",
            env=env,
            aliases=(_LEGACY_BUCKET_NAME_ENV,),
            allow_prompts=allow_prompts,
        )
    )

    endpoint_url = build_endpoint_url(region)
    public_url_base = env.get("B2_PUBLIC_URL_BASE", "").strip()
    if public_url_base:
        public_url_base = validate_public_url_base(
            public_url_base,
            endpoint_url=endpoint_url,
            bucket_name=bucket_name,
        )
    else:
        public_url_base = f"{endpoint_url}/{bucket_name}"

    return B2NotebookConfig(
        application_key_id=application_key_id,
        application_key=application_key,
        region=region,
        bucket_name=bucket_name,
        endpoint_url=endpoint_url,
        public_url_base=public_url_base,
    )


def export_s3_compatible_environment(
    config: B2NotebookConfig,
    *,
    env: MutableMapping[str, str] | None = None,
) -> None:
    env = os.environ if env is None else env
    prefix = "AWS"
    for suffix, value in {
        "ACCESS_KEY_ID": config.application_key_id,
        "SECRET_ACCESS_KEY": config.application_key,
        "DEFAULT_REGION": config.region,
    }.items():
        env[f"{prefix}_{suffix}"] = value


def create_b2_s3_client(config: B2NotebookConfig):
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=config.endpoint_url,
        aws_access_key_id=config.application_key_id,
        aws_secret_access_key=config.application_key,
        region_name=config.region,
        config=Config(
            user_agent_extra=B2_SAMPLE_USER_AGENT,
            connect_timeout=5,
            read_timeout=10,
            retries={"max_attempts": 2, "mode": "standard"},
        ),
    )


def preflight_b2_bucket(client, bucket_name: str) -> None:
    try:
        client.head_bucket(Bucket=bucket_name)
    except Exception as exc:
        raise B2ConfigError(
            f"B2 preflight failed for bucket {bucket_name}: "
            f"{exc.__class__.__name__}: {exc}"
        ) from exc
