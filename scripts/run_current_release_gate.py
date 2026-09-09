#!/usr/bin/env python3
"""Run the CupNavi current-release verification gate.

The repository intentionally retains hundreds of release-specific historical
contract tests. Many assert an exact old VERSION.txt or exact UI source text;
they are useful archaeology, but cannot be a meaningful gate for a later
release. This runner keeps those tests intact and instead executes:

1. compileall,
2. all evergreen/non-release-specific test modules,
3. a current replacement for the one superseded weather-default contract,
4. selected recent v540-v564 functional/safety contracts (not version pins or superseded UI labels),
5. current UX/product contracts through v602, using semantic replacements instead of stale version/text pins.

A failing selected test is a release blocker. Historical tests are not deleted
or rewritten just to make the suite green.
"""
from __future__ import annotations

import compileall
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    if not compileall.compile_dir(ROOT / "cupnavi_core", quiet=1):
        print("compileall failed", file=sys.stderr)
        return 1
    if not compileall.compile_file(ROOT / "app.py", quiet=1):
        print("app.py compile failed", file=sys.stderr)
        return 1

    evergreen = sorted(
        str(path.relative_to(ROOT))
        for path in TESTS.glob("test_*.py")
        if not path.name.startswith("test_v")
        and not path.name.startswith("test_current_release_gate_v")
    )

    # v90 expected weather-on-by-default. Since v528 the deliberate performance
    # contract is opt-in weather; v549 tests the current behavior explicitly.
    deselect = [
        "--deselect=tests/test_performance_v90.py::test_weather_is_on_by_default_but_user_can_toggle_it",
        # v106 hardcodes the indentation of the old shared-password login. v554
        # replaces that UI with organizer accounts while retaining the rerun
        # safety behavior; the current contract verifies the new flow.
        "--deselect=tests/test_team_privacy_v106.py::test_successful_logins_rerun_to_hide_credentials",
    ]
    run([sys.executable, "-m", "pytest", *evergreen, *deselect])

    recent_nodes = [
        # Imported-schedule safety and public summary integrity.
        "tests/test_v540_imported_schedule_repair_and_summary_fix.py",
        # Automatic highlights, excluding the historical version pin.
        "tests/test_v541_restore_public_highlights.py::test_top_scorer_is_automatic_again",
        "tests/test_v541_restore_public_highlights.py::test_partial_server_batch_does_not_fake_team_rankings",
        # Actionable schedule errors.
        "tests/test_v543_actionable_schedule_errors.py::test_issue_match_numbers_extract_single_and_pair",
        "tests/test_v543_actionable_schedule_errors.py::test_actionable_error_cards_open_manual_editor",
        # Reporter correction/push safety.
        "tests/test_v544_mobile_reporter_grace_window.py::test_v544_goal_push_waits_and_supersedes_latest_edit",
        # Current one-screen, setup-gated and large-touch reporter behavior.
        "tests/test_v545_one_screen_mobile_match_control.py::test_v545_large_mobile_controls_and_match_identity",
        "tests/test_v546_setup_driven_reporter_controls.py::test_reporter_sections_follow_setup_flags",
        "tests/test_v546_setup_driven_reporter_controls.py::test_each_player_event_control_is_individually_gated",
        "tests/test_v546_setup_driven_reporter_controls.py::test_reporter_missing_flag_defaults_do_not_expose_optional_events",
        "tests/test_v547_big_scoreboard_reporter_ui.py::test_big_scoreboard_has_large_touch_targets",
        "tests/test_v547_big_scoreboard_reporter_ui.py::test_setup_driven_event_gates_survive_scoreboard_redesign",
        "tests/test_v547_big_scoreboard_reporter_ui.py::test_correction_window_survives_scoreboard_redesign",
        "tests/test_v548_reporter_network_resilience.py::test_reporter_has_explicit_save_states",
        "tests/test_v548_reporter_network_resilience.py::test_reporter_has_live_browser_network_probe",
        "tests/test_v548_reporter_network_resilience.py::test_uncertain_write_requires_server_refresh_not_automatic_retry",
        "tests/test_v548_reporter_network_resilience.py::test_existing_safety_contracts_are_retained",
        "tests/test_current_release_gate_v554.py::test_v33_creates_account_and_membership_schema",
        "tests/test_current_release_gate_v554.py::test_admin_list_is_membership_scoped_for_organizers",
        "tests/test_current_release_gate_v554.py::test_every_selected_admin_tournament_has_server_side_guard",
        "tests/test_current_release_gate_v554.py::test_new_cups_and_copies_are_owned_by_current_account",
        "tests/test_current_release_gate_v554.py::test_passwords_are_scrypt_hashed_and_superadmin_is_separate",
        "tests/test_current_release_gate_v554.py::test_previous_v553_admin_flow_and_smart_import_survive",
        "tests/test_current_release_gate_v554.py::test_successful_account_and_superadmin_login_rerun_after_credentials",
        "tests/test_current_release_gate_v556.py::test_halftime_copy_uses_halves_periods",
        "tests/test_current_release_gate_v556.py::test_halftime_control_is_conditional_on_two_or_more_periods",
        "tests/test_current_release_gate_v556.py::test_v555_behaviour_is_retained",
        "tests/test_current_release_gate_v558.py::test_show_more_matches_updates_limit_then_forces_parent_app_rerun",
        "tests/test_current_release_gate_v558.py::test_v557_schedule_and_rules_fixes_are_retained",
        "tests/test_current_release_gate_v559.py::test_v559_environment_switch_and_public_safety",
        "tests/test_current_release_gate_v560.py::test_bare_public_root_is_marketing_home",
        "tests/test_current_release_gate_v560.py::test_direct_cup_link_bypasses_marketing_home",
        "tests/test_current_release_gate_v560.py::test_marketing_home_can_surface_live_and_upcoming_cups",
        "tests/test_current_release_gate_v560.py::test_v559_environment_and_public_safety_is_retained",
        "tests/test_current_release_gate_v561.py::test_only_owner_or_superadmin_can_manage_other_admins",
        "tests/test_current_release_gate_v561.py::test_new_local_admin_gets_scrypt_hashed_temporary_password",
        "tests/test_current_release_gate_v561.py::test_owner_membership_cannot_be_removed_by_local_admin_tool",
        "tests/test_current_release_gate_v561.py::test_current_organizer_can_change_own_password",
        "tests/test_current_release_gate_v562.py::test_membership_snapshot_exposes_current_users_role",
        "tests/test_current_release_gate_v562.py::test_admin_login_lands_on_my_cups_dashboard",
        "tests/test_current_release_gate_v562.py::test_environment_remains_server_side_scope_for_my_cups",
        "tests/test_current_release_gate_v562.py::test_open_from_dashboard_goes_directly_into_selected_cup",
        "tests/test_current_release_gate_v562.py::test_dashboard_keeps_create_and_full_list_paths",
        "tests/test_current_release_gate_v563.py::test_v34_creates_secure_invitation_schema",
        "tests/test_current_release_gate_v563.py::test_invitation_uses_hash_expiry_and_email_binding",
        "tests/test_current_release_gate_v563.py::test_invitation_link_opens_admin_and_can_create_profile",
        "tests/test_current_release_gate_v563.py::test_owner_can_create_track_and_revoke_pending_invites",
        "tests/test_current_release_gate_v563.py::test_acceptance_grants_only_invited_tournament_admin_membership",
        "tests/test_v564_admin_ux_expert_polish.py::test_v564_secondary_tools_do_not_compete_with_numbered_flow",
        "tests/test_v564_admin_ux_expert_polish.py::test_v564_access_center_has_task_tabs",
        "tests/test_v564_admin_ux_expert_polish.py::test_v564_current_step_gets_compact_visual_hierarchy",
        "tests/test_v565_decision_driven_admin_overview.py::test_v565_points_to_first_missing_setup_step",
        "tests/test_v565_decision_driven_admin_overview.py::test_v565_unassigned_team_keeps_groups_incomplete",
        "tests/test_v565_decision_driven_admin_overview.py::test_v565_requires_explicit_control_before_claiming_publish_ready",
        "tests/test_v565_decision_driven_admin_overview.py::test_v565_fresh_clean_validation_can_claim_publish_ready",
        "tests/test_v565_decision_driven_admin_overview.py::test_v565_validation_errors_keep_publication_blocked",
        "tests/test_v565_decision_driven_admin_overview.py::test_v565_dirty_schedule_is_actionable_and_never_publish_ready",
        "tests/test_current_release_gate_v566.py::test_planning_has_dedicated_route",
        "tests/test_current_release_gate_v566.py::test_schedule_dirty_when_capacity_or_windows_change",
        "tests/test_current_release_gate_v566.py::test_admin_overview_routes_missing_pitches_to_dedicated_page",
        "tests/test_current_release_gate_v567.py::test_schema_starts_with_explicit_user_intent",
        "tests/test_current_release_gate_v567.py::test_existing_schedule_defaults_to_safe_non_destructive_path",
        "tests/test_current_release_gate_v567.py::test_regeneration_requires_explicit_path_and_confirmation",
        "tests/test_current_release_gate_v567.py::test_import_and_manual_editor_are_progressively_disclosed",
        "tests/test_current_release_gate_v568.py::test_mobile_first_screen_uses_compact_stepper",
        "tests/test_current_release_gate_v568.py::test_all_nine_steps_remain_directly_accessible",
        "tests/test_current_release_gate_v568.py::test_responsive_shell_switch_is_css_only",
        "tests/test_current_release_gate_v568.py::test_v567_safe_schedule_choice_survives",
        "tests/test_current_release_gate_v569.py",
        "tests/test_current_release_gate_v570.py::test_control_contains_real_visitor_facing_preview",
        "tests/test_current_release_gate_v570.py::test_preview_exposes_public_information_architecture",
        "tests/test_current_release_gate_v570.py::test_preview_still_shows_core_content_before_publish",
        "tests/test_current_release_gate_v570.py::test_control_still_keeps_publish_as_separate_deliberate_step",
        "tests/test_current_release_gate_v571.py::test_v571_has_canonical_tokens_and_primary_secondary_hierarchy",
        "tests/test_current_release_gate_v571.py::test_v571_unifies_forms_cards_status_navigation_and_empty_states",
        "tests/test_current_release_gate_v571.py::test_v571_mobile_and_accessibility_contracts",
        "tests/test_current_release_gate_v571.py::test_v570_preview_contract_is_retained",
        "tests/test_current_release_gate_v572.py::test_kit_setup_remains_editable_later_from_team_page",
        "tests/test_current_release_gate_v573.py::test_color_clashes_are_information_only",
        "tests/test_current_release_gate_v574.py::test_v574_can_strip_common_youth_suffixes_without_claiming_identity",
        "tests/test_current_release_gate_v574.py::test_v574_single_team_scan_keeps_tournament_context_and_hint",
        "tests/test_current_release_gate_v575.py::test_cupinfo_explains_now_later_and_advanced",
        "tests/test_current_release_gate_v576.py::test_photo_import_supports_multiple_images_and_requires_review",
        "tests/test_current_release_gate_v576.py::test_photo_import_reuses_ai_document_extraction_and_never_silently_overwrites_groups",
        "tests/test_current_release_gate_v576.py::test_group_photo_import_matches_only_registered_team_names_and_surfaces_unmatched_rows",
        "tests/test_current_release_gate_v577.py::test_initial_scan_explicitly_carries_groups_forward_to_step_three",
        "tests/test_current_release_gate_v577.py::test_initial_team_import_defers_group_assignment_unless_imported_schedule_needs_it",
        "tests/test_current_release_gate_v577.py::test_later_group_apply_is_review_first_and_never_overwrites_existing_groups",
        "tests/test_current_release_gate_v577.py::test_snapshot_helpers_roundtrip_and_group_apply",
        "tests/test_v578_initial_import_plans_rules.py::test_rules_reused",
        "tests/test_v578_initial_import_plans_rules.py::test_plans_reused",
        "tests/test_v578_initial_import_plans_rules.py::test_no_fake_opening_hours",
        "tests/test_v578_initial_import_plans_rules.py::test_structured_rules_are_explicit",
        "tests/test_v578_initial_import_plans_rules.py::test_helpers_exist",
        "tests/test_v579_initial_import_overview.py::test_overview_is_review_first_not_fake_import_status",
        "tests/test_v579_initial_import_overview.py::test_overview_covers_setup_sections",
        "tests/test_v579_initial_import_overview.py::test_overview_surfaces_found_and_missing_separately",
        "tests/test_v579_initial_import_overview.py::test_overview_counts_actual_extracted_content",
        "tests/test_v579_initial_import_overview.py::test_warnings_remain_visible",
        "tests/test_v580_import_source_kit_shirts.py::test_kit_preview_uses_shirt_silhouette_not_rectangle_swatch",
        "tests/test_v580_import_source_kit_shirts.py::test_table_swatch_reuses_shirt_svg",
        "tests/test_v580_import_source_kit_shirts.py::test_shirt_supports_all_current_patterns",
        "tests/test_v580_import_source_kit_shirts.py::test_admin_overview_keeps_initial_import_available",
        "tests/test_v581_revision_import_playoff_rules.py::test_revised_document_extraction_supports_pitch_and_playoff_specific_rules",
        "tests/test_v581_revision_import_playoff_rules.py::test_playoff_can_have_own_match_duration_and_falls_back_to_group_rules",
        "tests/test_v581_revision_import_playoff_rules.py::test_v36_persists_playoff_timing_overrides",
        "tests/test_v581_revision_import_playoff_rules.py::test_revision_helpers_only_use_explicit_values_and_normalize_tie_rules",
        "tests/test_v581_revision_import_playoff_rules.py::test_kit_verification_status_is_admin_only_and_home_away_are_side_by_side",
        "tests/test_v582_revision_structure_diff.py::test_team_add_remove_and_group_move_are_detected",
        "tests/test_v582_revision_structure_diff.py::test_match_time_and_pitch_change_is_not_reported_as_remove_plus_add",
        "tests/test_v582_revision_structure_diff.py::test_added_and_removed_fixtures_are_detected_conservatively",
        "tests/test_v582_revision_structure_diff.py::test_colour_and_squad_suffixes_are_not_stripped_from_team_identity",
        "tests/test_v583_match_level_revision_approval.py::test_changed_unchanged_new_removed_are_classified",
        "tests/test_v583_match_level_revision_approval.py::test_played_match_is_never_safe_to_apply",
        "tests/test_v583_match_level_revision_approval.py::test_time_change_keeps_existing_match_date",
        "tests/test_v583_match_level_revision_approval.py::test_new_and_removed_matches_are_not_automatically_applied",
        "tests/test_v584_revision_consequence_preview.py::test_pitch_and_team_overlap_block_selected_change",
        "tests/test_v584_revision_consequence_preview.py::test_collective_selected_changes_are_evaluated_together",
        "tests/test_v584_revision_consequence_preview.py::test_referee_overlap_blocks_even_on_different_pitches",
        "tests/test_v584_revision_consequence_preview.py::test_confirmed_pitch_window_blocks_outside_availability",
        "tests/test_v584_revision_consequence_preview.py::test_short_rest_is_warning_not_hard_block",
        "tests/test_v585_revision_fix_suggestions.py",
        "tests/test_v586_multi_match_revision_repair.py",
        "tests/test_v587_flow_ux_expert_pass.py::test_shared_control_publish_route_keeps_correct_visible_step",
        "tests/test_v587_flow_ux_expert_pass.py::test_global_flow_suppresses_duplicate_workspace_flow",
        "tests/test_v587_flow_ux_expert_pass.py::test_control_back_button_uses_real_schema_route",
        "tests/test_v587_flow_ux_expert_pass.py::test_revision_source_is_visible_from_overview_and_not_participant_scoped",
        "tests/test_v588_admin_overview_3.py::test_overview_first_screen_answers_three_questions",
        "tests/test_v588_admin_overview_3.py::test_only_primary_blocker_is_expanded_by_default",
        "tests/test_v588_admin_overview_3.py::test_revision_import_and_operational_attention_are_progressively_disclosed",
        "tests/test_v588_admin_overview_3.py::test_advanced_overview_does_not_duplicate_step_guide",
        "tests/test_v589_team_flow_ux_pass.py::test_team_page_has_one_clear_core_task_before_optional_tools",
        "tests/test_v589_team_flow_ux_pass.py::test_optional_team_details_and_roster_import_are_progressively_disclosed",
        "tests/test_v589_team_flow_ux_pass.py::test_registered_team_list_defaults_to_setup_relevant_fields_only",
        "tests/test_current_release_gate_v596.py::test_app_import_contract_names_exist",
        "tests/test_current_release_gate_v597.py::test_current_plan_flow_replaces_superseded_v566_copy_without_losing_requirements",
        "tests/test_current_release_gate_v597.py::test_referees_remain_explicitly_optional_and_have_one_forward_handoff",
        "tests/test_current_release_gate_v597.py::test_schedule_navigation_matches_current_nine_step_flow_and_protects_existing_work",
        "tests/test_current_release_gate_v597.py::test_rules_current_copy_preserves_progressive_disclosure_and_played_match_safety",
        "tests/test_current_release_gate_v597.py::test_team_flow_semantics_survive_without_historical_version_pin",
        "tests/test_current_release_gate_v598.py::test_texttv_is_full_black_data_surface",
        "tests/test_current_release_gate_v598.py::test_texttv_keeps_accessible_headers_and_color_not_alone",
        "tests/test_current_release_gate_v598.py::test_kit_feature_is_promoted",
        "tests/test_current_release_gate_v599.py::test_desktop_density_layer_is_last_design_override",
        "tests/test_current_release_gate_v599.py::test_kit_feature_is_prominent_and_direct",
        "tests/test_current_release_gate_v599.py::test_mobile_guard_preserved",
        "tests/test_current_release_gate_v600.py::test_v600_shell_injected_after_v599",
        "tests/test_current_release_gate_v600.py::test_public_shell_visual_contract",
        "tests/test_current_release_gate_v600.py::test_kit_discovery_preserved",
        "tests/test_current_release_gate_v601.py::test_v601_uses_fast_two_pass_search_and_cache",
        "tests/test_current_release_gate_v601.py::test_v601_requires_kit_specific_sources_for_verification",
        "tests/test_current_release_gate_v601.py::test_v601_parallelises_whole_tournament_scan",
        "tests/test_current_release_gate_v601.py::test_v601_exposes_per_kit_evidence_and_keeps_manual_approval",
        "tests/test_current_release_gate_v602.py::test_ambiguous_club_identity_never_exposes_mixed_kit_colors",
        "tests/test_current_release_gate_v602.py::test_candidate_list_requires_real_source_urls_and_is_bounded",
        "tests/test_current_release_gate_v602.py::test_resolved_identity_is_part_of_search_context_and_cache_key",
        "tests/test_current_release_gate_v602.py::test_ui_forces_identity_choice_before_retrying_kit_search",
        "tests/test_current_release_gate_v603.py",
    ]
    run([sys.executable, "-m", "pytest", *recent_nodes])
    print("CURRENT RELEASE GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
