# Cherm Audit Rules & Workflows

### Hybrid Cherm + AI Review Workflow (`@cherm-audit` / `audit with cherm`)
Whenever the user asks to audit, review, or check code using Cherm:

**The 3-Stage Hybrid Pipeline:**
1. **Stage 1 (Cherm Deterministic Static Check):**
   - Run `cherm_mcp.run_all_in_one_check` or `cherm_mcp.audit_system_design_flaws` on the target code/file.
   - Cherm rapidly scans for multi-tap race conditions, DB pool starvation, BOLA/IDOR, crypto flaws, and code smells without using AI tokens.
   - Cherm automatically compiles the raw findings into `cherm_audit_report.html`.

2. **Stage 2 (AI Verification & Second Opinion Filter):**
   - As the AI (Antigravity), inspect each of Cherm's static findings against the actual code logic.
   - Filter out false positives (e.g. static patterns that are safe because of out-of-band middleware, or intentional exceptions).
   - Confirm true positives and provide contextual reasoning on severity.

3. **Stage 3 (User Control & Decision Gate):**
   - Present a concise, prioritized review summary to the user:
     - **Confirmed Issues:** Real bugs/risks with recommended fixes.
     - **Dismissed False Positives:** Flags from Cherm that were safely handled.
   - Ask the user for confirmation: *"Would you like me to apply these fixes to the file now?"*
   - Never overwrite code until the user gives explicit approval.

