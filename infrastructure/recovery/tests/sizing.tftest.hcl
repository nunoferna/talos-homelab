# Offline plans only. No cloud credentials, backend access or real resources.
mock_provider "cloudflare" {}

variables {
  account_id                  = "00000000000000000000000000000000"
  bucket_name                 = "ci-recovery-fixture"
  state_bucket_name           = "ci-state-fixture"
  snapshot_size_bound_bytes   = 16777216
  other_account_storage_bytes = 0
}

run "poc_default_budgets_two_objects_not_a_schedule" {
  command = plan

  assert {
    condition     = output.backup_mode == "poc" && var.snapshots_per_day == 0
    error_message = "The default must be a PoC with no scheduled uploads."
  }

  assert {
    condition     = output.projected_storage_bytes == 41943040
    error_message = "PoC sizing must allow two 16 MiB objects plus 25% headroom."
  }

  assert {
    condition     = cloudflare_r2_bucket.snapshots.storage_class == "Standard" && cloudflare_r2_managed_domain.snapshots.enabled == false
    error_message = "The bucket must remain Standard with managed public access off."
  }
}

run "reject_a_cadence_in_poc_mode" {
  command = plan
  variables {
    snapshots_per_day = 24
  }
  expect_failures = [var.snapshots_per_day]
}

run "reject_unknown_mode" {
  command = plan
  variables {
    backup_mode = "disabled"
  }
  expect_failures = [var.backup_mode]
}

run "reject_fractional_account_byte_bound" {
  command = plan
  variables {
    other_account_storage_bytes = 0.5
  }
  expect_failures = [var.other_account_storage_bytes]
}

run "reject_zero_cadence_in_scheduled_mode" {
  command = plan
  variables {
    backup_mode = "scheduled"
  }
  expect_failures = [var.snapshots_per_day]
}

run "scheduled_mode_keeps_the_existing_headroom_model" {
  command = plan
  variables {
    backup_mode          = "scheduled"
    snapshots_per_day    = 24
    storage_budget_bytes = 5000000000
  }
  assert {
    condition     = output.projected_storage_bytes == 4529848320
    error_message = "Scheduled sizing must include cadence, nine retention/headroom days and 25%."
  }
}

run "reject_poc_that_exceeds_its_reserved_budget" {
  command = plan
  variables {
    snapshot_size_bound_bytes = 50000000
  }
  expect_failures = [cloudflare_r2_bucket.snapshots]
}

run "reject_account_usage_that_exceeds_planning_ceiling" {
  command = plan
  variables {
    other_account_storage_bytes = 7950000000
  }
  expect_failures = [cloudflare_r2_bucket.snapshots]
}

run "reject_targeting_the_state_bucket" {
  command = plan
  variables {
    bucket_name = "ci-state-fixture"
  }
  expect_failures = [var.bucket_name]
}
