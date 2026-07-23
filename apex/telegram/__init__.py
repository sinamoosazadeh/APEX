"""Telegram Console (Book IV) - Phase 12.

The control layer over the platform: command menus (status,
portfolio, positions, reports, health, the Optimization Center with
queue control, promotions and rollback, the Emergency Center with
the kill-switch surfaces), nonce-guarded double confirmation for
dangerous actions, role-gated access (admin/viewer, Book IV Part 1's
current-version scheme) and bus-driven proactive notifications. No
trading logic lives here - every action forwards to the owning
platform service (the Book IV Golden Rule).
"""
