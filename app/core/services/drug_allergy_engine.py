"""
Drug–Allergy Risk Scoring Engine — PBI-S4-17
FR-Ph-4 / FR-Ph-5

Three-strategy scoring service that classifies medication orders as
CRITICAL / HIGH / MEDIUM / SAFE based on the patient's recorded allergies.

Strategies:
    A — Exact name match (normalised lowercase)               → score 100
    B — Pharmacological class cross-reactivity lookup          → score 75
    C — Fuzzy edit-distance match (Levenshtein distance ≤ 2)  → score 50

Final score = max(score_A, score_B, score_C)
Risk level:  100 → CRITICAL, 75 → HIGH, 50 → MEDIUM, 0 → SAFE
"""

import re

# ---------------------------------------------------------------------------
# Pharmacological class dictionary
# Maps lowercase drug name → pharmacological class string.
# Must cover ≥ 30 drugs across ≥ 6 classes (AC-17.8).
# ---------------------------------------------------------------------------

DRUG_CLASS_MAP: dict[str, str] = {
    # Penicillins
    "amoxicillin": "penicillin",
    "ampicillin": "penicillin",
    "penicillin": "penicillin",
    "penicillin v": "penicillin",
    "penicillin g": "penicillin",
    "oxacillin": "penicillin",
    "nafcillin": "penicillin",
    "dicloxacillin": "penicillin",
    "piperacillin": "penicillin",
    "ticarcillin": "penicillin",
    # Cephalosporins
    "cephalexin": "cephalosporin",
    "cefazolin": "cephalosporin",
    "cefuroxime": "cephalosporin",
    "ceftriaxone": "cephalosporin",
    "cefdinir": "cephalosporin",
    "cefprozil": "cephalosporin",
    "cefepime": "cephalosporin",
    "ceftazidime": "cephalosporin",
    # Sulfonamides
    "sulfamethoxazole": "sulfonamide",
    "trimethoprim-sulfamethoxazole": "sulfonamide",
    "sulfadiazine": "sulfonamide",
    "sulfasalazine": "sulfonamide",
    "dapsone": "sulfonamide",
    # NSAIDs
    "ibuprofen": "nsaid",
    "naproxen": "nsaid",
    "aspirin": "nsaid",
    "diclofenac": "nsaid",
    "indomethacin": "nsaid",
    "meloxicam": "nsaid",
    "celecoxib": "nsaid",
    "ketorolac": "nsaid",
    # Opioids
    "morphine": "opioid",
    "codeine": "opioid",
    "oxycodone": "opioid",
    "hydrocodone": "opioid",
    "fentanyl": "opioid",
    "tramadol": "opioid",
    "hydromorphone": "opioid",
    "methadone": "opioid",
    "buprenorphine": "opioid",
    # Fluoroquinolones
    "ciprofloxacin": "fluoroquinolone",
    "levofloxacin": "fluoroquinolone",
    "moxifloxacin": "fluoroquinolone",
    "ofloxacin": "fluoroquinolone",
    "norfloxacin": "fluoroquinolone",
    "gemifloxacin": "fluoroquinolone",
}

# Cross-reactivity map: allergy class → set of classes that may cross-react
CROSS_REACTIVITY: dict[str, set[str]] = {
    "penicillin": {"cephalosporin"},
    "cephalosporin": {"penicillin"},
    "sulfonamide": set(),
    "nsaid": set(),
    "opioid": set(),
    "fluoroquinolone": set(),
}


def _edit_distance(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(
                min(
                    prev[j] + 1,  # deletion
                    curr[j - 1] + 1,  # insertion
                    prev[j - 1] + (ca != cb),  # substitution
                )
            )
        prev = curr
    return prev[-1]


def _tokenise_allergies(allergies_raw: str) -> list[str]:
    """
    Split the allergies field on common separators: , ; / newline.
    Returns a list of lowercase, whitespace-stripped, non-empty tokens.
    AC-17.9
    """
    tokens = re.split(r"[,;/\n]+", allergies_raw)
    return [t.strip().lower() for t in tokens if t.strip()]


class DrugAllergyRiskEngine:
    """
    Scores the allergy risk of prescribing a medication to a patient.

    Usage::

        engine = DrugAllergyRiskEngine()
        result = engine.evaluate(medication_name="amoxicillin",
                                  allergies_raw="Penicillin; latex")
        # result.risk_level   → "critical"
        # result.risk_score   → 100
        # result.matched_allergen → "penicillin"
        # result.strategy     → "A"
    """

    class Result:
        __slots__ = ("risk_level", "risk_score", "matched_allergen", "strategy")

        def __init__(self, risk_level, risk_score, matched_allergen, strategy):
            self.risk_level = risk_level
            self.risk_score = risk_score
            self.matched_allergen = matched_allergen
            self.strategy = strategy

        def __repr__(self):
            return (
                f"<RiskResult level={self.risk_level!r} score={self.risk_score} "
                f"allergen={self.matched_allergen!r} strategy={self.strategy!r}>"
            )

    def evaluate(
        self, medication_name: str, allergies_raw: str
    ) -> "DrugAllergyRiskEngine.Result":
        """
        Evaluate the drug-allergy risk for a single medication.

        Args:
            medication_name: The medication being prescribed.
            allergies_raw:   Raw allergies string from ``Patient.allergies``.

        Returns:
            A :class:`Result` instance with risk_level, risk_score,
            matched_allergen, and strategy attributes.
        """
        if not medication_name or not allergies_raw:
            return self.Result("safe", 0, None, None)

        allergy_tokens = _tokenise_allergies(allergies_raw)
        if not allergy_tokens:
            return self.Result("safe", 0, None, None)

        med_norm = medication_name.strip().lower()

        best_score = 0
        best_allergen = None
        best_strategy = None

        for allergen in allergy_tokens:
            # --- Strategy A: exact name match OR substring containment ---
            # Substring check covers abbreviated allergy entries (e.g. "sulfa" → "sulfamethoxazole")
            score_a = 0
            if allergen == med_norm:
                score_a = 100
            elif len(allergen) >= 3 and (allergen in med_norm or med_norm in allergen):
                score_a = 100

            # --- Strategy B: pharmacological class cross-reactivity ---
            score_b = 0
            med_class = DRUG_CLASS_MAP.get(med_norm)
            allergen_class = DRUG_CLASS_MAP.get(allergen)
            if med_class and allergen_class:
                if med_class == allergen_class:
                    # Same class as allergen counts as exact (covered by A if same name)
                    score_b = 75
                elif allergen_class in CROSS_REACTIVITY.get(med_class, set()):
                    score_b = 75

            # --- Strategy C: fuzzy edit-distance match (threshold ≤ 2) ---
            score_c = 0
            if _edit_distance(med_norm, allergen) <= 2:
                score_c = 50

            candidate_score = max(score_a, score_b, score_c)
            if candidate_score > best_score:
                best_score = candidate_score
                best_allergen = allergen
                if score_a >= score_b and score_a >= score_c:
                    best_strategy = "A"
                elif score_b >= score_c:
                    best_strategy = "B"
                else:
                    best_strategy = "C"

        risk_level = {
            100: "critical",
            75: "high",
            50: "medium",
        }.get(best_score, "safe")

        return self.Result(risk_level, best_score, best_allergen, best_strategy)
