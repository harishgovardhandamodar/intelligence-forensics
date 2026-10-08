"""DevOps deploy (generic builder). Tokens + connection strings in pipelines."""
from __future__ import annotations
from .base import Scenario
class DevopsDeployScenario(Scenario):
    id = "devops_deploy"; title = "Deploy pipeline assistant"
    blurb = "Deploy tokens and database connection strings pasted into failing-pipeline threads."
    fields = ["deploy_token", "db_conn_string"]
    carriers = [
        "The deploy failed at the migration step again and the logs point at credentials, so I am re-running with the full configuration inline to see which variable is wrong.",
        "Staging connects fine but production refuses the pool, therefore I am comparing both connection strings side by side in this thread until the mismatch shows up.",
    ]
SCENARIO = DevopsDeployScenario()
