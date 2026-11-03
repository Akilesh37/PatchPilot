import os
import pytest
from services.verification_worker.worker import VerificationWorker, CommandSecurityError

def test_environment_filtering_purges_secrets():
    # Inject sensitive dummy tokens into current environment
    os.environ["GITHUB_TOKEN"] = "ghp_secret_dummy_token_12345"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    os.environ["OPENAI_API_KEY"] = "sk-dummy-1234567890abcdef"

    try:
        clean_env = VerificationWorker.filter_environment()

        # Sensitive variables must NOT exist in the execution environment
        assert "GITHUB_TOKEN" not in clean_env
        assert "AWS_SECRET_ACCESS_KEY" not in clean_env
        assert "OPENAI_API_KEY" not in clean_env

        # Safe system variables must be preserved
        assert "PATH" in clean_env
        assert clean_env.get("CI") == "true"
    finally:
        os.environ.pop("GITHUB_TOKEN", None)
        os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
        os.environ.pop("OPENAI_API_KEY", None)

def test_prohibited_arguments_blocked():
    worker = VerificationWorker()

    with pytest.raises(CommandSecurityError):
        worker.validate_command(["mvn", "test", "-Dexec.executable=/bin/sh"])

    with pytest.raises(CommandSecurityError):
        worker.validate_command(["mvn", "test", "-DforkCount=0"])

    with pytest.raises(CommandSecurityError):
        worker.validate_command(["mvn", "test", "-Djava.library.path=/tmp"])

