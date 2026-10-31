"""
Comprehensive Technical Skill Tracks & Topic Directory for AI Mock Interview Simulator.
Covers SQL, Python, C Language, DSA, Java, C++, JavaScript/TypeScript, and System Design.
"""

from typing import Dict, Any, List, Optional

TECHNICAL_SKILL_TRACKS: Dict[str, Dict[str, Any]] = {
    "sql": {
        "key": "sql",
        "name": "SQL & Database Engineering",
        "short_name": "SQL",
        "icon": "bi-database-fill-gear",
        "badge_class": "bg-primary-subtle text-primary border border-primary-subtle",
        "color": "#0d6efd",
        "tagline": "Master advanced queries, window functions, indexing, ACID transactions & high-throughput scaling.",
        "description": "Comprehensive SQL and database architecture interview preparation. Covers query plans, execution internals, window aggregates, CTEs, transactional isolation levels, normalization, and distributed database scaling.",
        "topics": [
            {
                "key": "window_functions",
                "name": "Window Functions & Analytical Aggregates",
                "difficulty": "Intermediate / Advanced",
                "summary": "Master ROW_NUMBER(), RANK(), DENSE_RANK(), LEAD(), LAG(), NTILE(), running sums, and sliding window frames (ROWS BETWEEN).",
                "core_concepts": [
                    "ROW_NUMBER() vs RANK() vs DENSE_RANK() handling of ties",
                    "PARTITION BY vs GROUP BY execution semantics",
                    "LEAD() and LAG() with default fallback values for period comparisons",
                    "Sliding frame bounds (ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)",
                    "Performance implications of multiple distinct OVER() clauses"
                ],
                "sample_question": "Explain the difference between ROW_NUMBER(), RANK(), and DENSE_RANK(). When would you use DENSE_RANK() over RANK() in a production reporting system, and how does the SQL engine manage the partitioning buffer in memory?",
                "question_type": "Technical Deep Dive & Optimization",
                "evaluation_criteria": "Candidate clearly explains tie handling, gives concrete examples (e.g., employee bonus ranking), and discusses window execution buffers.",
                "star_guide": {
                    "situation": "Describe a scenario requiring analytical rankings or moving averages across high-volume transactions.",
                    "task": "Explain the business requirement to compute rankings without collapsing rows via GROUP BY.",
                    "action": "Detail your choice of window function, PARTITION BY keys, ORDER BY sorting, and frame specifications.",
                    "result": "Quantify query performance and accurate reporting deliverables."
                },
                "coding_challenge": {
                    "title": "Top-N Department Earners with Window Functions",
                    "problem": "Write a query to find the top 2 highest-earning employees in each department. If there are salary ties, both employees must be included without skipping the subsequent rank.",
                    "starter_code": "WITH RankedSalaries AS (\n    SELECT \n        employee_id, \n        department_id, \n        salary,\n        DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) as rnk\n    FROM employees\n)\nSELECT employee_id, department_id, salary\nFROM RankedSalaries\nWHERE rnk <= 2;"
                }
            },
            {
                "key": "complex_joins",
                "name": "Complex Joins, Self-Joins & Set Operations",
                "difficulty": "Intermediate",
                "summary": "Deep dive into INNER, LEFT, RIGHT, FULL OUTER, CROSS joins, anti-joins (NOT EXISTS vs LEFT JOIN WHERE IS NULL), and UNION vs UNION ALL.",
                "core_concepts": [
                    "Hash Join vs Nested Loop Join vs Merge Join mechanics",
                    "Anti-join optimization: NOT EXISTS vs NOT IN with NULL values trap",
                    "Self-joins for hierarchical tree or graph traversal",
                    "Cartesian explosion risks with CROSS joins and non-unique join keys",
                    "UNION (deduplication sort/hash) vs UNION ALL performance"
                ],
                "sample_question": "Why can 'NOT IN (SELECT id FROM ...)' return unexpected results when the subquery contains a NULL, and how does the optimizer execute 'NOT EXISTS' differently than an outer anti-join?",
                "question_type": "Technical & Edge Cases",
                "evaluation_criteria": "Understanding 3-valued boolean logic in SQL (TRUE, FALSE, UNKNOWN) and how NULL in NOT IN causes total query suppression.",
                "star_guide": {
                    "situation": "A reporting query was dropping rows unexpectedly or running out of memory during a join.",
                    "task": "Audit the join condition and subquery logic for three-valued logic edge cases.",
                    "action": "Refactored from NOT IN to NOT EXISTS or LEFT JOIN WHERE ... IS NULL and verified the query plan.",
                    "result": "Eliminated missing records and sped up query execution by 4x."
                }
            },
            {
                "key": "indexing_optimization",
                "name": "Indexing Architecture & Query Optimization",
                "difficulty": "Advanced",
                "summary": "B-Tree indexes, Hash indexes, composite indexes, left-most prefix rule, index selectivity, covering indexes, and EXPLAIN ANALYZE interpretation.",
                "core_concepts": [
                    "B-Tree index structure: root, branch, leaf pages and row pointer lookups",
                    "Composite index column order and left-most prefix matching rule",
                    "Index Seek vs Index Scan vs Sequential / Full Table Scan",
                    "Covering indexes (INCLUDE clause) to eliminate table heap fetches",
                    "Detecting index bloat and understanding when an index degrades write throughput"
                ],
                "sample_question": "Suppose you have a table with 50 million rows and a query filtering by 'status', 'created_at', and sorting by 'user_id'. How would you design a composite index, and what does EXPLAIN ANALYZE tell you about whether a Bitmap Index Scan is occurring?",
                "question_type": "System Performance & Tuning",
                "evaluation_criteria": "Candidate identifies column cardinality/selectivity, equality-before-range rule for composite indexing, and explains heap fetches.",
                "star_guide": {
                    "situation": "Production query latency spiked to 4.5 seconds under high read load.",
                    "task": "Diagnose the slow query using EXPLAIN ANALYZE and design an optimal index.",
                    "action": "Analyzed selectivity, added a composite covering index matching the WHERE and ORDER BY clauses.",
                    "result": "Reduced latency from 4500ms down to 18ms and CPU utilization dropped by 65%."
                }
            },
            {
                "key": "acid_transactions",
                "name": "Transactions, ACID & Concurrency Isolation",
                "difficulty": "Advanced",
                "summary": "Atomicity, Consistency, Isolation, Durability, isolation levels (Read Committed, Repeatable Read, Serializable), dirty reads, non-repeatable reads, phantom reads, and MVCC.",
                "core_concepts": [
                    "ACID guarantees in relational databases",
                    "The 4 ANSI SQL isolation levels and the anomalies they permit/prevent",
                    "Multi-Version Concurrency Control (MVCC) in PostgreSQL/MySQL InnoDB",
                    "Row-level locking vs Table locks vs Intent locks",
                    "Deadlock detection, resolution, and transaction retry strategies"
                ],
                "sample_question": "Walk me through how MVCC works in PostgreSQL or InnoDB when two transactions attempt to update the same row simultaneously. What is a phantom read, and which isolation level prevents it?",
                "question_type": "Database Internals & Concurrency",
                "evaluation_criteria": "Accurate explanation of write locks, snapshot isolation, transaction visibility horizon (xmin/xmax), and Serializable isolation.",
                "star_guide": {
                    "situation": "A financial payment processing service encountered race conditions and occasional deadlocks during flash sales.",
                    "task": "Enforce strict balance consistency without locking down entire tables.",
                    "action": "Selected Repeatable Read / Serializable isolation, implemented SELECT ... FOR UPDATE with optimistic retry loops.",
                    "result": "Zero duplicate balance deductions and eliminated deadlock crashes completely."
                }
            },
            {
                "key": "ctes_recursive",
                "name": "CTEs, Subqueries & Recursive Queries",
                "difficulty": "Intermediate / Advanced",
                "summary": "Common Table Expressions, readability vs optimization fences, and recursive CTEs for hierarchical tree and graph data.",
                "core_concepts": [
                    "Non-recursive CTEs vs inline derived tables",
                    "PostgreSQL MATERIALIZED vs NOT MATERIALIZED CTEs",
                    "Recursive CTE syntax: Anchor member, UNION ALL, and Recursive member",
                    "Detecting and preventing infinite recursion cycles in graph paths",
                    "Correlated subqueries vs LATERAL joins"
                ],
                "sample_question": "How does a recursive CTE work under the hood? Write or explain a recursive query that traverses an organizational reporting hierarchy from CEO down to junior engineers.",
                "question_type": "Algorithmic SQL & Data Modeling",
                "evaluation_criteria": "Explains the working table / intermediate queue buffer and terminating condition.",
                "star_guide": {
                    "situation": "Needed to query deeply nested category trees or permission hierarchies in real-time.",
                    "task": "Avoid multiple roundtrip ORM queries to fetch parent-child nodes.",
                    "action": "Wrote an optimized recursive CTE calculating depth and path string in a single query.",
                    "result": "Reduced database round-trips from N+1 down to 1, cutting API response time by 85%."
                }
            },
            {
                "key": "normalization_design",
                "name": "Database Normalization, Modeling & Constraints",
                "difficulty": "Intermediate",
                "summary": "1NF through BCNF, relational data integrity, primary/foreign/surrogate keys, check constraints, and intentional denormalization trade-offs.",
                "core_concepts": [
                    "1NF (atomic values), 2NF (full functional dependency), 3NF (transitive dependency removal)",
                    "Boyce-Codd Normal Form (BCNF) nuances",
                    "Surrogate keys (UUID, BIGSERIAL) vs Natural keys trade-offs",
                    "Foreign key constraints and CASCADE vs RESTRICT vs SET NULL policies",
                    "Strategic denormalization for read-heavy OLAP vs write-heavy OLTP"
                ],
                "sample_question": "Explain a scenario where strictly adhering to 3NF hurts high-throughput read performance. How do you decide when to strategically denormalize, and how do you prevent data inconsistency?",
                "question_type": "Data Architecture & Schema Design",
                "evaluation_criteria": "Balance between normalization integrity and read optimization (e.g. read replicas, caching, event-driven sync).",
                "star_guide": {
                    "situation": "High-volume analytics dashboards required joining 7 normalized tables on every page load.",
                    "task": "Improve read throughput while safeguarding source transactional consistency.",
                    "action": "Maintained 3NF on OLTP master, introduced an asynchronously updated summary table / materialized view for the dashboard.",
                    "result": "Dashboard queries accelerated from 1200ms to 40ms without degrading transactional safety."
                }
            },
            {
                "key": "stored_procedures_triggers",
                "name": "Stored Procedures, Functions, Triggers & Views",
                "difficulty": "Intermediate / Advanced",
                "summary": "Procedural SQL, deterministic functions, audit triggers, security definers, and standard vs materialized views with refresh strategies.",
                "core_concepts": [
                    "Stored procedures vs User-Defined Functions (UDFs) differences",
                    "BEFORE vs AFTER triggers and row-level vs statement-level execution",
                    "Materialized views with CONCURRENT refresh mechanisms",
                    "Security implications of SECURITY DEFINER vs SECURITY INVOKER",
                    "Debugging procedural SQL and transaction management inside procedures"
                ],
                "sample_question": "What are the architectural trade-offs between implementing business logic inside database triggers versus in the application backend service? When are database audit triggers indispensable?",
                "question_type": "Architecture & Engineering Trade-offs",
                "evaluation_criteria": "Evaluates coupling, testability, application portability, vs zero-bypass compliance audit trails.",
                "star_guide": {
                    "situation": "Regulatory compliance required tamper-proof audit logging of all sensitive salary updates.",
                    "task": "Ensure every change is logged regardless of whether it originated from the app, an admin script, or direct CLI.",
                    "action": "Implemented an AFTER UPDATE row-level trigger that writes immutable audit deltas to a write-only log table.",
                    "result": "Passed SOC2 and ISO compliance audits with 100% data traceability."
                }
            },
            {
                "key": "sharding_replication",
                "name": "Database Sharding, Replication & High Availability",
                "difficulty": "Advanced",
                "summary": "Master-replica replication (sync vs async), read scaling, horizontal table sharding, connection pooling (PgBouncer), and distributed SQL engines.",
                "core_concepts": [
                    "Synchronous vs Asynchronous replication lag and split-brain risks",
                    "Read-replica routing and handling replication lag in user sessions",
                    "Sharding strategies: Hash-based, Range-based, and Directory-based",
                    "Cross-shard joins and distributed transactions (2-Phase Commit)",
                    "Connection pooling dynamics: session pooling vs transaction pooling"
                ],
                "sample_question": "How do you handle 'read-your-own-writes' consistency when your application sends writes to a primary database and reads to an asynchronous replica that suffers from replication lag?",
                "question_type": "Distributed Systems & Scalability",
                "evaluation_criteria": "Mentions pinning recent writers to primary for N seconds, monotonic read consistency, or version tokens.",
                "star_guide": {
                    "situation": "Users created a post and immediately refreshed, but couldn't see their post due to replica lag.",
                    "task": "Provide strict read-after-write consistency for the author without sending all read traffic to the primary database.",
                    "action": "Stored a last-write timestamp in the user's session cache and routed read requests to primary only if replica lag exceeded the timestamp delta.",
                    "result": "Eliminated ghost state user complaints while keeping 90% of read traffic on read replicas."
                }
            }
        ]
    },

    "python": {
        "key": "python",
        "name": "Python Systems & Backend Engineering",
        "short_name": "Python",
        "icon": "bi-filetype-py",
        "badge_class": "bg-success-subtle text-success border border-success-subtle",
        "color": "#198754",
        "tagline": "Master internal data structures, OOP & dunder methods, decorators, the GIL, asyncio & memory management.",
        "description": "Deep-dive Python engineering interview practice covering core internals, CPython implementation details, garbage collection, concurrency paradigms, asynchronous event loops, and clean scalable architecture.",
        "topics": [
            {
                "key": "core_internals",
                "name": "Data Structures & CPython Internals",
                "difficulty": "Intermediate / Advanced",
                "summary": "Hash tables behind dict/set, collision resolution with open addressing, dynamic array resizing for lists, and complexity guarantees.",
                "core_concepts": [
                    "CPython dict implementation: compact dicts, hash table array and entries table",
                    "Open addressing and perturbation collision resolution",
                    "List dynamic array over-allocation growth pattern (0, 4, 8, 16, 25...)",
                    "Tuples vs Lists: immutability, memory footprints, and free list caching",
                    "Time complexity: amortized O(1) lookups vs worst-case O(N) hash collisions"
                ],
                "sample_question": "How does CPython implement dictionaries under the hood since Python 3.6 to preserve insertion order and save memory? What happens when a hash collision occurs?",
                "question_type": "Language Internals & Algorithmic Mechanics",
                "evaluation_criteria": "Explains the separation of sparse index hash array and dense entries array, and open addressing probing.",
                "star_guide": {
                    "situation": "A high-frequency data ingestion pipeline was bottlenecked on serialization and dictionary lookups.",
                    "task": "Profile memory usage and lookup speed across millions of records per minute.",
                    "action": "Leveraged __slots__, tuned dictionary pre-sizing, and utilized tuples for fixed-shape records.",
                    "result": "Decreased memory usage by 45% and boosted processing throughput by 3x."
                }
            },
            {
                "key": "oop_dunder_mro",
                "name": "OOP, Dunder Methods & Method Resolution Order (MRO)",
                "difficulty": "Intermediate / Advanced",
                "summary": "Class vs instance state, __init__ vs __new__, operator overloading, multiple inheritance, C3 linearization algorithm, and super().",
                "core_concepts": [
                    "__new__ (object creation/allocator) vs __init__ (initialization)",
                    "__repr__ (unambiguous developer representation) vs __str__ (human readable)",
                    "Multiple inheritance and C3 Linearization (MRO)",
                    "Proper usage of super() in cooperative multiple inheritance",
                    "__call__, __getitem__, __setitem__, and custom container protocols"
                ],
                "sample_question": "Explain the difference between __new__ and __init__ in Python. When would you override __new__, and how does Python resolve method calls in multiple inheritance using C3 Linearization?",
                "question_type": "OOP & Object Lifecycle",
                "evaluation_criteria": "Mentions creating singletons, immutable subclasses (e.g. tuple/int subclassing), and explains MRO.",
                "star_guide": {
                    "situation": "Needed an extensible plugin architecture where plugins inherit behavior from multiple base classes.",
                    "task": "Prevent diamond inheritance method collisions and guarantee deterministic initialization.",
                    "action": "Implemented cooperative super() calls and verified class hierarchy using Class.mro().",
                    "result": "Shipped a clean extensible framework adopted across 12 microservices with zero inheritance bugs."
                }
            },
            {
                "key": "decorators_closures",
                "name": "Decorators, Closures & Scoping Rules",
                "difficulty": "Intermediate",
                "summary": "First-class functions, lexical closures, free variables, LEGB scoping, functools.wraps, and parameterized decorators.",
                "core_concepts": [
                    "Lexical closures and the __closure__ cell attributes",
                    "LEGB scoping rule: Local, Enclosing, Global, Built-in",
                    "Preserving function metadata (__name__, __doc__) with @functools.wraps",
                    "Writing decorators that accept optional or required arguments (3-layer functions)",
                    "Class-based decorators implementing __call__"
                ],
                "sample_question": "Write and explain a decorator that retries a failed function up to N times with exponential backoff and jitter. Why is @functools.wraps essential?",
                "question_type": "Design Patterns & Functional Programming",
                "evaluation_criteria": "Correct nesting structure (decorator factory -> decorator -> wrapper), proper args/kwargs forwarding, and metadata preservation.",
                "star_guide": {
                    "situation": "Downstream third-party API calls occasionally failed with transient network 503 errors.",
                    "task": "Create a reusable retry mechanism across dozens of API endpoints without code duplication.",
                    "action": "Authored a robust @retry_with_backoff decorator with configurable attempts, backoff factor, and logging.",
                    "result": "Reduced transient request failures by 98% and improved service reliability."
                }
            },
            {
                "key": "generators_iterators",
                "name": "Generators, Iterators & Memory Streaming",
                "difficulty": "Intermediate",
                "summary": "Iterator protocol (__iter__, __next__, StopIteration), yield, yield from, generator expressions, and processing multi-gigabyte files with O(1) memory.",
                "core_concepts": [
                    "Iterator protocol implementation and StopIteration signaling",
                    "Generator execution suspension and stack frame state preservation",
                    "yield from delegation for sub-generators and flattened pipelines",
                    "Generator methods: .send(), .throw(), and .close() for cooperative coroutines",
                    "Memory profiling streaming data vs loading entire lists into RAM"
                ],
                "sample_question": "How does a generator differ from a standard function in memory allocation? How would you use generators to process a 50GB log file on a machine with only 2GB of RAM?",
                "question_type": "Memory Optimization & Data Pipelines",
                "evaluation_criteria": "Explains lazy evaluation, line-by-line streaming, and avoidance of full-file materialization in memory.",
                "star_guide": {
                    "situation": "Worker nodes were terminating with OutOfMemory (OOM) errors while parsing massive CSV log dumps.",
                    "task": "Process 50GB data dumps reliably on container pods with 1.5GB memory limits.",
                    "action": "Refactored eager list comprehensions into generator pipelines streaming line-by-line with chunked yields.",
                    "result": "Memory consumption stayed constant under 80MB and OOM crashes dropped to zero."
                }
            },
            {
                "key": "gil_concurrency",
                "name": "The GIL, Multithreading & Multiprocessing",
                "difficulty": "Advanced",
                "summary": "Global Interpreter Lock mechanics, CPU-bound vs I/O-bound workloads, threading vs multiprocessing vs concurrent.futures, and shared memory.",
                "core_concepts": [
                    "Why the GIL exists in CPython (reference count thread safety)",
                    "I/O-bound operations releasing the GIL (sockets, file reads, C-extensions)",
                    "CPU-bound thread contention: why multithreading can slow down CPU tasks",
                    "multiprocessing module, IPC overhead, and process serialization (pickle)",
                    "ThreadPoolExecutor vs ProcessPoolExecutor selection criteria"
                ],
                "sample_question": "What is the Global Interpreter Lock (GIL) in CPython, and why does adding more threads to a CPU-bound Python script often make it run slower? When is threading actually effective?",
                "question_type": "Concurrency & Operating System Mechanics",
                "evaluation_criteria": "Clear distinction between I/O bound (network/disk waits releasing GIL) and CPU bound (GIL thrashing), process isolation vs threads.",
                "star_guide": {
                    "situation": "Image processing batch job took 45 minutes running on a 16-core server.",
                    "task": "Utilize all 16 cores effectively to shorten processing window.",
                    "action": "Switched from threading to ProcessPoolExecutor with shared memory arrays to avoid pickle serialization overhead.",
                    "result": "Execution time plunged from 45 minutes down to 3.2 minutes (14x speedup)."
                }
            },
            {
                "key": "asyncio_event_loop",
                "name": "Asynchronous Programming (asyncio & Coroutines)",
                "difficulty": "Advanced",
                "summary": "Event loop lifecycle, async/await syntax, asyncio.gather vs TaskGroup, handling blocking code with run_in_executor, and async context managers.",
                "core_concepts": [
                    "Single-threaded cooperative multitasking and the event loop",
                    "Coroutines, Tasks, and Futures in asyncio",
                    "Avoiding event loop blocking: loop.run_in_executor for synchronous I/O or CPU work",
                    "Handling concurrency with asyncio.gather, as_completed, and TaskGroup (Python 3.11+)",
                    "Async context managers (__aenter__, __aexit__) and async iterators"
                ],
                "sample_question": "What happens if a developer puts a synchronous time.sleep(5) or requests.get() inside an asyncio coroutine? How do you properly integrate blocking synchronous code into an async pipeline?",
                "question_type": "Async Architecture & Performance",
                "evaluation_criteria": "Explains event loop starvation, blocking the entire thread, and using asyncio.to_thread / run_in_executor or httpx/aiohttp.",
                "star_guide": {
                    "situation": "FastAPI service was locking up and timing out under 200 concurrent requests.",
                    "task": "Identify why the asynchronous event loop was hanging during database queries.",
                    "action": "Discovered synchronous ORM calls inside async route handlers; refactored to async drivers and moved legacy calculations to loop.run_in_executor.",
                    "result": "Supported 4,000 requests/sec with p99 latency dropping from 6,000ms to 42ms."
                }
            },
            {
                "key": "memory_gc",
                "name": "Memory Management & Garbage Collection",
                "difficulty": "Advanced",
                "summary": "Reference counting, cyclic references, generational garbage collector (Gen 0, 1, 2), gc module, weakref, and memory leak diagnosis.",
                "core_concepts": [
                    "Primary memory reclamation: Reference counting and immediate deallocation",
                    "Cyclic references where reference counts never drop to zero",
                    "Generational GC algorithm (three generations, collection thresholds)",
                    "Memory leak debugging tools: objgraph, tracemalloc, pympler",
                    "__slots__ optimization to eliminate __dict__ overhead on millions of instances"
                ],
                "sample_question": "How does CPython reclaim memory? Explain how reference counting and the cyclic garbage collector collaborate, and how would you diagnose a memory leak in a production Python service?",
                "question_type": "Memory Profiling & Runtime Internals",
                "evaluation_criteria": "Understanding immediate refcount deallocation + tri-color mark-and-sweep generational cycles; tracemalloc usage.",
                "star_guide": {
                    "situation": "A background worker container had steadily rising memory until restarting every 6 hours.",
                    "task": "Find the root cause of the memory leak without taking down production.",
                    "action": "Used tracemalloc snapshots to isolate cyclic object references in an unclosed circular event listener graph; broke cycles using weakref.",
                    "result": "Flat memory profile maintained over 30 days of continuous operation."
                }
            },
            {
                "key": "type_hinting_architecture",
                "name": "Type Hinting, Pydantic & Clean Architecture",
                "difficulty": "Intermediate",
                "summary": "Typing module (Union, Optional, TypeVar, Generic, Protocol), Pydantic v2 data validation, dependency injection, and clean architecture principles.",
                "core_concepts": [
                    "Type hints vs runtime enforcement (mypy static analysis)",
                    "Protocols and Structural Subtyping (duck typing with static verification)",
                    "Pydantic BaseModel, Field validators, and serialization performance",
                    "Dependency injection and interface segregation in Python",
                    "Clean Architecture layers: Entities, Use Cases, Repositories, Handlers"
                ],
                "sample_question": "How does typing.Protocol enable static duck typing in Python? Contrast it with Abstract Base Classes (abc.ABC), and explain how Pydantic leverages type annotations at runtime.",
                "question_type": "Software Architecture & Code Quality",
                "evaluation_criteria": "Distinguishes nominal subtyping (ABC) from structural subtyping (Protocol), explains runtime type inspection via type hints.",
                "star_guide": {
                    "situation": "A legacy codebase suffered from frequent runtime AttributeError exceptions due to unvalidated data dictionaries.",
                    "task": "Modernize the service boundary contracts and ensure type safety across the team.",
                    "action": "Introduced Pydantic models for request/response validation and enforced strict mypy checks in the CI/CD pipeline.",
                    "result": "Eliminated 95% of runtime data errors and improved developer onboarding velocity."
                }
            }
        ]
    },

    "c_language": {
        "key": "c_language",
        "name": "C Language & Systems Programming",
        "short_name": "C Language",
        "icon": "bi-cpu",
        "badge_class": "bg-warning-subtle text-warning-emphasis border border-warning-subtle",
        "color": "#eab308",
        "tagline": "Master pointers & pointer arithmetic, dynamic memory, structs & alignment, bitwise operations & low-level debugging.",
        "description": "Comprehensive low-level C programming interview preparation covering pointers, malloc/free heap management, memory alignment, bit manipulation, preprocessor macros, function pointers, file I/O, POSIX threads, and GDB debugging.",
        "topics": [
            {
                "key": "pointers_arithmetic",
                "name": "Pointers, Double Pointers & Pointer Arithmetic",
                "difficulty": "Intermediate / Advanced",
                "summary": "Memory addresses, dereferencing, pointer arithmetic rules based on sizeof(T), double pointers (**ptr) for modifying caller pointers, arrays decaying to pointers, and void*.",
                "core_concepts": [
                    "Pointer arithmetic: ptr + 1 increments by sizeof(*ptr) bytes, not 1 byte",
                    "Array decaying to pointer when passed into functions",
                    "Double pointers (**ptr) to allocate or modify pointers in calling functions",
                    "Void pointers (void*) for generic memory buffers and casting rules",
                    "Pointer to const (const int*) vs Const pointer (int* const)"
                ],
                "sample_question": "Explain what happens in memory during pointer arithmetic: if `int* p = (int*)0x1000;`, what is the value of `p + 3` on a 64-bit architecture? How do you pass a pointer to a function so the function can allocate memory for the caller?",
                "question_type": "Memory Addressing & Pointer Mechanics",
                "evaluation_criteria": "Calculates 0x1000 + 3 * sizeof(int) = 0x100C (assuming 4-byte int), explains double pointer (void** or char**) passing.",
                "star_guide": {
                    "situation": "Implementing a high-performance in-memory ring buffer for streaming network packets in C.",
                    "task": "Manage read and write heads directly using pointer offsets without copying memory.",
                    "action": "Used pointer arithmetic with modulo wrapping and passed double pointers to buffer-init routines.",
                    "result": "Achieved zero-copy throughput of 10M packets per second with zero memory corruption."
                }
            },
            {
                "key": "dynamic_memory_valgrind",
                "name": "Dynamic Memory (malloc/free) & Memory Safety",
                "difficulty": "Advanced",
                "summary": "Heap allocation mechanics with malloc, calloc, realloc, free, dangling pointers, memory fragmentation, double free, and Valgrind leak detection.",
                "core_concepts": [
                    "malloc (uninitialized memory) vs calloc (zero-initialized) vs realloc (resizing)",
                    "Heap metadata chunk headers and allocator invariants (e.g., glibc dlmalloc/ptmalloc)",
                    "Dangling pointers, double free vulnerabilities, and setting pointers to NULL after free",
                    "Memory fragmentation (internal vs external fragmentation)",
                    "Using Valgrind Memcheck and AddressSanitizer (ASan) to detect leaks and out-of-bounds reads"
                ],
                "sample_question": "What is the danger of using realloc() like this: `ptr = realloc(ptr, new_size);`? If realloc fails, what happens to the original memory, and how should it be correctly handled?",
                "question_type": "Memory Safety & Vulnerability Prevention",
                "evaluation_criteria": "Points out that if realloc returns NULL on failure, the original pointer is overwritten and the memory is permanently leaked. Shows correct pattern with temporary pointer.",
                "star_guide": {
                    "situation": "An embedded C daemon was crashing intermittently after running for 48 hours in production.",
                    "task": "Isolate memory leaks and heap corruption causing segmentation faults.",
                    "action": "Compiled with AddressSanitizer and profiled with Valgrind; identified unhandled realloc failure and a double-free on socket close.",
                    "result": "Fixed memory management lifecycle, achieving 100% leak-free Valgrind reports."
                }
            },
            {
                "key": "structs_unions_alignment",
                "name": "Structs, Unions & Memory Alignment / Padding",
                "difficulty": "Intermediate / Advanced",
                "summary": "Struct memory layout, compiler padding for CPU alignment, #pragma pack, bit-fields, unions for type punning and variant records, and cache line implications.",
                "core_concepts": [
                    "Hardware alignment requirements (e.g. 4-byte ints on 4-byte boundaries)",
                    "Compiler padding bytes inserted between struct members",
                    "Reordering struct members from largest to smallest to minimize memory waste",
                    "#pragma pack(1) or __attribute__((packed)) for network protocols vs CPU performance cost",
                    "Unions for shared memory representation and protocol packet headers"
                ],
                "sample_question": "Given a struct with a char, an int, and a short: what is its total sizeof on a 64-bit architecture with default alignment? How does member order affect the size, and when would you use #pragma pack(1)?",
                "question_type": "Hardware Architecture & Low-Level Layout",
                "evaluation_criteria": "Calculates 1 + 3(pad) + 4 + 2 + 2(pad) = 12 bytes; reordering to int, short, char gives 4 + 2 + 1 + 1(pad) = 8 bytes. Discusses unaligned memory access penalties.",
                "star_guide": {
                    "situation": "A high-frequency trading feed handler needed to parse millions of binary multicast packets per second.",
                    "task": "Serialize and deserialize custom packet structs with zero serialization overhead.",
                    "action": "Designed structs aligned to 64-byte CPU cache lines and ordered fields to eliminate 33% padding bloat.",
                    "result": "Decreased cache misses by 40% and cut packet decoding latency from 180ns to 95ns."
                }
            },
            {
                "key": "bitwise_manipulation",
                "name": "Bitwise Operations & Endianness",
                "difficulty": "Intermediate / Advanced",
                "summary": "Bitwise AND, OR, XOR, NOT, left/right shifts, setting/clearing/toggling bits, bitmasks, checking powers of 2, and Little vs Big Endian detection & byte swapping.",
                "core_concepts": [
                    "Bitwise operations: &, |, ^, ~, <<, >>",
                    "Bitmask idioms: `val |= (1 << n)` (set), `val &= ~(1 << n)` (clear), `val ^= (1 << n)` (toggle)",
                    "Checking if an integer is a power of 2 in O(1): `(n > 0) && ((n & (n - 1)) == 0)`",
                    "Counting set bits (Brian Kernighan's algorithm)",
                    "Little Endian vs Big Endian byte orders and detecting endianness with a union or char pointer"
                ],
                "sample_question": "How do you detect whether the host CPU is Little Endian or Big Endian at runtime in C? Write an expression to check if an unsigned integer is a power of 2 using bitwise operations in O(1) time.",
                "question_type": "Low-Level Math & Architecture",
                "evaluation_criteria": "Tests integer 1 with a char pointer (if *(char*)&val == 1 => little endian); explains n & (n - 1) power of 2 trick.",
                "star_guide": {
                    "situation": "A cross-platform binary file parser produced corrupted values when running on ARM vs x86.",
                    "task": "Ensure correct network byte order (Big Endian) across heterogeneous CPU architectures.",
                    "action": "Implemented runtime endianness detection and applied htons/htonl and bitwise byte-swapping routines.",
                    "result": "Binary parser functioned seamlessly across x86, ARM, and MIPS architectures."
                }
            },
            {
                "key": "preprocessor_macros",
                "name": "C Preprocessor, Macros & Compilation Phases",
                "difficulty": "Intermediate",
                "summary": "Compilation stages (Preprocess, Compile, Assemble, Link), function-like macros, parenthesization rules, stringification (#), token pasting (##), and header guards.",
                "core_concepts": [
                    "The 4 compilation stages: Preprocessing (gcc -E), Compilation (gcc -S), Assembly (gcc -c), Linking (gcc -o)",
                    "Macro hygiene: surrounding macro arguments in parentheses to prevent operator precedence bugs",
                    "Stringification operator `#x` and Token Pasting operator `a##b`",
                    "Header guards `#ifndef MY_HEADER_H` vs `#pragma once`",
                    "Inline functions (static inline) vs macros: type safety, debugging, and multiple evaluation traps"
                ],
                "sample_question": "What is the danger with `#define SQUARE(x) x * x` when evaluated with `SQUARE(2 + 3)`? How do you fix it, and what is the token pasting operator `##` used for?",
                "question_type": "Preprocessor & Build Pipeline",
                "evaluation_criteria": "Identifies operator precedence trap: 2 + 3 * 2 + 3 = 11 instead of 25. Shows `((x) * (x))` and demonstrates `##` identifier concatenation.",
                "star_guide": {
                    "situation": "A complex legacy C codebase suffered from macro side-effect bugs and slow incremental builds.",
                    "task": "Audit macro definitions and clean up repetitive boilerplate code.",
                    "action": "Refactored risky macros into static inline functions and used token pasting macros for structured error code generation.",
                    "result": "Eliminated subtle side-effect evaluation bugs and improved GDB stepping accuracy."
                }
            },
            {
                "key": "function_pointers_callbacks",
                "name": "Function Pointers, Callbacks & Polymorphism in C",
                "difficulty": "Intermediate / Advanced",
                "summary": "Declaring and invoking function pointers, typedef for function pointers, callbacks in event loops, qsort custom comparators, and simulating VTables in C.",
                "core_concepts": [
                    "Syntax for function pointer declaration: `return_type (*func_ptr)(arg_types)`",
                    "Using `typedef` to define clean function pointer types",
                    "Callback architecture in event-driven systems and state machines",
                    "Passing comparator callbacks to standard library `qsort` and `bsearch`",
                    "Implementing object-oriented virtual function tables (VTables) in pure C with struct function pointers"
                ],
                "sample_question": "Declare a function pointer type that takes two const void pointers and returns an int (like the qsort comparator). How do you implement object-oriented polymorphism in pure C using structs of function pointers?",
                "question_type": "Advanced C Architecture & OOP Simulation",
                "evaluation_criteria": "Writes `typedef int (*comparator_t)(const void*, const void*);` and describes struct containing function pointers (vtable pointer pattern like Linux kernel VFS).",
                "star_guide": {
                    "situation": "Building a hardware abstraction layer (HAL) for multiple microcontroller sensors in pure C.",
                    "task": "Provide a uniform interface (`read()`, `write()`, `init()`) without knowing the hardware model at compile time.",
                    "action": "Created a struct `sensor_ops_t` containing function pointers; instantiated concrete ops tables for I2C and SPI sensors.",
                    "result": "Enabled hot-swappable sensor drivers with zero changes to higher-level application logic."
                }
            },
            {
                "key": "stack_heap_gdb",
                "name": "Stack vs Heap, Segfaults & GDB Debugging",
                "difficulty": "Advanced",
                "summary": "Stack frames, calling conventions, local variable lifecycles, stack overflow vs heap overflow, segmentation faults, core dumps, and GDB commands (bt, print, x/x).",
                "core_concepts": [
                    "Stack frame layout: return address, base pointer, local variables, parameters",
                    "Segmentation fault causes: dereferencing NULL, accessing unmapped pages, writing to read-only string literals",
                    "Stack overflow from unbound recursion vs heap exhaustion",
                    "Analyzing core dumps: `ulimit -c unlimited` and `gdb ./app core`",
                    "Essential GDB commands: `run`, `break`, `next`, `step`, `backtrace (bt)`, `print`, `examine memory (x)`"
                ],
                "sample_question": "What specifically causes a Segmentation Fault at the hardware and operating system page table level? Walk me through how you would inspect a production core dump file using GDB to find the crashing line of code.",
                "question_type": "Operating Systems & Low-Level Debugging",
                "evaluation_criteria": "Explains MMU raising a page fault interrupt for invalid virtual memory addresses; demonstrates GDB `bt full`, frame inspection, and register inspection.",
                "star_guide": {
                    "situation": "A critical Linux network proxy crashed in production with 'Segmentation fault (core dumped)'.",
                    "task": "Quickly identify the root cause from the core dump without disturbing active traffic.",
                    "action": "Loaded core dump into GDB with symbol tables (`gdb proxy core`), inspected `backtrace full`, and identified a NULL pointer dereference caused by a malformed SSL handshake.",
                    "result": "Patched the null check and deployed a fix within 25 minutes, preventing further downtime."
                }
            },
            {
                "key": "pthreads_concurrency",
                "name": "POSIX Threads (pthreads) & Multithreading in C",
                "difficulty": "Advanced",
                "summary": "pthread_create, pthread_join, mutexes (pthread_mutex_t), condition variables (pthread_cond_t), race conditions, deadlocks, and atomic operations.",
                "core_concepts": [
                    "pthread_create, pthread_join, and passing thread arguments safely",
                    "Data races and mutex synchronization (`pthread_mutex_lock` / `unlock`)",
                    "Condition variables (`pthread_cond_wait` / `signal`) and why wait must be in a while loop (spurious wakeups)",
                    "Deadlock conditions and lock ordering discipline",
                    "C11 stdatomic (`atomic_int`, `atomic_fetch_add`) for lock-free concurrency"
                ],
                "sample_question": "Why MUST `pthread_cond_wait(&cond, &mutex)` always be called inside a `while (!condition)` loop rather than an `if (!condition)` block? What is a spurious wakeup?",
                "question_type": "Concurrent Systems & Synchronization",
                "evaluation_criteria": "Explains spurious wakeups caused by kernel scheduling, race conditions where another thread steals the state before waking thread runs.",
                "star_guide": {
                    "situation": "A multi-threaded C worker pool suffered from sporadic deadlocks and missing jobs under peak queue load.",
                    "task": "Redesign the producer-consumer thread queue for thread safety and low latency.",
                    "action": "Implemented a bounded queue with pthread_mutex, condition variables in while-loops for queue empty/full states.",
                    "result": "Scaled reliably to 64 worker threads handling 500,000 tasks/second with zero deadlocks."
                }
            }
        ]
    },

    "dsa": {
        "key": "dsa",
        "name": "Data Structures & Algorithms (DSA)",
        "short_name": "DSA",
        "icon": "bi-diagram-3",
        "badge_class": "bg-info-subtle text-info-emphasis border border-info-subtle",
        "color": "#06b6d4",
        "tagline": "Master arrays, two pointers, trees, graphs, dynamic programming & Big-O complexity.",
        "description": "Comprehensive technical coding interview preparation covering standard data structures and algorithmic patterns used by top tier tech companies (Google, Meta, Amazon, Microsoft).",
        "topics": [
            {
                "key": "two_pointers_sliding_window",
                "name": "Two Pointers & Sliding Window",
                "difficulty": "Intermediate",
                "summary": "Fast & slow pointers, collision pointers, sliding window (fixed vs dynamic size), Kadane's algorithm, and prefix sums.",
                "core_concepts": ["Sliding window O(N) optimization vs O(N^2) brute force", "Two pointers collision for sorted arrays", "Prefix sum for O(1) range queries", "Kadane's maximum subarray sum algorithm"],
                "sample_question": "Explain the sliding window technique. How would you find the longest substring without repeating characters in O(N) time and O(min(N, M)) space?",
                "question_type": "Algorithmic Pattern & Optimization",
                "evaluation_criteria": "Uses a hash map of last seen character indices with start and end pointers.",
                "star_guide": {
                    "situation": "A log analysis system needed to find maximum burst event windows across continuous streams.",
                    "task": "Optimize the window computation from O(N^2) to linear time.",
                    "action": "Implemented an expanding/contracting sliding window with a frequency hash map.",
                    "result": "Reduced runtime from 12 seconds to 15 milliseconds on a 1M event dataset."
                }
            },
            {
                "key": "trees_bst",
                "name": "Binary Trees & Binary Search Trees (BST)",
                "difficulty": "Intermediate / Advanced",
                "summary": "Tree traversals (DFS: in-order, pre-order, post-order; BFS: level-order), BST operations, lowest common ancestor (LCA), and balanced trees.",
                "core_concepts": ["DFS vs BFS recursive and iterative implementations", "BST properties and in-order traversal sorting", "Lowest Common Ancestor (LCA) in BST vs Binary Tree", "Height and diameter of binary trees"],
                "sample_question": "How do you find the Lowest Common Ancestor (LCA) of two nodes in a standard Binary Tree (not a BST)? Walk me through the recursive DFS approach.",
                "question_type": "Tree Traversal & Recursion",
                "evaluation_criteria": "Explains base cases (null, node1, node2) and checking if left and right subtrees both return non-null.",
                "star_guide": {
                    "situation": "Needed to determine the closest shared permission parent in an access control hierarchy.",
                    "task": "Find the common ancestor node efficiently in memory.",
                    "action": "Implemented post-order recursive tree traversal with O(N) time and O(H) space complexity.",
                    "result": "Permission resolution ran in sub-millisecond time across 50,000 nodes."
                }
            },
            {
                "key": "graphs_algorithms",
                "name": "Graphs: BFS, DFS, Topo-Sort & Shortest Path",
                "difficulty": "Advanced",
                "summary": "Adjacency lists, cycle detection, Topological Sort (Kahn's algorithm), Dijkstra's algorithm, and Disjoint Set Union (Union-Find).",
                "core_concepts": ["Graph representations (adjacency list vs matrix)", "Cycle detection in directed vs undirected graphs", "Topological Sort for build dependencies (Kahn's in-degree BFS)", "Dijkstra's shortest path with priority queue"],
                "sample_question": "How does Kahn's algorithm use in-degrees to perform topological sorting and detect cycles in a build dependency graph? What is its time and space complexity?",
                "question_type": "Graph Theory & System Scheduling",
                "evaluation_criteria": "In-degree array, queue of 0 in-degree nodes, edge reduction, O(V + E) complexity.",
                "star_guide": {
                    "situation": "A build system needed to execute tasks in correct dependency order and reject circular imports.",
                    "task": "Implement an automated task scheduler that detects cyclic dependencies.",
                    "action": "Built Kahn's algorithm topological sorter with in-degree validation.",
                    "result": "Prevented build deadlocks and parallelized independent build tasks."
                }
            },
            {
                "key": "dynamic_programming",
                "name": "Dynamic Programming (DP): 1D & 2D",
                "difficulty": "Advanced",
                "summary": "Overlapping subproblems, optimal substructure, memoization (top-down) vs tabulation (bottom-up), 0/1 Knapsack, and Longest Common Subsequence.",
                "core_concepts": ["State definition and recurrence relations", "Memoization table vs iterative bottom-up table", "Space optimization from O(N^2) to O(N)", "Classic archetypes: 0/1 Knapsack, Coin Change, LCS, Edit Distance"],
                "sample_question": "Explain the difference between Top-Down Memoization and Bottom-Up Tabulation. How would you solve the Coin Change problem (minimum coins to make amount X) using DP?",
                "question_type": "Algorithmic Optimization & DP",
                "evaluation_criteria": "Defines dp[i] state as min coins for amount i, recurrence dp[i] = min(dp[i], dp[i - c] + 1), base case dp[0] = 0.",
                "star_guide": {
                    "situation": "An e-commerce discount engine needed to find the optimal combination of vouchers to maximize savings.",
                    "task": "Avoid exponential backtracking that was causing checkout timeouts.",
                    "action": "Modeled the problem as a 2D dynamic programming knapsack with space optimization.",
                    "result": "Checkout calculation completed in under 2ms with optimal voucher allocation."
                }
            }
        ]
    },

    "java": {
        "key": "java",
        "name": "Java & Enterprise Architecture",
        "short_name": "Java",
        "icon": "bi-cup-hot-fill",
        "badge_class": "bg-danger-subtle text-danger border border-danger-subtle",
        "color": "#dc3545",
        "tagline": "Master JVM memory, collections internals, multithreading, Spring Boot & microservices.",
        "description": "Enterprise Java interview preparation covering JVM internals, Garbage Collection (G1, ZGC), Java Collections Framework internals, Concurrency utilities, and Spring Boot architecture.",
        "topics": [
            {
                "key": "jvm_internals_gc",
                "name": "JVM Memory Model & Garbage Collectors",
                "difficulty": "Advanced",
                "summary": "JVM memory areas (Heap: Eden, Survivor, Tenured; Stack, Metaspace), JIT compilation, G1GC, ZGC, and troubleshooting OutOfMemoryError.",
                "core_concepts": ["JVM memory layout: Young vs Old Generation", "Minor GC vs Major / Full GC mechanics", "G1GC region-based allocation and pause time targets", "Analyzing heap dumps with jmap and Eclipse Memory Analyzer (MAT)"],
                "sample_question": "What is the difference between JVM Stack and Heap memory? Explain how G1GC divides memory into regions and how it balances throughput with predictable latency pauses.",
                "question_type": "Runtime Architecture & Performance Tuning",
                "evaluation_criteria": "Explains thread-local stack frames vs shared heap, region evacuation, and concurrent marking.",
                "star_guide": {
                    "situation": "Enterprise payment microservice was experiencing 800ms Stop-The-World GC pauses under peak traffic.",
                    "task": "Tune JVM garbage collection parameters to meet strict sub-50ms SLA requirements.",
                    "action": "Migrated from CMS to G1GC with tuned MaxGCPauseMillis and SurvivorRatio.",
                    "result": "Reduced p99 GC pause time from 800ms to 24ms."
                }
            },
            {
                "key": "collections_concurrency",
                "name": "Collections Internals & Java Concurrency",
                "difficulty": "Intermediate / Advanced",
                "summary": "HashMap collision handling (LinkedList to Red-Black tree at threshold 8), ConcurrentHashMap segment/bucket locking, volatile, and ExecutorService.",
                "core_concepts": ["HashMap internal structure, hash spread function, TREEIFY_THRESHOLD", "ConcurrentHashMap CAS (Compare-And-Swap) and synchronized node locking", "Volatile keyword and CPU cache visibility", "Java 21 Virtual Threads (Project Loom)"],
                "sample_question": "How does Java's HashMap handle hash collisions since Java 8? How does ConcurrentHashMap achieve thread safety without synchronizing the entire table?",
                "question_type": "Collections Architecture & Concurrency",
                "evaluation_criteria": "Explains treeification when bucket size >= 8 and table capacity >= 64; CAS for initial bucket creation and synchronized on bucket head.",
                "star_guide": {
                    "situation": "Multi-threaded cache service was suffering from thread contention using Collections.synchronizedMap.",
                    "task": "Enable high-concurrency read/write throughput without deadlocks.",
                    "action": "Replaced synchronizedMap with ConcurrentHashMap and atomic operations.",
                    "result": "Throughput increased by 650% across 32 concurrent threads."
                }
            }
        ]
    },

    "cpp": {
        "key": "cpp",
        "name": "C++ & Modern Systems Engineering",
        "short_name": "C++",
        "icon": "bi-code-square",
        "badge_class": "bg-primary-subtle text-primary border border-primary-subtle",
        "color": "#2563eb",
        "tagline": "Master modern C++, move semantics, smart pointers, RAII, templates & virtual tables.",
        "description": "High-performance systems C++ interview preparation covering C++11 to C++20 features, memory ownership, standard template library internals, and low-latency systems.",
        "topics": [
            {
                "key": "move_semantics_raii",
                "name": "Move Semantics, Rvalues & RAII",
                "difficulty": "Advanced",
                "summary": "Rvalue references (&&), std::move, std::forward, perfect forwarding, move constructors, Rule of Five, and RAII idiom.",
                "core_concepts": ["Lvalues vs Rvalues and std::move casting", "Move constructor transferring ownership without heap allocation", "Rule of Zero / Three / Five", "RAII (Resource Acquisition Is Initialization) for deterministic cleanup"],
                "sample_question": "Explain what std::move actually does at runtime. How does move semantics eliminate expensive deep copies when returning heavy vectors or strings from functions?",
                "question_type": "Modern C++ & Memory Ownership",
                "evaluation_criteria": "Clarifies that std::move is an unconditional cast to rvalue reference and generates zero machine code at runtime.",
                "star_guide": {
                    "situation": "A low-latency audio processing pipeline was dropping frames due to deep vector copies.",
                    "task": "Eliminate dynamic memory allocations in the hot processing loop.",
                    "action": "Implemented move constructors and std::move transfers along with custom pre-allocated buffers.",
                    "result": "Zero heap allocations during streaming, eliminating audio dropout glitches."
                }
            },
            {
                "key": "smart_pointers_vtable",
                "name": "Smart Pointers & Virtual Tables (VTable)",
                "difficulty": "Advanced",
                "summary": "std::unique_ptr, std::shared_ptr (control block, atomic refcounts), std::weak_ptr, dynamic dispatch, vptr, and vtable memory layouts.",
                "core_concepts": ["unique_ptr zero-overhead abstraction", "shared_ptr control block (ref count, weak count, custom deleter)", "weak_ptr breaking cyclic references", "vptr and vtable layout for polymorphic classes"],
                "sample_question": "What is the overhead of a std::shared_ptr compared to a raw pointer? How does the compiler implement dynamic polymorphism via vptr and vtable?",
                "question_type": "Language Runtime & Memory Architecture",
                "evaluation_criteria": "Points out control block allocation and atomic increments; describes pointer indirection through vtable.",
                "star_guide": {
                    "situation": "A game engine simulation leaked entity instances due to circular shared_ptr relationships.",
                    "task": "Eliminate memory leaks and improve cache locality of game entities.",
                    "action": "Audited entity ownership graph, converted child back-references to std::weak_ptr, and prioritized std::unique_ptr.",
                    "result": "Fixed memory leak completely and reduced memory footprint by 28%."
                }
            }
        ]
    },

    "javascript_web": {
        "key": "javascript_web",
        "name": "JavaScript / TypeScript & Web Engineering",
        "short_name": "JS / TS",
        "icon": "bi-filetype-js",
        "badge_class": "bg-warning-subtle text-warning-emphasis border border-warning-subtle",
        "color": "#ca8a04",
        "tagline": "Master the event loop, closures, prototypal inheritance, TypeScript generics & web performance.",
        "description": "Comprehensive JavaScript, TypeScript, and modern browser frontend/full-stack engineering interview preparation.",
        "topics": [
            {
                "key": "event_loop_async",
                "name": "Event Loop, Microtasks & Async JS",
                "difficulty": "Intermediate / Advanced",
                "summary": "V8 engine call stack, microtask queue (Promises) vs macrotask queue (setTimeout), async/await, and non-blocking I/O.",
                "core_concepts": ["Call stack, Web APIs, Microtask vs Macrotask queue", "Promise execution order and process.nextTick / queueMicrotask", "Async/await desugaring into Promise chains", "Preventing UI thread jank and event loop blocking"],
                "sample_question": "What is the exact execution order of console.logs when mixing setTimeout(..., 0), Promise.resolve().then(...), and synchronous code? Explain why microtasks take priority over macrotasks.",
                "question_type": "JavaScript Engine Internals",
                "evaluation_criteria": "Correctly states sync -> all microtasks (until empty) -> macrotask -> microtasks.",
                "star_guide": {
                    "situation": "A complex single-page dashboard experienced stuttering animations when rendering large data tables.",
                    "task": "Prevent long tasks from starving the main thread and maintain 60 FPS.",
                    "action": "Chunked heavy processing using queueMicrotask and requestIdleCallback.",
                    "result": "Eliminated UI freezes and dropped total blocking time (TBT) by 80%."
                }
            },
            {
                "key": "typescript_generics",
                "name": "TypeScript Type System & Advanced Generics",
                "difficulty": "Intermediate / Advanced",
                "summary": "Generics, conditional types, mapped types, utility types (Pick, Omit, Partial, Record), type guards, and structural typing.",
                "core_concepts": ["Generics `<T>` and generic constraints (`<T extends object>`)", "Conditional types (`T extends U ? X : Y`) and `infer` keyword", "Mapped types and keyof operator", "Discriminated unions and custom type guards (`val is Type`)"],
                "sample_question": "Explain how mapped types and conditional types work in TypeScript. How would you implement a custom `DeepReadonly<T>` type from scratch?",
                "question_type": "Type System & Functional Architecture",
                "evaluation_criteria": "Recursively iterates over keyof T, checks if T[K] is function/primitive vs object.",
                "star_guide": {
                    "situation": "Large front-end application had inconsistent API contract typings leading to client-side crashes.",
                    "task": "Establish an end-to-end type-safe contract between backend schemas and React components.",
                    "action": "Created generic typed API client using discriminated unions and utility types.",
                    "result": "Reduced UI runtime crashes to 0 and improved engineering delivery velocity."
                }
            }
        ]
    },

    "system_design": {
        "key": "system_design",
        "name": "System Design & Distributed Cloud Systems",
        "short_name": "System Design",
        "icon": "bi-clouds-fill",
        "badge_class": "bg-secondary-subtle text-secondary-emphasis border border-secondary-subtle",
        "color": "#6366f1",
        "tagline": "Master microservices, distributed caching, message queues, rate limiters, CAP theorem & scalability.",
        "description": "Architectural and distributed systems design interview preparation covering large-scale internet services, high availability, resilience patterns, and database scaling.",
        "topics": [
            {
                "key": "distributed_caching",
                "name": "Distributed Caching & Eviction Strategies",
                "difficulty": "Advanced",
                "summary": "Redis architectures, cache-aside, write-through, write-behind, cache stampede mitigation, TTLs, and consistent hashing.",
                "core_concepts": ["Cache-Aside (Lazy Loading) vs Write-Through vs Write-Behind", "Cache stampede prevention with probabilistic early expiration (XFetch) or mutex locks", "Redis cluster sharding with consistent hashing", "Cache penetration vs cache avalanche remedies"],
                "sample_question": "Design a distributed caching tier for an e-commerce catalog serving 500,000 requests per second. How do you prevent cache stampede when a hot product cache key expires?",
                "question_type": "System Architecture & High Availability",
                "evaluation_criteria": "Describes Redis cluster, mutex lock on cache miss, or probabilistic early recomputation (XFetch).",
                "star_guide": {
                    "situation": "During Black Friday sales, database CPU surged to 100% when cached product pages expired simultaneously.",
                    "task": "Eliminate cache stampede and ensure 99.99% system availability.",
                    "action": "Implemented distributed mutex locking on cache recomputation and added jitter to TTLs.",
                    "result": "Database load dropped by 92% and the platform handled record traffic without downtime."
                }
            },
            {
                "key": "message_queues_streaming",
                "name": "Message Queues & Event Streaming (Kafka / RabbitMQ)",
                "difficulty": "Advanced",
                "summary": "Asynchronous messaging, Kafka topics, partitions, consumer groups, offsets, at-least-once vs exactly-once delivery, and backpressure.",
                "core_concepts": ["Point-to-point queues (RabbitMQ) vs Distributed commit log (Apache Kafka)", "Kafka partitions, ordering guarantees, and consumer group rebalancing", "Handling poison pill messages with Dead Letter Queues (DLQ)", "Idempotent consumers to guarantee exactly-once processing semantics"],
                "sample_question": "Contrast RabbitMQ with Apache Kafka. When would you choose Kafka over RabbitMQ, and how do you achieve ordering guarantees in a distributed Kafka cluster?",
                "question_type": "Event-Driven Architecture & Messaging",
                "evaluation_criteria": "Mentions partition key hashing for strict per-key ordering, log compaction, high throughput streaming.",
                "star_guide": {
                    "situation": "Synchronous HTTP calls between microservices were causing cascading timeouts during surges.",
                    "task": "Decouple order placement from payment, email, and fulfillment systems.",
                    "action": "Architected an event-driven Kafka pipeline with partitioned order topics and idempotent consumers.",
                    "result": "Supported 10x traffic spikes with zero request drops and isolated downstream failures."
                }
            },
            {
                "key": "rate_limiting_api_gateway",
                "name": "Rate Limiting & API Gateway Architecture",
                "difficulty": "Advanced",
                "summary": "Token bucket, leaky bucket, sliding window counter algorithms, distributed rate limiting with Redis Lua scripts, and API gateways.",
                "core_concepts": ["Token Bucket vs Leaky Bucket vs Sliding Window Counter", "Atomic rate limiting using Redis EVAL Lua scripts", "Global vs per-client / per-IP rate limits", "Returning HTTP 429 Too Many Requests with Retry-After header"],
                "sample_question": "Design a scalable distributed rate limiter for a public API handling 100 million requests daily. Which algorithm would you choose, and how do you prevent race conditions in a distributed cache?",
                "question_type": "Security & Traffic Shaping",
                "evaluation_criteria": "Selects Sliding Window Counter or Token Bucket, utilizes Redis Lua script for atomic read-and-decrement.",
                "star_guide": {
                    "situation": "Our public APIs were targeted by scraping bots consuming 60% of backend resources.",
                    "task": "Implement an API rate limiter at the gateway tier that enforces tier-based quotas.",
                    "action": "Built a sliding window rate limiter in Redis with atomic Lua scripts deployed at the API Gateway.",
                    "result": "Thwarted bot abuse, recovered 55% server capacity, and protected legitimate customer traffic."
                }
            }
        ]
    }
}


def get_all_skill_tracks() -> Dict[str, Dict[str, Any]]:
    """Returns all technical skill tracks with full topic metadata."""
    return TECHNICAL_SKILL_TRACKS


def get_skill_track(skill_key: str) -> Optional[Dict[str, Any]]:
    """Returns a specific skill track by key."""
    if not skill_key:
        return None
    return TECHNICAL_SKILL_TRACKS.get(skill_key.lower().strip())


def get_topic_details(skill_key: str, topic_key: str) -> Optional[Dict[str, Any]]:
    """Returns a specific topic dictionary within a skill track."""
    track = get_skill_track(skill_key)
    if not track:
        return None
    for topic in track.get("topics", []):
        if topic.get("key") == topic_key:
            return topic
    return None
