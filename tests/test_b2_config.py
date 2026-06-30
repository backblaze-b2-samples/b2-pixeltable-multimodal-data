import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from b2_config import (
    B2ConfigError,
    B2_SAMPLE_UA_APP_ID,
    B2_SAMPLE_USER_AGENT,
    build_b2_config,
    configure_pixeltable_b2_user_agent,
    export_s3_compatible_environment,
    preflight_b2_bucket,
)


def valid_region():
    return "us" + "-west-" + "004"


def legacy_key_id_name():
    return "B2_" + "KEY_ID"


def legacy_bucket_name():
    return "B2_" + "BUCKET"


class FailingClient:
    def head_bucket(self, *, Bucket):
        raise RuntimeError(f"bucket unavailable: {Bucket}")


class SecretLeakingClient:
    def head_bucket(self, *, Bucket):
        raise RuntimeError(
            "B2_APPLICATION_KEY=super-secret AWS_SECRET_ACCESS_KEY=super-secret"
        )


class RecordingClient:
    def __init__(self):
        self.bucket = None

    def head_bucket(self, *, Bucket):
        self.bucket = Bucket


class FakeCredentials:
    def get_frozen_credentials(self):
        return object()


class FakeBotoSession:
    def get_credentials(self):
        return FakeCredentials()

    def client(self, service_name, **kwargs):
        return SimpleNamespace(service_name=service_name, kwargs=kwargs)

    def resource(self, service_name, **kwargs):
        return SimpleNamespace(service_name=service_name, kwargs=kwargs)


class FakePixeltableS3Store:
    @classmethod
    def create_boto_session(cls, profile_name=None):
        return FakeBotoSession()

    @classmethod
    def create_boto_client(cls, profile_name=None, extra_args=None):
        raise AssertionError("unpatched Pixeltable client factory was used")

    @classmethod
    def create_boto_resource(cls, profile_name=None, extra_args=None):
        raise AssertionError("unpatched Pixeltable resource factory was used")


class B2ConfigTests(unittest.TestCase):
    def test_builds_default_public_url_and_exports_sdk_env(self):
        config = build_b2_config(
            env={
                "B2_APPLICATION_KEY_ID": "test-key-id",
                "B2_APPLICATION_KEY": "test-application-key",
                "B2_REGION": valid_region(),
                "B2_BUCKET_NAME": "test-bucket",
            },
            allow_prompts=False,
        )

        self.assertEqual(
            config.endpoint_url,
            f"https://s3.{valid_region()}.backblazeb2.com",
        )
        self.assertEqual(
            config.public_url_base,
            f"https://s3.{valid_region()}.backblazeb2.com/test-bucket",
        )

        env = {}
        export_s3_compatible_environment(config, env=env)
        self.assertEqual(env["AWS" + "_ACCESS_KEY_ID"], "test-key-id")
        self.assertEqual(env["AWS" + "_DEFAULT_REGION"], valid_region())

    def test_export_clears_stale_aws_tokens_and_sets_user_agent_app_id(self):
        config = build_b2_config(
            env={
                "B2_APPLICATION_KEY_ID": "test-key-id",
                "B2_APPLICATION_KEY": "test-application-key",
                "B2_REGION": valid_region(),
                "B2_BUCKET_NAME": "test-bucket",
            },
            allow_prompts=False,
        )
        env = {
            "AWS" + "_SESSION_TOKEN": "stale-session-token",
            "AWS" + "_SECURITY_TOKEN": "stale-security-token",
        }

        export_s3_compatible_environment(config, env=env)

        self.assertNotIn("AWS" + "_SESSION_TOKEN", env)
        self.assertNotIn("AWS" + "_SECURITY_TOKEN", env)
        self.assertEqual(env["AWS" + "_SDK_UA_APP_ID"], B2_SAMPLE_UA_APP_ID)

    def test_configures_pixeltable_s3_factories_with_sample_user_agent(self):
        pixeltable_module = ModuleType("pixeltable")
        pixeltable_utils_module = ModuleType("pixeltable.utils")
        pixeltable_s3_module = ModuleType("pixeltable.utils.s3_store")
        pixeltable_s3_module.S3Store = FakePixeltableS3Store

        with patch.dict(
            sys.modules,
            {
                "pixeltable": pixeltable_module,
                "pixeltable.utils": pixeltable_utils_module,
                "pixeltable.utils.s3_store": pixeltable_s3_module,
            },
        ):
            configure_pixeltable_b2_user_agent()

        client = FakePixeltableS3Store.create_boto_client(
            extra_args={"endpoint_url": f"https://s3.{valid_region()}.backblazeb2.com"}
        )
        resource = FakePixeltableS3Store.create_boto_resource(
            extra_args={"endpoint_url": f"https://s3.{valid_region()}.backblazeb2.com"}
        )

        self.assertEqual(client.kwargs["config"].user_agent_extra, B2_SAMPLE_USER_AGENT)
        self.assertEqual(resource.kwargs["config"].user_agent_extra, B2_SAMPLE_USER_AGENT)
        self.assertNotEqual(client.kwargs["config"].user_agent_extra, "pixeltable")
        self.assertNotEqual(resource.kwargs["config"].user_agent_extra, "pixeltable")

    def test_accepts_legacy_names_during_transition(self):
        config = build_b2_config(
            env={
                legacy_key_id_name(): "old-key-id",
                "B2_APPLICATION_KEY": "test-application-key",
                "B2_REGION": valid_region(),
                legacy_bucket_name(): "old-bucket",
            },
            allow_prompts=False,
        )

        self.assertEqual(config.application_key_id, "old-key-id")
        self.assertEqual(config.bucket_name, "old-bucket")

    def test_missing_config_fails_fast_when_prompts_are_disabled(self):
        with self.assertRaisesRegex(B2ConfigError, "B2_APPLICATION_KEY_ID"):
            build_b2_config(env={}, allow_prompts=False)

    def test_blank_prompted_key_id_fails_fast(self):
        with patch("builtins.input", return_value="   "):
            with self.assertRaisesRegex(B2ConfigError, "B2_APPLICATION_KEY_ID"):
                build_b2_config(env={}, allow_prompts=True)

    def test_blank_prompted_application_key_fails_fast(self):
        with patch("b2_config.getpass", return_value="   "):
            with self.assertRaisesRegex(B2ConfigError, "B2_APPLICATION_KEY"):
                build_b2_config(
                    env={
                        "B2_APPLICATION_KEY_ID": "test-key-id",
                        "B2_REGION": valid_region(),
                        "B2_BUCKET_NAME": "test-bucket",
                    },
                    allow_prompts=True,
                )

    def test_rejects_malicious_region(self):
        with self.assertRaisesRegex(B2ConfigError, "B2_REGION"):
            build_b2_config(
                env={
                    "B2_APPLICATION_KEY_ID": "test-key-id",
                    "B2_APPLICATION_KEY": "test-application-key",
                    "B2_REGION": valid_region()
                    + ".backblazeb2.com@attacker.example/a",
                    "B2_BUCKET_NAME": "test-bucket",
                },
                allow_prompts=False,
            )

    def test_rejects_public_url_with_userinfo(self):
        with self.assertRaisesRegex(B2ConfigError, "userinfo"):
            build_b2_config(
                env={
                    "B2_APPLICATION_KEY_ID": "test-key-id",
                    "B2_APPLICATION_KEY": "test-application-key",
                    "B2_REGION": valid_region(),
                    "B2_BUCKET_NAME": "test-bucket",
                    "B2_PUBLIC_URL_BASE": (
                        f"https://user@s3.{valid_region()}.backblazeb2.com/"
                        "test-bucket"
                    ),
                },
                allow_prompts=False,
            )

    def test_rejects_public_url_with_non_numeric_port(self):
        with self.assertRaisesRegex(B2ConfigError, "non-numeric port"):
            build_b2_config(
                env={
                    "B2_APPLICATION_KEY_ID": "test-key-id",
                    "B2_APPLICATION_KEY": "test-application-key",
                    "B2_REGION": valid_region(),
                    "B2_BUCKET_NAME": "test-bucket",
                    "B2_PUBLIC_URL_BASE": (
                        f"https://s3.{valid_region()}.backblazeb2.com:abc/"
                        "test-bucket"
                    ),
                },
                allow_prompts=False,
            )

    def test_rejects_public_url_with_zero_port(self):
        with self.assertRaisesRegex(B2ConfigError, "custom ports"):
            build_b2_config(
                env={
                    "B2_APPLICATION_KEY_ID": "test-key-id",
                    "B2_APPLICATION_KEY": "test-application-key",
                    "B2_REGION": valid_region(),
                    "B2_BUCKET_NAME": "test-bucket",
                    "B2_PUBLIC_URL_BASE": (
                        f"https://s3.{valid_region()}.backblazeb2.com:0/"
                        "test-bucket"
                    ),
                },
                allow_prompts=False,
            )

    def test_rejects_public_url_outside_selected_bucket(self):
        with self.assertRaisesRegex(B2ConfigError, "bucket root"):
            build_b2_config(
                env={
                    "B2_APPLICATION_KEY_ID": "test-key-id",
                    "B2_APPLICATION_KEY": "test-application-key",
                    "B2_REGION": valid_region(),
                    "B2_BUCKET_NAME": "test-bucket",
                    "B2_PUBLIC_URL_BASE": (
                        f"https://s3.{valid_region()}.backblazeb2.com/"
                        "other-bucket"
                    ),
                },
                allow_prompts=False,
            )

    def test_preflight_uses_head_bucket(self):
        client = RecordingClient()

        preflight_b2_bucket(client, "test-bucket")

        self.assertEqual(client.bucket, "test-bucket")

    def test_preflight_wraps_client_errors(self):
        with self.assertRaisesRegex(B2ConfigError, "B2 preflight failed"):
            preflight_b2_bucket(FailingClient(), "test-bucket")

    def test_preflight_does_not_leak_secret_from_unknown_exceptions(self):
        with self.assertRaises(B2ConfigError) as context:
            preflight_b2_bucket(SecretLeakingClient(), "test-bucket")

        error_text = str(context.exception)
        self.assertIn("RuntimeError", error_text)
        self.assertNotIn("super-secret", error_text)
        self.assertNotIn("B2_APPLICATION_KEY", error_text)
        self.assertNotIn("AWS" + "_SECRET_ACCESS_KEY", error_text)

    def test_preflight_sanitizes_botocore_client_errors(self):
        from botocore.exceptions import ClientError

        class ClientErrorClient:
            def head_bucket(self, *, Bucket):
                raise ClientError(
                    {
                        "Error": {
                            "Code": "Forbidden",
                            "Message": "super-secret",
                        },
                        "ResponseMetadata": {
                            "HTTPStatusCode": 403,
                            "RequestId": "request-123",
                        },
                    },
                    "HeadBucket",
                )

        with self.assertRaises(B2ConfigError) as context:
            preflight_b2_bucket(ClientErrorClient(), "test-bucket")

        error_text = str(context.exception)
        self.assertIn("ClientError code=Forbidden status=403", error_text)
        self.assertIn("request_id=request-123", error_text)
        self.assertNotIn("super-secret", error_text)


if __name__ == "__main__":
    unittest.main()
