import unittest

from b2_config import (
    B2ConfigError,
    build_b2_config,
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


class RecordingClient:
    def __init__(self):
        self.bucket = None

    def head_bucket(self, *, Bucket):
        self.bucket = Bucket


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


if __name__ == "__main__":
    unittest.main()
