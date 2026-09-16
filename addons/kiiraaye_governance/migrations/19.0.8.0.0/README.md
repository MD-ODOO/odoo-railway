# Kiiraaye 19.0.8 migration

- pre: creates missing `res_users` columns before registry/schema synchronization.
- post: repairs legacy nullable geographic references, removes orphan hierarchy rows, and re-applies selected NOT NULL constraints.

The scripts are idempotent.
