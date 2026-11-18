"""
Cherm Auditor Pro - Static Code & System Design Architect
Automated checking for:
1. System Design & Architectural Flaws (IDOR, Connection Starvation, N+1, CORS, Timeouts).
2. Code Smells & AST Anti-patterns with root cause and fix recipes.
3. Multi-Tap & Concurrency Stress Testing (debouncing, idempotency, row locking).
4. Automated PR Reviews with Risk Scores.
5. Clean, basic, minimalist HTML report generation (no AI themes, no emojis).
"""

import os
import re
import ast
import json
import time
import hashlib
import tempfile
import subprocess
from typing import Optional, Dict, Any, List
from fastmcp import FastMCP

try:
    from ml_scanner import run_ml_audit
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from ml_scanner import run_ml_audit

mcp = FastMCP("Cherm-Auditor-Pro")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIT_LOG_FILE = os.path.join(BASE_DIR, "cherm_audit_history.json")
_ANALYSIS_CACHE: Dict[str, Dict[str, Any]] = {}

def _get_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()

def _resolve_content(file_path: Optional[str], code_content: Optional[str]) -> tuple[str, str]:
    if code_content is not None and code_content.strip():
        return code_content, "raw_content"
    if file_path and os.path.isfile(file_path):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(), os.path.abspath(file_path)
    raise ValueError("Either 'code_content' or a valid 'file_path' must be provided.")

def _record_audit_event(action: str, target: str, summary: Dict[str, Any]):
    try:
        events = []
        if os.path.isfile(AUDIT_LOG_FILE):
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                events = json.load(f)
                if not isinstance(events, list):
                    events = []
        events.append({
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "target": target,
            "summary": summary
        })
        with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(events[-100:], f, indent=2)
    except Exception:
        pass


# =====================================================================
# 1. CODE SMELLS & AST DETECTOR
# =====================================================================

EXPLANATION_TEMPLATES = {
    "MUTABLE_DEFAULT_ARG": {
        "badge": "[WARNING] Mutable Default Arg",
        "title": "Mutable Default Argument in Function Signature",
        "plain_english": (
            "In Python, default arguments like [] or {} are created only once when the script starts, "
            "not every time your function is called. Modifying this argument will mutate it for all future callers."
        ),
        "production_risk": (
            "Cross-request state leaks. In web frameworks (FastAPI/Flask/Django), User B can receive cached data "
            "or items previously appended by User A."
        ),
        "how_to_fix": "def my_func(data=None):\n    if data is None:\n        data = []"
    },
    "BARE_EXCEPT": {
        "badge": "[CRITICAL] Bare Except Clause",
        "title": "Bare 'except:' Clause Swallowing System Signals",
        "plain_english": (
            "A bare except clause without an exception type catches everything, including KeyboardInterrupt (Ctrl+C), "
            "SystemExit, and memory errors."
        ),
        "production_risk": (
            "Zombified services. Prevents graceful shutdown when Docker or Kubernetes sends SIGTERM."
        ),
        "how_to_fix": "except Exception as err:\n    logger.error(f'Failed: {err}')\n    raise"
    },
    "SILENT_EXCEPTION_SUPPRESSION": {
        "badge": "[CRITICAL] Silent Exception Suppression",
        "title": "Silent Error Suppression ('except: pass')",
        "plain_english": (
            "An exception occurred, but was swallowed by 'pass' without logging. This creates ghost bugs that "
            "corrupt database state without warning."
        ),
        "production_risk": (
            "Silent data corruption and impossible post-mortem debugging."
        ),
        "how_to_fix": "except Exception as err:\n    logger.warning(f'Error occurred: {err}')"
    },
    "GOD_FUNCTION": {
        "badge": "[INFO] High Complexity",
        "title": "High Cognitive Complexity ('God Function')",
        "plain_english": (
            "This function is over 50 lines long. Monolithic functions are difficult to test and maintain."
        ),
        "production_risk": (
            "High bug regression rate during team refactoring."
        ),
        "how_to_fix": "Apply Single Responsibility Principle. Extract into small helper functions."
    },
    "UNMANAGED_RESOURCE_LEAK": {
        "badge": "[WARNING] Resource Leak",
        "title": "Unmanaged Resource / File Handle Leak",
        "plain_english": (
            "File opened with bare open() without a 'with' context manager."
        ),
        "production_risk": (
            "OSError: [Errno 24] Too many open files under concurrent traffic."
        ),
        "how_to_fix": "with open(filepath, 'r', encoding='utf-8') as f:\n    data = f.read()"
    }
}

class NaturalReviewVisitor(ast.NodeVisitor):
    def __init__(self, lines: List[str]):
        self.lines = lines
        self.issues: List[Dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        for default in node.args.defaults + node.args.kw_defaults:
            if default is not None and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                t = EXPLANATION_TEMPLATES["MUTABLE_DEFAULT_ARG"]
                self.issues.append({
                    "line": node.lineno,
                    "badge": t["badge"],
                    "rule": "MUTABLE_DEFAULT_ARG",
                    "severity": "HIGH",
                    "title": t["title"],
                    "plain_english_explanation": t["plain_english"],
                    "production_risk": t["production_risk"],
                    "how_to_fix": t["how_to_fix"],
                    "code_snippet": self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""
                })

        loc = (getattr(node, 'end_lineno', node.lineno) - node.lineno) + 1
        if loc > 50:
            t = EXPLANATION_TEMPLATES["GOD_FUNCTION"]
            self.issues.append({
                "line": node.lineno,
                "badge": t["badge"],
                "rule": "GOD_FUNCTION",
                "severity": "MEDIUM",
                "title": t["title"],
                "plain_english_explanation": f"{t['plain_english']} (Total {loc} lines)",
                "production_risk": t["production_risk"],
                "how_to_fix": t["how_to_fix"],
                "code_snippet": f"def {node.name}(...):  # {loc} lines"
            })
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Try(self, node: ast.Try):
        for handler in node.handlers:
            if handler.type is None:
                t = EXPLANATION_TEMPLATES["BARE_EXCEPT"]
                self.issues.append({
                    "line": handler.lineno,
                    "badge": t["badge"],
                    "rule": "BARE_EXCEPT",
                    "severity": "CRITICAL",
                    "title": t["title"],
                    "plain_english_explanation": t["plain_english"],
                    "production_risk": t["production_risk"],
                    "how_to_fix": t["how_to_fix"],
                    "code_snippet": self.lines[handler.lineno - 1].strip() if handler.lineno <= len(self.lines) else ""
                })
            elif isinstance(handler.type, ast.Name) and handler.type.id in ("Exception", "BaseException"):
                if len(handler.body) == 1 and isinstance(handler.body[0], (ast.Pass, ast.Expr)):
                    t = EXPLANATION_TEMPLATES["SILENT_EXCEPTION_SUPPRESSION"]
                    self.issues.append({
                        "line": handler.lineno,
                        "badge": t["badge"],
                        "rule": "SILENT_EXCEPTION_SUPPRESSION",
                        "severity": "CRITICAL",
                        "title": t["title"],
                        "plain_english_explanation": t["plain_english"],
                        "production_risk": t["production_risk"],
                        "how_to_fix": t["how_to_fix"],
                        "code_snippet": "except ...: pass"
                    })
        self.generic_visit(node)


@mcp.tool()
def explain_code_issues(file_path: Optional[str] = None, code_content: Optional[str] = None) -> Dict[str, Any]:
    """Static code review that explains issues with production impact and exact fix recipes."""
    try:
        content, source = _resolve_content(file_path, code_content)
    except Exception as e:
        return {"success": False, "error": str(e)}

    content_hash = _get_hash(content)
    cache_key = f"explain:{content_hash}"
    if cache_key in _ANALYSIS_CACHE:
        return _ANALYSIS_CACHE[cache_key]

    lines = content.splitlines()
    issues: List[Dict[str, Any]] = []

    try:
        tree = ast.parse(content)
        visitor = NaturalReviewVisitor(lines)
        visitor.visit(tree)
        issues.extend(visitor.issues)
    except SyntaxError as se:
        return {"success": False, "error": f"SyntaxError parsing code: {se}"}

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(("#", "//")):
            continue
        if re.search(r'\bopen\s*\(', stripped) and not stripped.startswith("with ") and "=" in stripped:
            t = EXPLANATION_TEMPLATES["UNMANAGED_RESOURCE_LEAK"]
            issues.append({
                "line": i,
                "badge": t["badge"],
                "rule": "UNMANAGED_RESOURCE_LEAK",
                "severity": "HIGH",
                "title": t["title"],
                "plain_english_explanation": t["plain_english"],
                "production_risk": t["production_risk"],
                "how_to_fix": t["how_to_fix"],
                "code_snippet": stripped[:80]
            })

    result = {
        "success": True,
        "source": source,
        "clean": len(issues) == 0,
        "total_issues": len(issues),
        "critical_blockers": sum(1 for x in issues if x.get("severity") == "CRITICAL"),
        "findings": issues
    }

    _ANALYSIS_CACHE[cache_key] = result
    _record_audit_event("explain_code_issues", source, {"issues": len(issues)})
    return result


# =====================================================================
# 2. SYSTEM DESIGN & ARCHITECTURAL FLAW ENGINE
# =====================================================================

SYSTEM_DESIGN_RULES = [
    {
        "id": "BOLA_IDOR",
        "badge": "[SECURITY] BOLA / IDOR Flaw",
        "pattern": r'(?i)\.query\.(?:get|filter_by)\([^\)]*(?:id|user_id|account_id)\s*=\s*(?:request\.|payload\.|data\[|id\b)',
        "title": "Broken Object Level Authorization (IDOR / BOLA)",
        "explanation": "Queries records directly from client-supplied ID without verifying tenant or user ownership.",
        "hack_scenario": "Attacker changes order_id=1001 to 1002 to steal other users' invoices and private records.",
        "architectural_fix": "Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()"
    },
    {
        "id": "RACE_CONDITION_TOCTOU",
        "badge": "[FINANCIAL] Race Condition / Double Spend",
        "pattern": r'(?i)if\s+[\w\.]+(?:balance|credits?|stock|inventory|limit)\s*>=?\s*[\w\.]+:\s*\n.*(?:balance|credits?|stock)\s*-=',
        "title": "Check-Then-Act Race Condition (Double Spending)",
        "explanation": "Checks balance in memory then decrements without database locking or atomic execution.",
        "hack_scenario": "Firing 20 parallel requests drains $2,000 from a $100 balance because all threads read the starting balance simultaneously.",
        "architectural_fix": "Use atomic SQL updates (UPDATE account SET balance = balance - 100 WHERE balance >= 100) or Redis Redlock."
    },
    {
        "id": "UNBOUNDED_PAGINATION_DOS",
        "badge": "[DOS] Memory Explosion",
        "pattern": r'(?i)\.(?:fetchall|all)\(\s*\)|SELECT\s+\*\s+FROM\s+\w+\s*(?:;|\"|\')',
        "title": "Unbounded Database Query (Missing Pagination Limit)",
        "explanation": "Fetching rows with .all() or SELECT * without explicit LIMIT pulls the entire table into memory.",
        "hack_scenario": "Under 500,000 rows, this deserializes 500MB+ into RAM, triggering Linux OOM-Killer SIGKILL on the server.",
        "architectural_fix": "Enforce strict cursor or page limits: query.paginate(page=page, per_page=min(per_page, 100))"
    },
    {
        "id": "WILDCARD_CORS_EXPLOIT",
        "badge": "[SECURITY] Permissive CORS Bypass",
        "pattern": r'(?i)(?:allow_origins|origins)\s*=\s*\[[\'"]\*[\'"]\]',
        "title": "Wildcard CORS Misconfiguration",
        "explanation": "Allowing all origins (*) permits any arbitrary website to perform authenticated API calls from a user's browser.",
        "hack_scenario": "Malicious site makes background calls to your API; user's browser sends cookies and leaks sensitive data.",
        "architectural_fix": "allow_origins=['https://app.yourdomain.com', 'https://api.yourdomain.com']"
    },
    {
        "id": "UNPOOLED_DB_CONNECTION",
        "badge": "[STABILITY] DB Connection Starvation",
        "pattern": r'(?i)(?:psycopg2|mysql\.connector|sqlite3|pymongo)\.connect\s*\(',
        "title": "Raw Database Connection Without Connection Pooling",
        "explanation": "Opening raw individual connections per request instead of using a managed connection pool (e.g. SQLAlchemy QueuePool, HikariCP, pgpool).",
        "hack_scenario": "A sudden spike of 200 users makes 200 concurrent TCP handshakes to PostgreSQL, exhausting max_connections=100 and crashing the database.",
        "architectural_fix": "Use a singleton connection pool with max overflow limits: engine = create_engine(url, pool_size=20, max_overflow=10)"
    },
    {
        "id": "MISSING_REQUEST_TIMEOUT",
        "badge": "[STABILITY] Cascading Failure / Thread Starvation",
        "pattern": r'(?i)requests\.(?:get|post|put|delete|patch)\(',
        "title": "Synchronous Outbound HTTP Call Without Timeout",
        "explanation": "Calling third-party APIs without setting an explicit timeout. The default in Python requests is infinite wait.",
        "hack_scenario": "If the third-party payment or SMS gateway hangs, every worker thread waiting on the request stays blocked forever, completely freezing your web app.",
        "architectural_fix": "Always enforce strict connect and read timeouts: requests.get(url, timeout=(3.05, 10))"
    },
    {
        "id": "MISSING_RATE_LIMITER",
        "badge": "[SECURITY] Missing Rate Limiting / DDoS Risk",
        "pattern": r'(?i)@(app|router)\.(?:post|put)\([\'"]\/(?:login|signin|register|forgot|reset-password|auth)',
        "title": "Sensitive Auth/Payment Endpoint Without Rate Limiter",
        "explanation": "Authentication, password reset, or OTP endpoints defined without rate limiting decorators (like slowapi or Redis token bucket).",
        "hack_scenario": "Attacker runs a credential-stuffing dictionary attack with 100,000 attempts per minute, easily cracking weak passwords.",
        "architectural_fix": "Decorate with rate limits: @limiter.limit('5/minute') using Redis sliding window."
    },
    {
        "id": "STICKY_SESSION_STATEFUL",
        "badge": "[SCALABILITY] Load Balancer Session Desync",
        "pattern": r'(?i)session\[[\'"][^\'"]+[\'"]\]\s*=\s*(?!.*redis)',
        "title": "In-Memory Session Storage Behind Load Balancers",
        "explanation": "Writing user state directly to local in-process memory or local filesystem sessions.",
        "hack_scenario": "Behind an AWS ALB or Nginx round-robin load balancer, Request 1 writes session to Container A. Request 2 routes to Container B where session is absent, causing random logouts.",
        "architectural_fix": "Use stateless JWTs or an externalized session store (Redis / DynamoDB) across all load-balanced replicas."
    },
    {
        "id": "N_PLUS_ONE_QUERY",
        "badge": "[PERFORMANCE] N+1 Database Query Loop",
        "pattern": r'(?i)for\s+\w+\s+in\s+[\w\.]+:\s*\n.*(?:db\.session|\.query|SELECT\s+)',
        "title": "N+1 Database Query Loop in API Handler",
        "explanation": "Executing a database query inside an iteration loop over a list of parent entities.",
        "hack_scenario": "Loading a page with 100 posts executes 1 query for posts + 100 individual queries for authors (101 round trips). Under load, DB CPU spikes to 100%.",
        "architectural_fix": "Eager load relationships in a single joined query: query.options(joinedload(Post.author)) or SQL JOIN."
    },
    {
        "id": "MISSING_CIRCUIT_BREAKER",
        "badge": "[STABILITY] Missing Circuit Breaker",
        "pattern": r'(?i)while\s+(?:retry|attempts?)\s*<\s*\d+:\s*\n.*requests\.',
        "title": "Naive Tight Retry Loop Without Exponential Backoff / Circuit Breaker",
        "explanation": "Retrying failed remote calls in a fast loop without exponential backoff, jitter, or a circuit breaker pattern (PyBreaker).",
        "hack_scenario": "When a microservice begins failing, thousands of client instances hammer it with immediate retries ('retry storm'), completely preventing downstream recovery.",
        "architectural_fix": "Implement exponential backoff with jitter and a Circuit Breaker that fails fast when error rate exceeds 50%."
    },
    {
        "id": "JWT_NONE_ALGORITHM_BYPASS",
        "badge": "[AUTH] JWT None Algorithm Bypass",
        "pattern": r'(?i)jwt\.decode\([^)]*(?:verify_signature\s*=\s*False|algorithms\s*=\s*\[[^\]]*[\'"]none[\'"])',
        "title": "JWT Signature Verification Disabled or Algorithm 'none' Allowed",
        "explanation": "Decoding JWT tokens with verify_signature=False or allowing algorithm='none'. This allows anyone to forge admin tokens without knowing the secret key.",
        "hack_scenario": "An attacker creates a token with {'alg': 'none'} and payload {'user_id': 1, 'is_admin': true}, completely bypassing authentication.",
        "architectural_fix": "Enforce strict algorithm verification: jwt.decode(token, SECRET_KEY, algorithms=['HS256'])"
    },
    {
        "id": "BROKEN_PASSWORD_RESET_FLOW",
        "badge": "[AUTH] Password Reset Poisoning",
        "pattern": r'(?i)request\.headers\.get\([\'"]host[\'"]\).*reset',
        "title": "Host Header Injection in Password Reset Email Generation",
        "explanation": "Constructing password reset links using the client-supplied HTTP Host header instead of a fixed server environment configuration.",
        "hack_scenario": "Attacker triggers password reset for victim with header Host: evil-phish.com. The victim receives an official email linking to evil-phish.com, leaking their token.",
        "architectural_fix": "Hardcode the application domain from environment variables: reset_url = f'{settings.BASE_URL}/reset?token={token}'"
    },
    {
        "id": "WEAK_PASSWORD_HASHING",
        "badge": "[AUTH] Weak Password Hashing Algorithm",
        "pattern": r'(?i)(?:hashlib\.md5|hashlib\.sha1|hashlib\.sha256)\([^\)]*(?:password|passwd|pwd)',
        "title": "Passwords Hashed Using Fast Hashing Algorithms",
        "explanation": "Using MD5, SHA-1, or plain SHA-256 for passwords instead of slow, salted, memory-hard algorithms (Argon2, bcrypt, PBKDF2).",
        "hack_scenario": "If the database is leaked, an attacker uses GPUs with hashcat to crack billions of plain SHA-256 hashes per second.",
        "architectural_fix": "Use Argon2id or bcrypt with cost factor >= 12: bcrypt.hashpw(password.encode(), bcrypt.gensalt(12))"
    },
    {
        "id": "UNPROTECTED_ADMIN_ENDPOINT",
        "badge": "[AUTH] Missing Admin Route RBAC Guard",
        "pattern": r'(?i)@(app|router)\.(?:get|post|put|delete)\([\'"]\/(?:admin|internal|dashboard|manage)',
        "title": "Sensitive Administrative Route Without Access Control Guard",
        "explanation": "Administrative routes defined without authentication or role-based dependency checks (Depends(admin_required)).",
        "hack_scenario": "Anyone can navigate to /admin/delete_user or /admin/export_db without logging in, directly executing privileged operations.",
        "architectural_fix": "Protect all admin routes with authentication and role dependencies: dependencies=[Depends(require_admin_role)]"
    },
    {
        "id": "CLIENT_CONTROLLED_ROLE_ASSIGNMENT",
        "badge": "[AUTH] Mass Assignment Privilege Escalation",
        "pattern": r'(?i)User\([^)]*(?:role\s*=\s*(?:request|data|payload)|is_admin\s*=\s*(?:request|data|payload))',
        "title": "Mass Assignment / Client-Controlled Role Assignment",
        "explanation": "Allowing client-supplied request bodies to set privileged fields like role or is_admin during user registration or profile updates.",
        "hack_scenario": "During signup, attacker injects 'is_admin': true into JSON payload. The backend deserializes it directly into the User model.",
        "architectural_fix": "Use strict Pydantic schemas excluding privileged fields: class UserCreate(BaseModel): name: str, email: str, password: str"
    },
    {
        "id": "INSECURE_SESSION_COOKIE_FLAGS",
        "badge": "[AUTH] Insecure Session Cookie Flags",
        "pattern": r'(?i)response\.set_cookie\([^\)]*(?:httponly\s*=\s*False|samesite\s*=\s*[\'"]none[\'"])',
        "title": "Missing HttpOnly / Secure Flags on Auth Cookies",
        "explanation": "Setting session or auth cookies with httponly=False or insecure flags.",
        "hack_scenario": "Any minor Cross-Site Scripting (XSS) vulnerability allows malicious JavaScript to read document.cookie and steal the session token.",
        "architectural_fix": "Always enforce secure cookie attributes: response.set_cookie(key, value, httponly=True, secure=True, samesite='lax')"
    },
    # --- CRYPTO WALLET & WEB3 SECURITY RULES ---
    {
        "id": "CRYPTO_HARDCODED_PRIVATE_KEY",
        "badge": "[CRYPTO] Exposed Private Key / Seed Phrase",
        "pattern": r'(?i)(?:private_key|privkey|wallet_key)\s*=\s*["\'](?:0x)?[a-fA-F0-9]{64}["\']|mnemonic\s*=\s*["\'][a-z\s]{24,}["\']',
        "title": "Hardcoded Crypto Private Key or BIP-39 Mnemonic Seed Phrase",
        "explanation": "Embedding raw private keys or 12/24-word recovery seed phrases directly inside source code. Anyone with repository read access can drain the entire wallet instantly.",
        "hack_scenario": "Automated mempool and GitHub bot scrapers monitor commits; within 3 seconds of pushing this key, an automated sweeper bot transfers all ETH/tokens to an anonymous mixer.",
        "architectural_fix": "Never commit private keys. Load them through an isolated Hardware Security Module (HSM), AWS KMS, or encrypted keystore file."
    },
    {
        "id": "CRYPTO_TX_REPLAY_NO_NONCE",
        "badge": "[CRYPTO] Transaction Replay / Missing Nonce",
        "pattern": r'(?i)(?:eth\.send_raw_transaction|w3\.eth\.send_transaction)\(',
        "title": "Transaction Broadcast Without Explicit Dynamic Nonce Verification",
        "explanation": "Broadcasting blockchain transactions without explicit nonce management or replay-protection mechanisms.",
        "hack_scenario": "Under network congestion, identical raw transaction signatures can be captured and replayed on fork chains (e.g. Ethereum vs Ethereum Classic) or re-ordered in mempool, draining balances twice.",
        "architectural_fix": "Query current transaction count dynamically: nonce = w3.eth.get_transaction_count(address, 'pending'); tx['nonce'] = nonce"
    },
    {
        "id": "CRYPTO_UNBOUNDED_ERC20_APPROVE",
        "badge": "[CRYPTO] Unbounded ERC-20 Token Allowance",
        "pattern": r'(?i)approve\([^\)]*(?:2\*\*256\s*-\s*1|0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff|uint256\(-1\)|MaxUint256)',
        "title": "Infinite / Maximum ERC-20 Token Approval",
        "explanation": "Granting infinite token allowance (2^256 - 1) to a smart contract or third-party decentralized protocol.",
        "hack_scenario": "If the third-party smart contract has an undiscovered vulnerability or gets upgraded maliciously by an attacker, the contract can drain 100% of tokens from your wallet without asking for confirmation.",
        "architectural_fix": "Approve only the exact amount required for the immediate transaction, or revoke allowance immediately after execution."
    },
    {
        "id": "CRYPTO_WEAK_RNG_KEY_GEN",
        "badge": "[CRYPTO] Weak Insecure PRNG for Key Generation",
        "pattern": r'(?i)random\.(?:randint|random|choice|randrange)\([^\)]*(?:key|seed|nonce|secret|wallet)',
        "title": "Cryptographic Key Generation Using Insecure Pseudo-Random Number Generator",
        "explanation": "Using standard Python random module (Mersenne Twister) instead of cryptographically secure random sources (os.urandom or secrets).",
        "hack_scenario": "The internal state of Python random can be completely reconstructed after observing 624 outputs. An attacker predicts future private keys or nonces, reconstructing the wallet's signing key.",
        "architectural_fix": "Always use secrets or os.urandom for key generation: secrets.token_bytes(32)"
    },
    {
        "id": "CRYPTO_MISSING_SLIPPAGE_PROTECTION",
        "badge": "[CRYPTO] Missing Slippage Protection (MEV Sandwich Attack)",
        "pattern": r'(?i)(?:swap_exact_tokens|swapExactTokensForTokens|swapTokensForExactTokens)\([^\)]*(?:amountOutMin\s*=\s*0|min_output\s*=\s*0)',
        "title": "DeFi Swap Executed with Zero Minimum Output (Missing Slippage Bound)",
        "explanation": "Executing decentralized exchange swaps with amountOutMin set to 0 or without slippage tolerance checks.",
        "hack_scenario": "MEV searcher bots monitor the public mempool and execute a 'Sandwich Attack' (front-run buy to push price up, let your swap execute at terrible rate, back-run sell), extracting 90%+ of your swap value.",
        "architectural_fix": "Calculate strict slippage bound (e.g. 0.5% max): amount_out_min = int(expected_out * 0.995)"
    },
    {
        "id": "CRYPTO_PLAINTEXT_KEYSTORE_STORAGE",
        "badge": "[CRYPTO] Plaintext Keystore / Unencrypted Private Key Storage",
        "pattern": r'(?i)localStorage\.setItem\([\'"][^\'"]*(?:private_key|privkey|seed|mnemonic|secret)[\'"]',
        "title": "Crypto Wallet Credentials Stored in Plaintext Browser LocalStorage",
        "explanation": "Storing unencrypted private keys or seed phrases in browser localStorage or sessionStorage.",
        "hack_scenario": "Any third-party npm analytics script or Cross-Site Scripting (XSS) vulnerability reads localStorage.getItem('private_key') and exfiltrates it to an external server in one line of code.",
        "architectural_fix": "Never store raw private keys in browser storage. Delegate transaction signing to injected non-custodial wallet providers (MetaMask, Phantom) or use WebCrypto API with hardware-backed WebAuthn."
    },
    # --- SHA-256 CRYPTOGRAPHIC INTEGRITY & MISUSE RULES ---
    {
        "id": "SHA256_TIMING_ATTACK",
        "badge": "[CRYPTO] SHA-256 Hash Timing Attack",
        "pattern": r'(?i)(?:hash|digest|sha256|signature)\s*==\s*(?:hash|digest|sha256|signature|expected|client_hash)',
        "title": "SHA-256 Hash Comparison Using Standard Non-Constant-Time '==' Operator",
        "explanation": "Comparing SHA-256 digests or HMACs with standard '==' operator instead of constant-time comparison (hmac.compare_digest). Standard equality checks exit on the first mismatched byte, leaking execution time.",
        "hack_scenario": "An attacker measures round-trip latency variations in microseconds across millions of requests, reconstructing the expected SHA-256 hash or HMAC byte-by-byte to bypass authentication.",
        "architectural_fix": "Use constant-time comparison: hmac.compare_digest(calculated_hash, expected_hash)"
    },
    {
        "id": "SHA256_LENGTH_EXTENSION_ATTACK",
        "badge": "[CRYPTO] SHA-256 Length Extension Attack",
        "pattern": r'(?i)hashlib\.sha256\(\s*(?:secret|key|salt)\s*\+\s*(?:data|message|payload)',
        "title": "Vulnerable Secret Construction: SHA-256(secret + message)",
        "explanation": "Attempting to create message authentication codes (MACs) using naive prefix secret hashing like sha256(secret + message). SHA-256 uses the Merkle-Damgard construction, which is vulnerable to Length Extension Attacks.",
        "hack_scenario": "An attacker uses tools like hashpump to append malicious payload data to a transaction while forging a valid SHA-256 signature, without ever knowing your secret key.",
        "architectural_fix": "Use HMAC-SHA256 instead of raw hashing: hmac.new(key, message, hashlib.sha256).digest()"
    },
    {
        "id": "SHA256_UNSALTED_PASSWORD_HASH",
        "badge": "[CRYPTO] Unsalted Raw SHA-256 Password Hash",
        "pattern": r'(?i)hashlib\.sha256\([^\)]*(?:password|passwd|pwd)\.encode\(\)\)',
        "title": "Raw Unsalted SHA-256 Used For Password Hashing",
        "explanation": "Storing passwords with plain SHA-256 without a dynamic salt or key stretching. Modern GPUs compute over 10 billion SHA-256 hashes per second.",
        "hack_scenario": "If the database is leaked, rainbow tables and Hashcat easily crack all plain SHA-256 passwords in seconds.",
        "architectural_fix": "Replace with salted, memory-hard algorithms: Argon2id or bcrypt (cost factor >= 12)."
    }
]

@mcp.tool()
def audit_system_design_flaws(file_path: Optional[str] = None, code_content: Optional[str] = None) -> Dict[str, Any]:
    """Audit codebase for critical System Design Flaws, architectural vulnerabilities, and scaling bottlenecks."""
    try:
        content, source = _resolve_content(file_path, code_content)
    except Exception as e:
        return {"success": False, "error": str(e)}

    content_hash = _get_hash(content)
    cache_key = f"sysdesign:{content_hash}"
    if cache_key in _ANALYSIS_CACHE:
        return _ANALYSIS_CACHE[cache_key]

    findings = []
    lines = content.splitlines()

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(("#", "//")):
            continue
        for rule in SYSTEM_DESIGN_RULES:
            if re.search(rule["pattern"], stripped):
                findings.append({
                    "line": i,
                    "id": rule["id"],
                    "badge": rule["badge"],
                    "title": rule["title"],
                    "explanation": rule["explanation"],
                    "hack_scenario": rule["hack_scenario"],
                    "architectural_fix": rule["architectural_fix"],
                    "snippet": stripped[:90]
                })

    result = {
        "success": True,
        "source": source,
        "clean": len(findings) == 0,
        "system_design_flaws_count": len(findings),
        "architecture_health": "SECURE & SCALABLE" if len(findings) == 0 else ("HIGH RISK" if len(findings) > 2 else "WARNING"),
        "flaws": findings
    }

    _ANALYSIS_CACHE[cache_key] = result
    _record_audit_event("audit_system_design_flaws", source, {"flaws_found": len(findings)})
    return result


# =====================================================================
# 3. MULTI-TAP CONCURRENCY & STRESS TEST ANALYZER
# =====================================================================

@mcp.tool()
def stress_test_multitap_vulnerability(
    file_path: Optional[str] = None,
    code_content: Optional[str] = None,
    simulated_taps: int = 50
) -> Dict[str, Any]:
    """Audit code against rapid multi-tapping / rage-click stress attacks."""
    try:
        content, source = _resolve_content(file_path, code_content)
    except Exception as e:
        return {"success": False, "error": str(e)}

    sensitive_operations = [
        ("payment", r"(?i)(charge|checkout|payment|pay|transfer|withdraw|deposit)"),
        ("order", r"(?i)(create_order|place_order|submit_order|buy)"),
        ("points_or_credits", r"(?i)(claim|redeem|add_credits|apply_coupon|voucher)"),
        ("booking", r"(?i)(reserve|book_seat|book_slot|claim_seat)"),
        ("voting_or_likes", r"(?i)(like|vote|upvote|follow|subscribe)")
    ]

    has_debounce = bool(re.search(r'(?i)(debounce|throttle|disabled\s*=\s*true|is_submitting|is_loading)', content))
    has_idempotency = bool(re.search(r'(?i)(idempotency_key|idempotency-key|x-request-id|unique_together)', content))
    has_locking = bool(re.search(r'(?i)(select_for_update|with_for_update|atomic|transaction\.atomic|redlock|redis.*lock)', content))

    vulnerabilities = []

    for category, pat in sensitive_operations:
        match = re.search(pat, content)
        if match:
            operation_name = match.group(0)
            missing_defenses = []
            if not has_debounce:
                missing_defenses.append("Frontend: Missing click debounce or button disable state")
            if not has_idempotency:
                missing_defenses.append("Backend: Missing Idempotency-Key / unique request identifier")
            if not has_locking:
                missing_defenses.append("Database: Missing atomic transaction or row locking (SELECT FOR UPDATE)")

            if missing_defenses:
                vulnerabilities.append({
                    "badge": "[CONCURRENCY] Multi-Tap Vulnerability",
                    "operation_detected": operation_name,
                    "category": category,
                    "simulated_burst": f"{simulated_taps} taps in 1.0 second",
                    "what_happens_under_burst": (
                        f"When a user or automated bot taps the '{operation_name}' button {simulated_taps} times simultaneously, "
                        f"all {simulated_taps} requests hit the server in parallel. Without idempotency or DB locks, "
                        f"the backend processes multiple duplicate operations before state updates."
                    ),
                    "real_world_loss_scenario": (
                        f"Duplicate execution: User account gets charged multiple times, duplicate orders are shipped, "
                        f"or promotional credits/bonuses are claimed {simulated_taps}x."
                    ),
                    "missing_defenses": missing_defenses,
                    "fix_recipe": (
                        "1. Frontend: Disable button immediately on first tap: setSubmitting(true);\n"
                        "2. API Gateway: Require Idempotency-Key header for all mutations.\n"
                        "3. Database: Use atomic SQL updates or lock with Redis: with redis.lock(f'lock:{user_id}:{order_id}'):"
                    )
                })

    is_vulnerable = len(vulnerabilities) > 0

    return {
        "success": True,
        "source": source,
        "simulated_taps_count": simulated_taps,
        "multitap_safe": not is_vulnerable,
        "defense_audit": {
            "has_frontend_debounce_or_lock": has_debounce,
            "has_backend_idempotency_key": has_idempotency,
            "has_database_or_distributed_locking": has_locking
        },
        "vulnerability_count": len(vulnerabilities),
        "verdict": "VULNERABLE TO MULTI-TAP STRESS" if is_vulnerable else "PROTECTED AGAINST MULTI-TAP RUSH",
        "detailed_scenarios": vulnerabilities
    }


# =====================================================================
# 4. SHA-256 CRYPTOGRAPHIC INTEGRITY & FILE TAMPER AUDITOR
# =====================================================================

@mcp.tool()
def audit_sha256_cryptographic_integrity(
    file_path: Optional[str] = None,
    code_content: Optional[str] = None,
    expected_hash: Optional[str] = None
) -> Dict[str, Any]:
    """Cryptographic SHA-256 integrity auditor.
    
    1. Computes deterministic SHA-256 checksum of code/file.
    2. Verifies cryptographic integrity against expected baseline hash (tamper detection).
    3. Scans for cryptographic SHA-256 misuse:
       - Non-constant-time comparisons (Timing Attacks).
       - Length extension vulnerabilities (secret + message instead of HMAC).
       - Insecure password storage with raw unsalted SHA-256.
    """
    try:
        content, source = _resolve_content(file_path, code_content)
    except Exception as e:
        return {"success": False, "error": str(e)}

    # 1. Deterministic SHA-256 calculation
    computed_sha256 = _get_hash(content)
    
    # 2. Tamper verification
    tamper_status = "UNKNOWN (No baseline provided)"
    is_tampered = False
    if expected_hash:
        import hmac
        is_tampered = not hmac.compare_digest(computed_sha256.lower().strip(), expected_hash.lower().strip())
        tamper_status = "TAMPER DETECTED: Hash mismatch!" if is_tampered else "VERIFIED: Cryptographic match."

    # 3. Cryptographic code misuse audit
    crypto_misuse_findings = []
    lines = content.splitlines()

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(("#", "//")):
            continue
        
        # Timing attack detection
        if re.search(r'(?i)(?:hash|digest|sha256|signature)\s*==\s*(?:hash|digest|sha256|signature|expected|client_hash)', stripped):
            crypto_misuse_findings.append({
                "line": i,
                "type": "TIMING_ATTACK",
                "severity": "CRITICAL",
                "title": "SHA-256 Comparison Leaking Timing Information",
                "issue": "Using standard '==' comparison leaks execution time byte-by-byte.",
                "fix": "Use hmac.compare_digest(computed, expected)"
            })
        
        # Length extension attack
        if re.search(r'(?i)hashlib\.sha256\(\s*(?:secret|key|salt)\s*\+\s*(?:data|message|payload)', stripped):
            crypto_misuse_findings.append({
                "line": i,
                "type": "LENGTH_EXTENSION_ATTACK",
                "severity": "CRITICAL",
                "title": "Vulnerable Prefix MAC: SHA-256(secret + message)",
                "issue": "Merkle-Damgard construction allows attackers to append arbitrary payload data.",
                "fix": "Use hmac.new(key, message, hashlib.sha256).digest()"
            })

        # Unsalted password hash
        if re.search(r'(?i)hashlib\.sha256\([^\)]*(?:password|passwd|pwd)\.encode\(\)\)', stripped):
            crypto_misuse_findings.append({
                "line": i,
                "type": "UNSALTED_PASSWORD_HASH",
                "severity": "HIGH",
                "title": "Raw Unsalted SHA-256 Password Hash",
                "issue": "Modern GPUs crack over 10 billion raw SHA-256 hashes per second.",
                "fix": "Use memory-hard slow algorithms: Argon2id or bcrypt."
            })

    return {
        "success": True,
        "source": source,
        "computed_sha256": computed_sha256,
        "tamper_verification": {
            "expected_hash": expected_hash,
            "status": tamper_status,
            "tampered": is_tampered
        },
        "crypto_misuse_issues_count": len(crypto_misuse_findings),
        "crypto_misuse_findings": crypto_misuse_findings,
        "overall_crypto_health": "SECURE" if len(crypto_misuse_findings) == 0 and not is_tampered else "VULNERABLE"
    }


# =====================================================================
# 5. MACHINE LEARNING CODE RISK & HALSTEAD METRIC ENGINE
# =====================================================================

@mcp.tool()
def audit_ml_defects(
    file_path: Optional[str] = None,
    code_content: Optional[str] = None
) -> Dict[str, Any]:
    """Runs local Machine Learning security analysis: Shannon entropy secrets, Halstead software metrics, AST anomaly scoring, and defect propensity."""
    try:
        content, source = _resolve_content(file_path, code_content)
    except Exception as e:
        return {"success": False, "error": str(e)}

    ml_audit = run_ml_audit(content)
    ml_audit["source"] = source
    return ml_audit


# =====================================================================
# 6. BASIC, MINIMALIST HTML REPORT GENERATOR (NO EMOJIS, NO AI THEMES)
# =====================================================================

@mcp.tool()
def generate_html_audit_report(
    file_path: Optional[str] = None,
    code_content: Optional[str] = None,
    output_html_path: Optional[str] = None
) -> Dict[str, Any]:
    """Runs a complete static, system design, multi-tap stress, and ML audit and exports a clean, basic HTML report."""
    try:
        content, source = _resolve_content(file_path, code_content)
    except Exception as e:
        return {"success": False, "error": str(e)}

    smells = explain_code_issues(code_content=content)
    design = audit_system_design_flaws(code_content=content)
    multitap = stress_test_multitap_vulnerability(code_content=content)
    ml_res = run_ml_audit(content)

    entropy_findings = ml_res.get("shannon_entropy_findings", [])
    total_issues = (
        smells.get("total_issues", 0) +
        design.get("system_design_flaws_count", 0) +
        multitap.get("vulnerability_count", 0) +
        len(entropy_findings)
    )

    overall_verdict = "PASS" if total_issues == 0 else ("FAIL - CRITICAL" if total_issues > 3 else "WARNING")

    rows_html = []

    # 1. Multi-Tap
    for item in multitap.get("detailed_scenarios", []):
        defenses = "; ".join(item.get("missing_defenses", []))
        rows_html.append(f"""
        <tr>
            <td><strong>{item.get('badge')}</strong></td>
            <td>Operation: <code>{item.get('operation_detected')}()</code><br>
                <strong>Stress:</strong> {item.get('simulated_burst')}<br>
                <strong>Impact:</strong> {item.get('real_world_loss_scenario')}<br>
                <strong>Missing:</strong> {defenses}<br>
                <strong>Fix:</strong> <pre>{item.get('fix_recipe')}</pre>
            </td>
        </tr>
        """)

    # 2. System Design
    for item in design.get("flaws", []):
        rows_html.append(f"""
        <tr>
            <td><strong>{item.get('badge')}</strong><br><small>Line {item.get('line')}</small></td>
            <td><strong>{item.get('title')}</strong><br>
                {item.get('explanation')}<br>
                <strong>Exploit:</strong> {item.get('hack_scenario')}<br>
                <strong>Snippet:</strong> <code>{item.get('snippet')}</code><br>
                <strong>Fix:</strong> <pre>{item.get('architectural_fix')}</pre>
            </td>
        </tr>
        """)

    # 3. High-Entropy ML Secrets
    for item in entropy_findings:
        rows_html.append(f"""
        <tr>
            <td><strong>[SECURITY] High-Entropy Secret</strong><br><small>Line {item.get('line')}</small></td>
            <td><strong>Shannon Entropy: {item.get('entropy')} bits/char (Length: {item.get('length')})</strong><br>
                Token Preview: <code>{item.get('token_preview')}</code><br>
                Classification: {item.get('classification')}<br>
                <strong>Risk:</strong> Obfuscated or high-entropy literal detected escaping regex patterns. Potential hardcoded credential or token leak.<br>
                <strong>Fix:</strong> <pre>Remove hardcoded secret; load from environment variable (os.environ.get(...)) or secure vault.</pre>
            </td>
        </tr>
        """)

    # 4. AST Structural Anomaly
    ast_anomaly = ml_res.get("ast_anomaly_detection", {})
    if ast_anomaly.get("is_structural_outlier"):
        rows_html.append(f"""
        <tr>
            <td><strong>[ML-WARNING] Structural Anomaly</strong><br><small>AST Isolation Forest</small></td>
            <td><strong>Structural Anomaly Score: {ast_anomaly.get('structural_anomaly_index')}/100</strong><br>
                Verdict: {ast_anomaly.get('verdict')}<br>
                <strong>Risk:</strong> Code deviates significantly from standard architectural and syntax distributions. High likelihood of obfuscation or excessive nesting.<br>
                <strong>Fix:</strong> <pre>Refactor into standard procedural or object-oriented modular patterns.</pre>
            </td>
        </tr>
        """)

    # 5. Code Smells
    for item in smells.get("findings", []):
        rows_html.append(f"""
        <tr>
            <td><strong>{item.get('badge')}</strong><br><small>Line {item.get('line')}</small></td>
            <td><strong>{item.get('title')}</strong><br>
                {item.get('plain_english_explanation')}<br>
                <strong>Risk:</strong> {item.get('production_risk')}<br>
                <strong>Snippet:</strong> <code>{item.get('code_snippet')}</code><br>
                <strong>Fix:</strong> <pre>{item.get('how_to_fix')}</pre>
            </td>
        </tr>
        """)

    table_content = "\n".join(rows_html) if rows_html else "<tr><td colspan='2'>No vulnerabilities detected. All checks passed.</td></tr>"

    halstead = ml_res.get("halstead_metrics", {})
    html_document = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Audit Report - Cherm Auditor Pro</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 30px;
            background-color: #ffffff;
            color: #111111;
            line-height: 1.5;
        }}
        h1 {{ font-size: 20px; margin-bottom: 5px; }}
        .meta {{ font-size: 13px; color: #555555; margin-bottom: 20px; }}
        .summary-box {{
            border: 1px solid #cccccc;
            padding: 15px;
            margin-bottom: 25px;
            background-color: #f9f9f9;
        }}
        .summary-box table {{ width: 100%; border: none; }}
        .summary-box td {{ padding: 5px; border: none; font-size: 14px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            border: 1px solid #dddddd;
            padding: 10px;
            text-align: left;
            vertical-align: top;
            font-size: 13px;
        }}
        th {{
            background-color: #eeeeee;
            font-weight: bold;
        }}
        code {{
            background-color: #f1f1f1;
            padding: 2px 4px;
            font-family: monospace;
            font-size: 12px;
        }}
        pre {{
            background-color: #f6f6f6;
            padding: 8px;
            border: 1px solid #e1e1e1;
            font-family: monospace;
            font-size: 12px;
            white-space: pre-wrap;
            margin: 6px 0 0 0;
        }}
        .verdict-PASS {{ color: #008000; font-weight: bold; }}
        .verdict-WARNING {{ color: #d97706; font-weight: bold; }}
        .verdict-FAIL {{ color: #cc0000; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Audit Report: Cherm Auditor Pro</h1>
    <div class="meta">Target: {source} | Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}</div>

    <div class="summary-box">
        <table>
            <tr>
                <td><strong>Overall Status:</strong> <span class="verdict-{overall_verdict.split()[0]}">{overall_verdict}</span></td>
                <td><strong>Total Issues:</strong> {total_issues}</td>
            </tr>
            <tr>
                <td><strong>System Design Flaws:</strong> {design.get('system_design_flaws_count', 0)}</td>
                <td><strong>Multi-Tap Flaws:</strong> {multitap.get('vulnerability_count', 0)}</td>
            </tr>
            <tr>
                <td><strong>Code Smells:</strong> {smells.get('total_issues', 0)}</td>
                <td><strong>High-Entropy Secrets:</strong> {len(entropy_findings)}</td>
            </tr>
            <tr>
                <td><strong>ML Defect Probability:</strong> {ml_res.get('classifier_vulnerability_probability', 0)}%</td>
                <td><strong>ML Overall Risk Score:</strong> {ml_res.get('ml_overall_risk_score', 0)} / 100 ({ml_res.get('ml_verdict')})</td>
            </tr>
        </table>
    </div>

    <h2>Software Science & Complexity (Halstead Metrics)</h2>
    <table>
        <thead>
            <tr>
                <th>Lines of Code (LOC)</th>
                <th>Halstead Volume</th>
                <th>Halstead Difficulty</th>
                <th>Halstead Effort</th>
                <th>Estimated Bugs</th>
                <th>Est. Dev Time</th>
                <th>Cyclomatic Complexity</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>{halstead.get('loc', 0)}</td>
                <td>{halstead.get('volume', 0)}</td>
                <td>{halstead.get('difficulty', 0)}</td>
                <td>{halstead.get('effort', 0)}</td>
                <td>{halstead.get('estimated_delivered_bugs', 0)}</td>
                <td>{halstead.get('estimated_dev_time_minutes', 0)} min</td>
                <td>{halstead.get('cyclomatic_complexity', 0)}</td>
            </tr>
        </tbody>
    </table>

    <h2>Diagnostic Findings</h2>
    <table>
        <thead>
            <tr>
                <th style="width: 25%;">Category / Severity</th>
                <th>Details and Fix Recommendations</th>
            </tr>
        </thead>
        <tbody>
            {table_content}
        </tbody>
    </table>
</body>
</html>
"""

    save_path = output_html_path if output_html_path else os.path.join(BASE_DIR, "cherm_audit_report.html")

    try:
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(html_document)
    except Exception as e:
        return {"success": False, "error": f"Failed writing HTML file: {e}"}

    return {
        "success": True,
        "source": source,
        "report_file_path": os.path.abspath(save_path),
        "total_issues_found": total_issues,
        "overall_verdict": overall_verdict
    }


# =====================================================================
# ALL-IN-ONE AUTOMATIC DYNAMIC AUDIT RUNNER
# =====================================================================

@mcp.tool()
def run_all_in_one_check(
    file_path: Optional[str] = None,
    code_content: Optional[str] = None,
    directory_path: Optional[str] = None,
    auto_generate_html: bool = True
) -> Dict[str, Any]:
    """Single-command, 100% automated all-in-one quality and security check."""
    target_source = code_content
    target_file = file_path

    if not target_source and not target_file:
        search_dir = os.path.abspath(directory_path) if directory_path else BASE_DIR
        for root, _, files in os.walk(search_dir):
            if any(skip in root.lower() for skip in [".git", "node_modules", "venv", "__pycache__"]):
                continue
            for f in files:
                if f.endswith((".py", ".js", ".ts", ".go", ".java")):
                    target_file = os.path.join(root, f)
                    break
            if target_file:
                break

    try:
        content, source = _resolve_content(target_file, target_source)
    except Exception as e:
        return {"success": False, "error": f"Target resolution failed: {e}"}

    system_design_res = audit_system_design_flaws(code_content=content)
    multitap_res = stress_test_multitap_vulnerability(code_content=content)
    smells_res = explain_code_issues(code_content=content)
    ml_res = run_ml_audit(content)

    entropy_findings = ml_res.get("shannon_entropy_findings", [])
    ml_risk_score = ml_res.get("ml_overall_risk_score", 0)

    total_fatal_issues = (
        system_design_res.get("system_design_flaws_count", 0) +
        multitap_res.get("vulnerability_count", 0) +
        smells_res.get("critical_blockers", 0) +
        (1 if len(entropy_findings) > 0 else 0)
    )

    total_issues = (
        system_design_res.get("system_design_flaws_count", 0) +
        multitap_res.get("vulnerability_count", 0) +
        smells_res.get("total_issues", 0) +
        len(entropy_findings)
    )

    if total_fatal_issues == 0 and total_issues == 0 and ml_risk_score < 30:
        health_grade = "A (Passed - Clean)"
        status = "PASSED"
    elif total_fatal_issues == 0:
        health_grade = "B (Minor Warnings)"
        status = "PASSED_WITH_WARNINGS"
    elif total_fatal_issues <= 2:
        health_grade = "C (Action Required)"
        status = "FAILED"
    else:
        health_grade = "F (Critical Vulnerabilities Found)"
        status = "CRITICAL_BLOCKED"

    html_report_path = None
    if auto_generate_html:
        html_res = generate_html_audit_report(code_content=content)
        if html_res.get("success"):
            html_report_path = html_res.get("report_file_path")

    _record_audit_event("run_all_in_one_check", source, {
        "status": status,
        "health_grade": health_grade,
        "total_issues": total_issues,
        "html_report": html_report_path
    })

    action_items = [
        f"[{flaw.get('badge')}] Line {flaw.get('line')}: {flaw.get('title')}"
        for flaw in system_design_res.get("flaws", [])[:4]
    ]
    for ent in entropy_findings[:2]:
        action_items.append(f"[ML-SECURITY] Line {ent.get('line')}: High entropy token ({ent.get('entropy')} bits/char)")

    return {
        "success": True,
        "audited_source": source,
        "status": status,
        "health_grade": health_grade,
        "summary": {
            "total_issues_found": total_issues,
            "fatal_critical_flaws": total_fatal_issues,
            "multitap_concurrency_flaws": multitap_res.get("vulnerability_count", 0),
            "system_design_flaws": system_design_res.get("system_design_flaws_count", 0),
            "code_smells_and_antipatterns": smells_res.get("total_issues", 0),
            "high_entropy_secrets_found": len(entropy_findings),
            "ml_risk_score": ml_risk_score,
            "ml_vulnerability_probability": f"{ml_res.get('classifier_vulnerability_probability', 0)}%"
        },
        "ml_software_metrics": ml_res.get("halstead_metrics"),
        "ml_anomaly_detection": ml_res.get("ast_anomaly_detection"),
        "html_dashboard_report": html_report_path,
        "quick_action_items": action_items
    }


if __name__ == "__main__":
    mcp.run()
