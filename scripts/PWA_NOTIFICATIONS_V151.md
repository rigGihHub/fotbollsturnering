# CupNavi PWA & notifications v151

## Implemented now
- Verified email subscriptions per followed team.
- Separate preferences for schedule/venue changes, results and organizer information.
- Confirmation link before activation.
- Unsubscribe link in every notification email.
- Notification is persisted in CupNavi before SMTP is attempted.
- Delivery log is persisted.
- PWA manifest scaffold is included.

## Deliberately not claimed
Full browser Web Push is not enabled in the Streamlit frontend. A production service
worker must control the public app scope, which Streamlit static serving does not
reliably provide. This should be enabled in the future PWA/Next.js public frontend
or through appropriate root-level reverse-proxy hosting.
