# environment/scenarios.py
# Full prerequisite state machine with rich context, 3-tier action graph, and variant groups

SCENARIOS = [

    # ════════════════════════════════════════════
    # ── EASY SCENARIOS
    # Rule: 1-2 observe steps, 1 fix. Direct 1:1 error→fix mapping.
    # ════════════════════════════════════════════
    {
        "id": "easy_001",
        "difficulty": "easy",
        "category": "git",
        "pipeline_name": "payment-service-build",
        "environment": "UAT",
        "failed_stage": "git-checkout",
        "stage_number": 1,
        "error_message": "fatal: Remote branch feature/paymnts not found in upstream origin",
        "root_cause": "Typo in branch name in Jenkinsfile.",
        "context_data": {
            "http_status": 128, 
            "remote": "origin", 
            "branch_requested": "feature/paymnts", 
            "branch_exists": False,
            "alternative_branches": ["feature/payments"]
        },
        "action_tiers": {
            "observe":  ["compare_branch_names"],
            "diagnose": [],
            "fix":      ["correct_branch_name"]
        },
        "irrelevant_actions": ["refresh_github_token", "retry_pipeline"],
        "hint": "Branch not found + branch_exists=False. Compare against alternative_branches.",
        "resolution": "Fix the branch name typo in Jenkinsfile and rerun."
    },
    {
        "id": "easy_002",
        "difficulty": "easy",
        "category": "security",
        "pipeline_name": "auth-service-build",
        "environment": "UAT",
        "failed_stage": "checkmarx",
        "stage_number": 3,
        "error_message": "Checkmarx scan failed: Project 'auth-service-v2' not found",
        "root_cause": "Checkmarx project name doesn't match portal registration.",
        "context_data": {
            "http_status": 404, 
            "project_status": "NOT_FOUND",
            "registered_projects": ["auth-service", "auth-service-prod"]
        },
        "action_tiers": {
            "observe":  ["check_checkmarx_portal"],
            "diagnose": [],
            "fix":      ["correct_checkmarx_project_name"]
        },
        "irrelevant_actions": ["retry_scan", "refresh_sonar_token"],
        "hint": "Project 'auth-service-v2' is NOT_FOUND. Look at registered_projects for the correct name.",
        "resolution": "Update Checkmarx project name in Jenkinsfile to match portal."
    },
    {
        "id": "easy_003",
        "difficulty": "easy",
        "category": "git",
        "pipeline_name": "frontend-web-app",
        "environment": "Dev",
        "failed_stage": "git-checkout",
        "stage_number": 1,
        "error_message": "fatal: Authentication failed for 'https://github.com/org/repo.git'",
        "root_cause": "GitHub PAT expired.",
        "context_data": {
            "auth_status": "EXPIRED", 
            "token_age_days": 91, 
            "policy_violation": True
        },
        "action_tiers": {
            "observe":  ["verify_github_token_expiry"],
            "diagnose": [],
            "fix":      ["refresh_github_token"]
        },
        "irrelevant_actions": ["correct_branch_name", "retry_pipeline"],
        "hint": "Authentication failed with auth_status=EXPIRED. Rotate the token.",
        "resolution": "Rotate the GitHub PAT in Jenkins credential store."
    },
    {
        "id": "easy_004",
        "difficulty": "easy",
        "category": "docker",
        "pipeline_name": "worker-queue",
        "environment": "Test",
        "failed_stage": "docker-build",
        "stage_number": 2,
        "error_message": "Step 4/10 : COPY requirements.txt .\nCOPY failed: file not found in build context: stat no_such_file.txt",
        "root_cause": "Dockerfile references a file not present in context.",
        "context_data": {
            "dockerfile_line": "COPY no_such_file.txt .", 
            "file_present": False,
            "build_context": ["requirements.txt", "app.py"]
        },
        "action_tiers": {
            "observe":  ["inspect_dockerfile"],
            "diagnose": [],
            "fix":      ["fix_dockerfile_copy_path"]
        },
        "irrelevant_actions": ["clear_docker_cache", "build_multiarch_docker_image"],
        "hint": "file_present=False in build_context. Correct the path in the Dockerfile.",
        "resolution": "Correct the filename in the Dockerfile COPY instruction."
    },

    # ════════════════════════════════════════════
    # ── MEDIUM SCENARIOS (3–4 steps)
    # Rule: 1 observe + 1 diagnose + 1 fix.
    # ════════════════════════════════════════════
    {
        "id": "medium_001",
        "difficulty": "medium",
        "category": "ecs",
        "pipeline_name": "orders-service-build",
        "environment": "PreProd",
        "failed_stage": "ecs-deployment",
        "stage_number": 6,
        "error_message": "ECS deployment failed: Task definition 'orders-service:prod' not found",
        "root_cause": "Prod task revision used in PreProd account.",
        "context_data": {
            "aws_account_ids": {"current": "456", "prod": "123"},
            "env_mismatch_detected": True,
            "available_revisions": ["orders-service:preprod"]
        },
        "action_tiers": {
            "observe":  ["inspect_task_definition_config"],
            "diagnose": ["verify_account_environment_matching"],
            "fix":      ["correct_task_definition_revision"]
        },
        "irrelevant_actions": ["refresh_github_token", "release_tf_lock"],
        "hint": "Task 'prod' requested in 'preprod' account (env_mismatch_detected=True). Map the correct revision.",
        "resolution": "Update the pipeline to use 'orders-service:preprod' in PreProd environments."
    },
    {
        "id": "medium_002",
        "difficulty": "medium",
        "category": "docker",
        "pipeline_name": "image-processor",
        "environment": "Dev",
        "failed_stage": "docker-build",
        "stage_number": 3,
        "error_message": "exec format error",
        "root_cause": "Build/Runner architecture mismatch (ARM64 vs AMD64).",
        "context_data": {
            "architecture_mismatch": True,
            "build_arch": "arm64",
            "runner_arch": "amd64"
        },
        "action_tiers": {
            "observe":  ["inspect_build_logs_architecture"],
            "diagnose": ["confirm_platform_mismatch"],
            "fix":      ["build_multiarch_container"]
        },
        "irrelevant_actions": ["release_tf_lock", "refresh_github_token"],
        "hint": "exec format error + architecture_mismatch=True. You need to build for the correct platform.",
        "resolution": "Use docker buildx --platform linux/amd64 to produce the correct binary."
    },
    {
        "id": "medium_003",
        "difficulty": "medium",
        "category": "k8s",
        "pipeline_name": "k8s-manifests",
        "environment": "Prod",
        "failed_stage": "kubectl-apply",
        "stage_number": 5,
        "error_message": "Error from server (Conflict): the object has been modified",
        "root_cause": "Manual edit caused resourceVersion conflict.",
        "context_data": {
            "drift_detected": True,
            "server_version": "8937",
            "local_version": "8421"
        },
        "action_tiers": {
            "observe":  ["read_k8s_diff_report"],
            "diagnose": ["detect_manual_resource_drift"],
            "fix":      ["force_k8s_manifest_sync"]
        },
        "irrelevant_actions": ["refresh_github_token", "clear_docker_cache"],
        "hint": "Conflict + drift_detected=True. A manual change is overriding the CI pipeline.",
        "resolution": "Apply --server-side or merge local manifest with server state."
    },

    # ════════════════════════════════════════════
    # ── HARD SCENARIOS (4–6 steps)
    # Rule: 2 observe + 2 diagnose + 1 fix.
    # ════════════════════════════════════════════
    {
        "id": "hard_001",
        "difficulty": "hard",
        "category": "git",
        "variant_group": "http_403",
        "pipeline_name": "github-releaser",
        "environment": "Prod",
        "failed_stage": "github-release",
        "stage_number": 7,
        "error_message": "HTTP 403 Forbidden calling GitHub API",
        "root_cause": "Token has insufficient scope (missing 'repo').",
        "context_data": {
            "http_status": 403,
            "auth_failed": True,
            "scope_check": "MISSING_REPO_SCOPE",
            "token_scopes_present": ["read:org"],
            "required_scopes": ["repo"],
            "ratelimit_status": "OK"
        },
        "action_tiers": {
            "observe":  ["audit_github_api_headers", "read_token_metadata"],
            "diagnose": ["verify_token_scope_requirements", "confirm_insufficient_permissions", "verify_token_expiration_policy"],
            "fix":      ["rotate_token_with_full_scopes"]
        },
        "irrelevant_actions": ["clear_docker_cache", "retry_with_basic_auth"],
        "hint": "403 Forbidden with scope_check=MISSING_REPO_SCOPE. Must rotate the token with full scopes.",
        "resolution": "Regenerate GitHub token with 'repo' scope."
    },
    {
        "id": "hard_002",
        "difficulty": "hard",
        "category": "ecs",
        "variant_group": "ecs_fail",
        "pipeline_name": "ai-inference",
        "environment": "Prod",
        "failed_stage": "ecs-deployment",
        "stage_number": 6,
        "error_message": "ECS tasks failed to start",
        "root_cause": "Fargate Spot capacity exhausted in AZ.",
        "context_data": {
            "capacity_error": "CAPACITY_UNAVAILABLE",
            "provider_status": "FARGATE_SPOT_EMPTY",
            "az_health": "DEGRADED",
            "ondemand_available": True
        },
        "action_tiers": {
            "observe":  ["read_ecs_service_events", "check_aws_health_dashboard"],
            "diagnose": ["detect_spot_instance_shortage", "verify_regional_capacity_limits", "audit_fargate_resource_quotas"],
            "fix":      ["switch_to_ondemand_strategy"]
        },
        "irrelevant_actions": ["update_iam_boundary", "correct_task_definition"],
        "hint": "provider_status=FARGATE_SPOT_EMPTY. Switch to on-demand provider.",
        "resolution": "Switch capacity provider to FARGATE on-demand."
    },
    {
        "id": "hard_003",
        "difficulty": "hard",
        "category": "auth",
        "pipeline_name": "inventory-app",
        "environment": "Prod",
        "failed_stage": "multi-stage",
        "stage_number": 3,
        "error_message": "Checkmarx: 401. ECR: expired. Webhook: 401.",
        "root_cause": "Simultaneous expiry of shared CI token.",
        "context_data": {
            "multi_service_failure": True,
            "token_status": "SHARED_TOKEN_EXPIRED",
            "shared_token_age": 92,
            "expiry_policy": 90,
            "auth_failed_services": ["checkmarx", "ecr", "github"]
        },
        "action_tiers": {
            "observe":  ["detect_cross_service_auth_failure", "audit_credential_lifecycle"],
            "diagnose": ["identify_shared_token_dependency", "verify_credential_expiry_policy", "check_global_credential_sync_status"],
            "fix":      ["rotate_shared_service_credential"]
        },
        "irrelevant_actions": ["correct_branch_name", "increase_timeout"],
        "hint": "multi_service_failure=True + token_status=SHARED_TOKEN_EXPIRED. Rotate the global shared credential.",
        "resolution": "Rotate CI_SHARED_API_TOKEN globally."
    },
    {
        "id": "medium_004",
        "difficulty": "medium",
        "category": "npm",
        "pipeline_name": "react-frontend-build",
        "environment": "Dev",
        "failed_stage": "npm-install",
        "stage_number": 2,
        "error_message": "npm ERR! code ETIMEDOUT\nnpm ERR! syscall connect\nnpm ERR! errno ETIMEDOUT",
        "root_cause": "Corporate Artifactory proxy is down.",
        "context_data": {
            "proxy_host": "artifactory.internal",
            "proxy_status": "DOWN",
            "network_connectivity": "OK",
            "external_registry_access": "BLOCKED_BY_POLICY"
        },
        "action_tiers": {
            "observe":  ["check_artifactory_health"],
            "diagnose": ["verify_proxy_configuration"],
            "fix":      ["bypass_proxy_to_public_registry"]
        },
        "irrelevant_actions": ["clear_npm_cache", "refresh_github_token"],
        "hint": "ETIMEDOUT + proxy_status=DOWN. External access is BLOCKED_BY_POLICY. You must bypass the internal proxy or fix it.",
        "resolution": "Switch .npmrc to use public registry temporarily or wait for Artifactory recovery."
    },
    {
        "id": "hard_004",
        "difficulty": "hard",
        "category": "vpc",
        "pipeline_name": "data-processor-job",
        "environment": "Prod",
        "failed_stage": "ecs-task-launch",
        "stage_number": 6,
        "error_message": "ECS Task failed to launch: Insufficient capacity",
        "root_cause": "Subnet IP address exhaustion (CIDR full).",
        "context_data": {
            "vpc_id": "vpc-0abc123",
            "subnet_ids": ["subnet-1", "subnet-2"],
            "available_ips": 0,
            "ip_exhaustion_detected": True,
            "az": "us-east-1a",
            "capacity_provider": "FARGATE"
        },
        "action_tiers": {
            "observe":  ["read_vpc_flow_logs", "check_subnet_available_ips"],
            "diagnose": ["detect_cidr_exhaustion", "verify_network_interface_limits", "analyze_vpc_cidr_utilization"],
            "fix":      ["add_secondary_cidr_to_vpc"]
        },
        "irrelevant_actions": ["increase_ecs_task_cpu", "refresh_aws_credentials"],
        "hint": "available_ips=0 in subnet. The network is full. Add more CIDR capacity.",
        "resolution": "Add a secondary CIDR block and a new subnet to the VPC."
    },
    {
        "id": "hard_005",
        "difficulty": "hard",
        "category": "terraform",
        "pipeline_name": "infra-prod-deploy",
        "environment": "Prod",
        "failed_stage": "terraform-plan",
        "stage_number": 4,
        "error_message": "Error acquiring the state lock: 423 Locked",
        "root_cause": "Stale Terraform state lock in DynamoDB from crashed previous run.",
        "context_data": {
            "lock_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
            "lock_info_present": True,
            "dynamodb_status": "ACTIVE",
            "last_lock_owner": "jenkins-slave-732",
            "lock_age_hours": 14
        },
        "action_tiers": {
            "observe":  ["read_terraform_lock_info", "query_dynamodb_lock_table"],
            "diagnose": ["detect_stale_tf_lock", "verify_lock_owner_process_status", "confirm_lock_owner_is_offline"],
            "fix":      ["force_unlock_terraform_state"]
        },
        "irrelevant_actions": ["retry_terraform_plan", "refresh_github_token"],
        "hint": "423 Locked + lock_age_hours=14. The previous process crashed. Force-unlock using the Lock ID.",
        "resolution": "Run terraform force-unlock <LOCK_ID> to clear the stale entry."
    }
]

def get_contextual_actions(scenario: dict) -> list:
    """Build context-aware action pool: correct path + distractors."""
    actions = set()
    tiers = scenario.get("action_tiers", {})
    for t in tiers.values():
        actions.update(t)
    actions.update(scenario.get("irrelevant_actions", []))
    return sorted(list(actions))