"""Cloud red-team configuration mixin.

Existing CSPM coverage (Prowler / Checkov) audits configuration
posture. This mixin adds the *post-exploit* layer: which IAM paths
escalate to admin, which over-privileged service principal can be
abused via OAuth consent grants, which GCP service account holds
the keys to the kingdom.

Three scanners share the mixin:

- ``pmapper`` — AWS IAM privilege-escalation graph (NCC PMapper).
  Reads ``iam:`` / ``sts:`` metadata, emits Edge / PrivescPath JSON.
- ``scoutsuite`` — multi-cloud (AWS, Azure, GCP) misconfig sweep.
  Complements Prowler by covering Azure + GCP that Prowler does
  not.
- ``azurehound`` — Azure resource-graph collector that feeds
  BloodHound CE; surfaces dangerous role assignments and Conditional
  Access gaps.

Credentials follow the same path as the identity scanners: the
target carries a ``credentials_ref`` resolved via the credential
backend; secrets reach the container through the ``--env-file``
mechanism.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class _CloudRedTeamConfig(BaseModel):
    cloud_red_team_enabled: bool = Field(
        default=False,
        description=(
            "Master toggle for the cloud red-team scanners. Off by "
            "default; per-scanner flags below act as a fine-grained "
            "override once the master is on."
        ),
    )

    pmapper_enabled: bool = Field(
        default=False,
        description="Enable the PMapper AWS IAM privesc scanner.",
    )
    pmapper_image: str = Field(
        default="ghcr.io/nccgroup/pmapper:latest",
        description="Container image for PMapper.",
    )

    scoutsuite_enabled: bool = Field(
        default=False,
        description="Enable the ScoutSuite multi-cloud audit scanner.",
    )
    scoutsuite_image: str = Field(
        default="ghcr.io/nccgroup/scoutsuite:latest",
        description="Container image for ScoutSuite.",
    )
    scoutsuite_default_provider: str = Field(
        default="aws",
        description=(
            "Default cloud provider when the target metadata does not "
            "specify one. Accepts ``aws|azure|gcp|aliyun|oci``."
        ),
    )

    azurehound_enabled: bool = Field(
        default=False,
        description="Enable the AzureHound (BloodHound Azure collector).",
    )
    azurehound_image: str = Field(
        default="specterops/azurehound:latest",
        description="Container image for AzureHound.",
    )

    cloud_collection_timeout_seconds: int = Field(
        default=2400,
        description=(
            "Wall-clock cap per cloud collection. Large AWS orgs / "
            "Azure tenants take 30+ minutes; default is 40 minutes."
        ),
    )
