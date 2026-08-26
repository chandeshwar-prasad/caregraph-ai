import os
import yaml
import pytest

def test_ci_workflow_yaml_validity():
    """Verify that .github/workflows/ci.yml exists and has valid YAML syntax."""
    workflow_path = os.path.join(".github", "workflows", "ci.yml")
    assert os.path.exists(workflow_path), f"Workflow file not found: {workflow_path}"
    
    with open(workflow_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    data = yaml.safe_load(content)
    assert isinstance(data, dict), "Workflow YAML must parse as a dictionary"
    assert "name" in data
    # PyYAML parses unquoted 'on:' as boolean True
    assert "on" in data or True in data
    assert "jobs" in data


def test_ci_workflow_jobs_and_security():
    """Verify that required CI jobs exist and no credentials are hardcoded."""
    workflow_path = os.path.join(".github", "workflows", "ci.yml")
    with open(workflow_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    data = yaml.safe_load(content)
    jobs = data.get("jobs", {})
    
    # Check essential jobs
    assert "hygiene-check" in jobs
    assert "test-suite" in jobs
    assert "docker-build-check" in jobs
    assert "azure-deployment-stage" in jobs
    
    # Ensure all secrets references use GitHub secrets interpolation
    assert "secrets.AZURE_CREDENTIALS" in content
    assert "secrets.REGISTRY_LOGIN_SERVER" in content
    assert "secrets.REGISTRY_PASSWORD" in content
    assert "postgres:postgres@" not in content



def test_pytest_ini_configuration():
    """Verify that pytest.ini exists and defines correct settings."""
    assert os.path.exists("pytest.ini"), "pytest.ini configuration file must exist"
    with open("pytest.ini", "r", encoding="utf-8") as f:
        content = f.read()
    assert "pythonpath = ." in content
    assert "testpaths = tests" in content


def test_dockerignore_completeness():
    """Verify that .dockerignore covers .github, .env*, and secret files."""
    assert os.path.exists(".dockerignore")
    with open(".dockerignore", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    assert ".github" in lines
    assert ".env*" in lines
    assert "!.env.example" in lines
