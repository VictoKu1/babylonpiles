# Installer repair implementation plan

The user authorized repairing the confirmed repository review findings. This work covers the existing operator helper and its documentation; other workers own application services.

1. Add fixture tests for independent storage roots, preserved Compose settings, sparse drive IDs, symlinks, validation ordering, rollback, authenticated HTTP errors, and safe fstab generation. Run them against the old implementation and record the failures.
2. Replace shell YAML editing with `scripts/manage_storage.py`. Read normalized Compose configuration on each invocation, apply a separate managed storage map, validate before filesystem mutations, use dedicated content directories, and recreate storage with authenticated verification.
3. Preserve local block-device and persistent mount support through detected UUID/filesystem values, validated fstab candidates, and rollback. Never recursively change existing disk ownership or remove user data.
4. Keep `babylonpiles.sh` as the interactive entry point. Correct help, startup, Compose detection, credentials, test paths, and error reporting.
5. Correct deployment/authentication instructions and remove the incompatible privileged Raspberry Pi override. Keep historical feature lists aligned with actual support.
6. Run fixture tests, shell syntax checks, and offline Python compilation in an existing container with the repository mounted read-only and networking disabled. No live application stack or host storage changes.
