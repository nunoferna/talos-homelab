locals {
  github_actions_oidc_audience = "talos-homelab-kubernetes"
  github_actions_repository_id = "1398543528"
  github_actions_workflow_ref  = "nunoferna/talos-homelab-gitops/.github/workflows/cilium-deploy.yaml@refs/heads/main"

  github_actions_authentication_config = {
    apiVersion = "v1alpha1"
    kind       = "KubeAuthenticationConfig"
    configuration = {
      apiVersion = "apiserver.config.k8s.io/v1"
      kind       = "AuthenticationConfiguration"
      anonymous = {
        enabled = true
        conditions = [
          { path = "/livez" },
          { path = "/readyz" },
          { path = "/healthz" },
        ]
      }
      jwt = [
        {
          issuer = {
            url       = "https://token.actions.githubusercontent.com"
            audiences = [local.github_actions_oidc_audience]
          }
          claimValidationRules = [
            {
              claim         = "repository_id"
              requiredValue = local.github_actions_repository_id
            },
            {
              claim         = "repository_visibility"
              requiredValue = "private"
            },
            {
              claim         = "ref"
              requiredValue = "refs/heads/main"
            },
            {
              claim         = "event_name"
              requiredValue = "workflow_dispatch"
            },
            {
              claim         = "workflow_ref"
              requiredValue = local.github_actions_workflow_ref
            },
            {
              expression = "claims.environment in ['cilium-plan', 'cilium-production']"
              message    = "GitHub Actions environment is not authorized"
            },
          ]
          claimMappings = {
            username = {
              expression = format(
                "'github-actions:%s:' + claims.environment",
                local.github_actions_repository_id,
              )
            }
          }
          userValidationRules = [
            {
              expression = format(
                "user.username in ['github-actions:%[1]s:cilium-plan', 'github-actions:%[1]s:cilium-production']",
                local.github_actions_repository_id,
              )
              message = "Mapped GitHub Actions user is not authorized"
            },
          ]
        },
      ]
    }
  }
}
