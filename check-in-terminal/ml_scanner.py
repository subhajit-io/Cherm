"""
ML Security & Code Risk Engine for CheckInTerminal (Cherm Auditor Pro)
Pure local, zero-token, high-performance static intelligence engine:

1. Formal Halstead Software Science & AST Structural Metrics:
   - Operators & Operands frequency analysis via Python AST visitor
   - Halstead Volume, Difficulty, Effort, Bugs Delivered, and Development Time
   - Cyclomatic Complexity and Maximum Nesting Depth
2. Information Entropy & Obfuscation Analysis:
   - Shannon Entropy calculation per string literal
   - 2-gram and 3-gram character redundancy scoring
   - High-entropy secret and token leak detection
3. AST Structural Anomaly Detection:
   - Vectorization of AST node frequencies
   - Isolation Forest outlier scoring for structural irregularity
4. Machine Learning Defect Classifier:
   - TF-IDF (1-2 n-grams) + Random Forest ensemble
   - Predicts vulnerability probability across OWASP & architecture flaws
"""

import ast
import math
import os
import re
from typing import Dict, Any, List, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier, IsolationForest

# =====================================================================
# 1. SHANNON ENTROPY & STRING ANALYSIS
# =====================================================================

def calculate_shannon_entropy(data: str) -> float:
    """Calculates Shannon Entropy (bits per character) to detect encrypted/random tokens."""
    if not data:
        return 0.0
    length = len(data)
    counts: Dict[str, int] = {}
    for char in data:
        counts[char] = counts.get(char, 0) + 1
    entropy = 0.0
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy

def extract_high_entropy_literals(source_code: str, min_len: int = 14, min_entropy: float = 3.75) -> List[Dict[str, Any]]:
    """Extracts string literals and checks for obfuscated, random, or cryptographic tokens."""
    findings = []
    lines = source_code.splitlines()
    for i, line in enumerate(lines, 1):
        # Extract quoted strings
        literals = re.findall(r'["\']([^"\'\\]{14,})["\']', line)
        for lit in literals:
            # Skip obvious URL patterns or simple human readable strings with many spaces
            if lit.count(" ") > 3 or lit.startswith("http://") or lit.startswith("https://"):
                continue
            ent = calculate_shannon_entropy(lit)
            if ent >= min_entropy:
                token_preview = lit[:8] + "..." + lit[-4:] if len(lit) > 14 else lit
                classification = (
                    "CRITICAL_HIGH_ENTROPY_KEY" if ent > 4.3 and len(lit) >= 20
                    else "SUSPICIOUS_TOKEN_OR_HASH"
                )
                findings.append({
                    "line": i,
                    "token_preview": token_preview,
                    "length": len(lit),
                    "entropy": round(ent, 3),
                    "classification": classification
                })
    return findings


# =====================================================================
# 2. HALSTEAD SOFTWARE SCIENCE & AST METRICS
# =====================================================================

class HalsteadVisitor(ast.NodeVisitor):
    """Traverses Python AST to extract genuine Halstead operators and operands."""
    def __init__(self):
        self.operators: List[str] = []
        self.operands: List[str] = []
        self.node_counts: Dict[str, int] = {}

    def generic_visit(self, node):
        node_name = type(node).__name__
        self.node_counts[node_name] = self.node_counts.get(node_name, 0) + 1
        super().generic_visit(node)

    def visit_BinOp(self, node):
        self.operators.append(type(node.op).__name__)
        self.generic_visit(node)

    def visit_UnaryOp(self, node):
        self.operators.append(type(node.op).__name__)
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.operators.append(type(node.op).__name__)
        self.generic_visit(node)

    def visit_Compare(self, node):
        for op in node.ops:
            self.operators.append(type(op).__name__)
        self.generic_visit(node)

    def visit_Call(self, node):
        self.operators.append("Call")
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.operators.append("FunctionDef")
        self.operands.append(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.operators.append("AsyncFunctionDef")
        self.operands.append(node.name)
        self.generic_visit(node)

    def visit_Name(self, node):
        self.operands.append(node.id)
        self.generic_visit(node)

    def visit_Constant(self, node):
        self.operands.append(repr(node.value))
        self.generic_visit(node)

    def visit_Return(self, node):
        self.operators.append("Return")
        self.generic_visit(node)

    def visit_If(self, node):
        self.operators.append("If")
        self.generic_visit(node)

    def visit_For(self, node):
        self.operators.append("For")
        self.generic_visit(node)

    def visit_While(self, node):
        self.operators.append("While")
        self.generic_visit(node)

    def visit_Try(self, node):
        self.operators.append("Try")
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.operators.append("ExceptHandler")
        self.generic_visit(node)


def calculate_halstead_and_ast_metrics(source_code: str) -> Dict[str, Any]:
    """Computes full Halstead complexity metrics, cyclomatic score, and AST node distribution."""
    lines = source_code.splitlines()
    total_loc = len(lines)
    blank_lines = sum(1 for l in lines if not l.strip())
    comment_lines = sum(1 for l in lines if l.strip().startswith(("#", "//", "/*", "*")))
    code_loc = max(1, total_loc - blank_lines - comment_lines)

    # Maximum nesting depth
    max_indent = 0
    for line in lines:
        stripped = line.lstrip(" ")
        if stripped:
            indent = len(line) - len(stripped)
            max_indent = max(max_indent, indent // 4)

    visitor = HalsteadVisitor()
    try:
        tree = ast.parse(source_code)
        visitor.visit(tree)
    except SyntaxError:
        # Fallback regex tokenization for non-Python or broken syntax
        words = re.findall(r'\b[a-zA-Z_]\w*\b', source_code)
        operators = re.findall(r'[+\-*/%=&|^<>!]+|==|!=|<=|>=', source_code)
        visitor.operands = words
        visitor.operators = operators

    n1 = len(set(visitor.operators))  # Unique operators
    n2 = len(set(visitor.operands))   # Unique operands
    N1 = len(visitor.operators)        # Total operators
    N2 = len(visitor.operands)         # Total operands

    vocabulary = n1 + n2
    length = N1 + N2
    volume = length * math.log2(max(2, vocabulary)) if vocabulary > 1 else 0.0
    difficulty = ((n1 / 2.0) * (N2 / max(1, n2))) if n2 > 0 else 0.0
    effort = difficulty * volume
    delivered_bugs = (volume ** (2 / 3)) / 3000.0 if volume > 0 else 0.0
    time_to_code_sec = effort / 18.0

    # Cyclomatic decision points
    cyclomatic = 1 + sum(visitor.operators.count(op) for op in ["If", "For", "While", "ExceptHandler"])

    # Composite risk score 0 - 100
    defect_risk = min(100, int((cyclomatic * 2.2) + (max_indent * 7) + (volume / 200)))

    return {
        "loc": code_loc,
        "max_nesting_depth": max_indent,
        "cyclomatic_complexity": cyclomatic,
        "distinct_operators_n1": n1,
        "distinct_operands_n2": n2,
        "total_operators_N1": N1,
        "total_operands_N2": N2,
        "halstead_vocabulary": vocabulary,
        "halstead_length": length,
        "halstead_volume": round(volume, 2),
        "halstead_difficulty": round(difficulty, 2),
        "halstead_effort": round(effort, 2),
        "estimated_delivered_bugs": round(delivered_bugs, 4),
        "estimated_dev_time_minutes": round(time_to_code_sec / 60.0, 1),
        "defect_probability_score": defect_risk,
        "risk_level": "CRITICAL" if defect_risk > 70 else ("HIGH" if defect_risk > 40 else "NORMAL"),
        "ast_node_distribution": visitor.node_counts
    }


# =====================================================================
# 3. UNSUPERVISED AST ANOMALY DETECTION (ISOLATION FOREST)
# =====================================================================

class ASTAnomalyDetector:
    """Detects structural anomalies using Isolation Forest on AST node density profiles."""
    FEATURE_KEYS = [
        "FunctionDef", "Call", "If", "For", "While", "Try",
        "ExceptHandler", "BinOp", "Compare", "Constant", "Name"
    ]

    def __init__(self):
        self.model = IsolationForest(n_estimators=50, contamination=0.1, random_state=42)
        self._fit_baseline()

    def _extract_vector(self, node_counts: Dict[str, int]) -> np.ndarray:
        return np.array([node_counts.get(k, 0) for k in self.FEATURE_KEYS], dtype=float)

    def _fit_baseline(self):
        # Baseline normal distributions for standard functions
        normal_samples = [
            {"FunctionDef": 1, "Call": 2, "If": 1, "Constant": 4, "Name": 6},
            {"FunctionDef": 2, "Call": 5, "If": 2, "Try": 1, "ExceptHandler": 1, "Constant": 8, "Name": 12},
            {"FunctionDef": 1, "Call": 1, "Constant": 2, "Name": 3},
            {"FunctionDef": 3, "Call": 8, "If": 3, "For": 1, "BinOp": 2, "Constant": 10, "Name": 20},
            {"FunctionDef": 1, "Call": 3, "If": 1, "Constant": 5, "Name": 8},
        ]
        X = np.array([self._extract_vector(d) for d in normal_samples])
        self.model.fit(X)

    def score_structural_anomaly(self, node_counts: Dict[str, int]) -> Dict[str, Any]:
        vec = self._extract_vector(node_counts).reshape(1, -1)
        score = float(self.model.score_samples(vec)[0])
        # Score typically ranges between -0.8 (highly anomalous) to -0.3 (normal)
        # Normalize to 0-100 anomaly index
        anomaly_index = max(0, min(100, int(((-score) - 0.3) * 200)))
        is_anomaly = anomaly_index > 65
        return {
            "raw_anomaly_score": round(score, 4),
            "structural_anomaly_index": anomaly_index,
            "is_structural_outlier": is_anomaly,
            "verdict": "ANOMALOUS_STRUCTURE" if is_anomaly else "NORMAL_STRUCTURE"
        }


# =====================================================================
# 4. SUPERVISED VULNERABILITY & ANTI-PATTERN CLASSIFIER
# =====================================================================

class MLCodeClassifier:
    """Pre-trained NLP & Statistical Classifier identifying defect-prone vs safe patterns."""
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=350, token_pattern=r'\b\w+\b', ngram_range=(1, 2))
        self.model = RandomForestClassifier(n_estimators=60, random_state=42)
        self._init_training()

    def _init_training(self):
        samples = [
            # Safe code (0)
            "with open('file.txt', 'r') as f: data = f.read()",
            "db.session.query(User).filter_by(id=uid, tenant_id=tenant).first()",
            "jwt.decode(token, secret, algorithms=['HS256'])",
            "response = requests.get(url, timeout=(3, 10))",
            "def add_item(item, container=None):\n    if container is None: container = []",
            "cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
            "hmac.compare_digest(hash1, hash2)",
            "allow_origins=['https://trusted.domain.com']",
            "db.session.query(Account).with_for_update().filter_by(id=acc_id).first()",
            "def process(x: int) -> int: return x * 2",
            "except KeyError as e: logger.error(f'Missing key: {e}')",
            "subprocess.run(['ls', '-l'], check=True)",
            "yaml.safe_load(data)",

            # Defective / Vulnerable code (1)
            "f = open('file.txt')\ndata = f.read()",
            "User.query.filter_by(id=request.id).first()",
            "jwt.decode(token, verify_signature=False)",
            "requests.get(url)",
            "def add_item(item, container=[]): container.append(item)",
            "cursor.execute(f'SELECT * FROM users WHERE id = {user_id}')",
            "if hash1 == hash2: return True",
            "allow_origins=['*']",
            "balance = acc.balance; acc.balance = balance - amount; db.session.commit()",
            "except: pass",
            "os.system(f'rm -rf {path}')",
            "eval(user_input)",
            "pickle.loads(untrusted_bytes)",
            "yaml.load(data, Loader=yaml.Loader)"
        ]
        labels = [
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1
        ]
        X = self.vectorizer.fit_transform(samples)
        self.model.fit(X, labels)

    def predict_vulnerability_probability(self, code_snippet: str) -> float:
        try:
            X_test = self.vectorizer.transform([code_snippet])
            prob = self.model.predict_proba(X_test)[0][1]
            return round(float(prob), 3)
        except Exception:
            return 0.5


# Singleton instances
_CLASSIFIER = MLCodeClassifier()
_ANOMALY_DETECTOR = ASTAnomalyDetector()

# =====================================================================
# 5. PUBLIC ML AUDIT INTERFACE
# =====================================================================

def run_ml_audit(source_code: str) -> Dict[str, Any]:
    """Runs full Machine Learning security, Halstead science, and entropy audit."""
    entropy_secrets = extract_high_entropy_literals(source_code)
    metrics = calculate_halstead_and_ast_metrics(source_code)
    anomaly_res = _ANOMALY_DETECTOR.score_structural_anomaly(metrics["ast_node_distribution"])
    defect_prob = _CLASSIFIER.predict_vulnerability_probability(source_code)

    overall_ml_score = int(
        (defect_prob * 45) +
        (min(100, metrics["defect_probability_score"]) * 0.35) +
        (min(100, len(entropy_secrets) * 25) * 0.20)
    )

    verdict = (
        "CRITICAL_RISK" if overall_ml_score >= 65
        else ("ELEVATED_RISK" if overall_ml_score >= 35 else "CONFIDENT_CLEAN")
    )

    return {
        "success": True,
        "ml_overall_risk_score": min(100, overall_ml_score),
        "ml_verdict": verdict,
        "shannon_entropy_findings": entropy_secrets,
        "obfuscated_secrets_count": len(entropy_secrets),
        "halstead_metrics": {
            "vocabulary": metrics["halstead_vocabulary"],
            "length": metrics["halstead_length"],
            "volume": metrics["halstead_volume"],
            "difficulty": metrics["halstead_difficulty"],
            "effort": metrics["halstead_effort"],
            "estimated_delivered_bugs": metrics["estimated_delivered_bugs"],
            "estimated_dev_time_minutes": metrics["estimated_dev_time_minutes"],
            "cyclomatic_complexity": metrics["cyclomatic_complexity"],
            "max_nesting_depth": metrics["max_nesting_depth"],
            "loc": metrics["loc"]
        },
        "ast_anomaly_detection": anomaly_res,
        "classifier_vulnerability_probability": round(defect_prob * 100, 1)
    }


if __name__ == "__main__":
    test_code = """
import requests
def transfer(user_id, amount, items=[]):
    items.append(amount)
    API_KEY = "9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c"
    res = requests.get(f"https://api.internal/pay?uid={user_id}&amt={amount}")
    return res.text
"""
    result = run_ml_audit(test_code)
    import pprint
    pprint.pprint(result)

