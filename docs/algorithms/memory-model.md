# Algorithm: Explicit Memory Merge

At VM startup:

1. initialize each declared memory from compiled literal defaults;
2. load repository-local persisted state if present;
3. merge persisted keys over defaults by memory and key;
4. execute `MEM_GET` and `MEM_SET` against the merged map;
5. sort memory and key names for stable human-readable persistence;
6. write a temporary UTF-8 JSON state file;
7. atomically replace the prior state file after successful execution.

Future event sourcing will append immutable facts and derive the current view rather than replacing a snapshot.
