# Transactional Repair

Full SQLite backup via `Connection.backup`, SHA-256, integrity_check. Apply in one transaction. Rollback restores entire adaptive DB state; logical_state_hash compared.
