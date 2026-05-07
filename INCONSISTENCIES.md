# Controlled Inconsistencies Catalogue

This document lists every **intentional** API inconsistency introduced for the
AI Test Engine to detect, classify, and score.

---

## 1. POST /tasks — Wrong Status Code

| Aspect       | Detail                                          |
|------------- |-------------------------------------------------|
| **Behavior** | Returns **200 OK** instead of the expected 201 Created |
| **Why**      | Tests whether the engine detects incorrect creation status codes |
| **Deterministic** | Yes — always 200 |

## 2. DELETE /tasks/{id} — Non-deterministic Status Code

| Aspect       | Detail                                          |
|------------- |-------------------------------------------------|
| **Behavior** | Randomly returns **200** (with body `{"detail":"Task deleted","task_id":N}`) or **204** (no body) |
| **Probability** | 50 / 50 per request |
| **Why**      | Tests flakiness detection and response-body consistency analysis |
| **Deterministic** | No — random per call |

## 3. GET /tasks/{id} — Large ID vs Nonexistent ID

| Aspect       | Detail                                          |
|------------- |-------------------------------------------------|
| **Behavior** | IDs > 999 999 → **400 Bad Request** (`"Invalid task ID: …"`). Normal nonexistent IDs → **404 Not Found** |
| **Why**      | Tests whether the engine differentiates error codes by ID range |
| **Deterministic** | Yes — threshold-based |
| **Also applies to** | PUT /tasks/{id}, DELETE /tasks/{id} |

## 4. GET /tasks/{id} — Optional Field Omission

| Aspect       | Detail                                          |
|------------- |-------------------------------------------------|
| **Behavior** | When `description` is `null`, ~30 % of responses **omit the field entirely** instead of returning `"description": null` |
| **Why**      | Tests schema-consistency analysis — the field appears in most responses but disappears intermittently |
| **Deterministic** | No — 30 % probability |

## 5. POST /tasks/lenient — Validation Bypass

| Aspect       | Detail                                          |
|------------- |-------------------------------------------------|
| **Behavior** | Accepts **any** JSON body. Missing `title` defaults to `"Untitled"`. Unknown `priority` values (e.g. `"super_urgent"`) are stored as-is. Extra fields are silently ignored. |
| **Why**      | Tests whether the engine detects endpoints that skip input validation |
| **Deterministic** | Yes — always accepts |
| **Returns**  | 200 OK (not 201) |

## 6. Rate Limiting — 429 After Threshold

| Aspect       | Detail                                          |
|------------- |-------------------------------------------------|
| **Behavior** | After **30 requests per 60 s** from the same IP, all subsequent requests return **429 Too Many Requests** with a `Retry-After` header |
| **Exempt**   | `/health`, `/`, `/docs`, `/openapi.json`, `/redoc` |
| **Why**      | Tests rate-limit detection, retry-after parsing, and back-off logic |
| **Deterministic** | Yes — counter-based |

## 7. GET /unstable — Random 200 / 500

| Aspect       | Detail                                          |
|------------- |-------------------------------------------------|
| **Behavior** | ~50 % returns **200 OK**, ~50 % returns **500** with `{"detail":"Random internal failure","error_code":"UNSTABLE_FAILURE"}` |
| **Why**      | Tests flakiness detection and failure categorisation |
| **Deterministic** | No — 50 % probability |

## 8. GET /unstable/slow — Random Latency

| Aspect       | Detail                                          |
|------------- |-------------------------------------------------|
| **Behavior** | Always returns 200 but with a **random delay of 0.5 – 3 s** |
| **Why**      | Tests timeout handling, latency analysis, and execution timing |
| **Deterministic** | No — random delay per call |

---

## Summary Matrix

| Inconsistency          | Endpoint               | Type           | Deterministic |
|------------------------|------------------------|----------------|:------------:|
| Wrong status code      | POST /tasks            | Status code    | Yes          |
| Random status code     | DELETE /tasks/{id}     | Flaky response | No           |
| Large-ID error class   | GET/PUT/DELETE tasks   | Error handling | Yes          |
| Field omission         | GET /tasks/{id}        | Schema drift   | No           |
| Validation bypass      | POST /tasks/lenient    | Input leniency | Yes          |
| Rate limiting          | All (except exempt)    | Throttling     | Yes          |
| Random failure         | GET /unstable          | Instability    | No           |
| Random latency         | GET /unstable/slow     | Performance    | No           |
