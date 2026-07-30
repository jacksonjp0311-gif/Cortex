# Capability Boundary

`ExecutionCapability` is the only authority for adaptive mutations. Strings like `memory_controller="advanced"` describe intent but do not grant writes.

Unknown operation → deny. Missing capability → deny. Expired → deny.
