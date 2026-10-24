# Examples: Sample Inputs and Outputs

This directory contains representative inputs and end-to-end multi-agent audit outputs for three distinct user profiles audited by Digital Doppelgänger.

## Profiles

1. **Profile A (Suburban Fitness Enthusiast)**
   - **Input**: [`inputs/profile_A_sample_input.json`](inputs/profile_A_sample_input.json) (Strava GPS telemetry, food delivery addresses, Google Calendar work meetings).
   - **Output**: [`outputs/privacy_audit_profile_A.json`](outputs/privacy_audit_profile_A.json) / [Markdown](outputs/privacy_audit_profile_A.md).
   - **Key Finding**: GPS cluster intersects food delivery coordinates, pinpointing home residence and revealing empty-home vacation window.

2. **Profile B (Corporate Executive / Patient)**
   - **Input**: [`inputs/profile_B_sample_input.json`](inputs/profile_B_sample_input.json) (Specialist clinic calendar appointments, pharmacy delivery orders).
   - **Output**: [`outputs/privacy_audit_profile_B.json`](outputs/privacy_audit_profile_B.json) / [Markdown](outputs/privacy_audit_profile_B.md).
   - **Key Finding**: Oncology consultation location coupled with anti-emetic medications exposes underwriting/insurance risk while clinical lymphoma diagnosis is rejected by Verifier as ungrounded speculation.

3. **Profile C (Content Creator / Tech Lead)**
   - **Input**: [`inputs/profile_C_sample_input.json`](inputs/profile_C_sample_input.json) (Public social media posts, birthday dinner calendar event, profile fields).
   - **Output**: [`outputs/privacy_audit_profile_C.json`](outputs/privacy_audit_profile_C.json) / [Markdown](outputs/privacy_audit_profile_C.md).
   - **Key Finding**: Social posts reveal banking Knowledge-Based Authentication (KBA) answers (DOB, pet name, elementary school), while speculative maiden name claim is rejected.
