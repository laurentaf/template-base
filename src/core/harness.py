import os
import json
from datetime import datetime

class ProjectHarness:
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.root = os.getcwd()
        self.state_file = os.path.join(self.root, ".harness_state.json")
        self._init_state()

    def _init_state(self):
        if not os.path.exists(self.state_file):
            state = {
                "project": self.project_name,
                "created_at": datetime.now().isoformat(),
                "last_deployment": None,
                "active_specs": [],
                "github_repo": None,
                "health": "OK"
            }
            self._save_state(state)

    def _save_state(self, state):
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def register_spec(self, spec_name: str):
        with open(self.state_file, "r") as f:
            state = json.load(f)
        if spec_name not in state["active_specs"]:
            state["active_specs"].append(spec_name)
            self._save_state(state)

    def set_github_repo(self, repo_url: str):
        with open(self.state_file, "r") as f:
            state = json.load(f)
        state["github_repo"] = repo_url
        self._save_state(state)

    def check_health(self):
        status = "OK"
        issues = []
        if not os.path.exists(self.state_file):
            status = "DEGRADED"
            issues.append("Harness state file missing")
        return {"status": status, "issues": issues, "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    harness = ProjectHarness("ltade-project")
    print(harness.check_health())
