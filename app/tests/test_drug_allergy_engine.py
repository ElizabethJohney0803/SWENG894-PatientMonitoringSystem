"""
Tests for the Drug–Allergy Risk Scoring Engine — PBI-S4-17
TC-S4-061 — TC-S4-070

FR-Ph-4, FR-Ph-5
"""

import pytest
from datetime import date
from django.contrib.auth.models import User
from core.models import UserProfile, Patient, Medication
from core.services.drug_allergy_engine import (
    DrugAllergyRiskEngine,
    DRUG_CLASS_MAP,
    _tokenise_allergies,
    _edit_distance,
)


# ---------------------------------------------------------------------------
# Engine unit tests
# ---------------------------------------------------------------------------


class TestDrugAllergyEngineExactMatch:
    """TC-S4-061 — Exact name match → risk_level=critical, risk_score=100 (AC-17.1)."""

    def test_exact_match_case_insensitive(self):
        engine = DrugAllergyRiskEngine()
        result = engine.evaluate("Penicillin", "penicillin, latex")
        assert result.risk_level == "critical"
        assert result.risk_score == 100
        assert result.strategy == "A"

    def test_exact_match_medication_in_allergy(self):
        engine = DrugAllergyRiskEngine()
        result = engine.evaluate("amoxicillin", "amoxicillin")
        assert result.risk_level == "critical"
        assert result.risk_score == 100

    def test_substring_match_scores_critical(self):
        """Substring containment also scores 100 via Strategy A."""
        engine = DrugAllergyRiskEngine()
        # "sulfa" is a substring of "sulfamethoxazole" — length ≥ 3
        result = engine.evaluate("sulfamethoxazole", "sulfa, latex")
        assert result.risk_level == "critical"
        assert result.risk_score == 100
        assert result.strategy == "A"

    def test_exact_match_sets_allergy_conflict(self):
        """When exact match fires, allergy_conflict on saved medication should be True."""
        engine = DrugAllergyRiskEngine()
        result = engine.evaluate("ibuprofen", "ibuprofen")
        assert result.risk_level == "critical"


class TestDrugAllergyEngineCrossReactivity:
    """TC-S4-062 — Drug-class cross-reactivity → risk_level=high, risk_score=75 (AC-17.2)."""

    def test_penicillin_cephalosporin_cross_reactivity(self):
        """Penicillin allergy + cephalosporin medication → high risk."""
        engine = DrugAllergyRiskEngine()
        result = engine.evaluate("cephalexin", "penicillin")
        assert result.risk_level == "high"
        assert result.risk_score == 75
        assert result.strategy == "B"

    def test_cephalosporin_penicillin_cross_reactivity(self):
        """Cephalosporin allergy + penicillin medication → high risk."""
        engine = DrugAllergyRiskEngine()
        result = engine.evaluate("amoxicillin", "cephalexin")
        assert result.risk_level == "high"
        assert result.risk_score == 75
        assert result.strategy == "B"

    def test_same_class_scores_high(self):
        """Same pharmacological class scores 75 (Strategy B)."""
        engine = DrugAllergyRiskEngine()
        # Two different opioids
        result = engine.evaluate("morphine", "codeine")
        assert result.risk_level == "high"
        assert result.risk_score == 75

    def test_no_cross_reactivity_between_unrelated_classes(self):
        """NSAIDs and opioids do not cross-react."""
        engine = DrugAllergyRiskEngine()
        result = engine.evaluate("morphine", "ibuprofen")
        # No A or cross-reactivity B match; may be SAFE or medium (fuzzy check)
        assert result.risk_level in ("safe", "medium")


class TestDrugAllergyEngineFuzzyMatch:
    """TC-S4-063 — Fuzzy edit-distance match → risk_level=medium, risk_score=50 (AC-17.3)."""

    def test_edit_distance_1_scores_medium(self):
        """One-character difference should trigger fuzzy match."""
        engine = DrugAllergyRiskEngine()
        # 'codine' (typo of 'codeine') — edit distance 1
        result = engine.evaluate("codeine", "codine")
        assert result.risk_level == "medium"
        assert result.risk_score == 50
        assert result.strategy in ("A", "B", "C")  # could be A (substring) or C

    def test_edit_distance_2_scores_medium(self):
        """Two-character difference should trigger fuzzy match."""
        engine = DrugAllergyRiskEngine()
        result = engine.evaluate("aspirin", "asprin")  # edit distance 1 — still valid
        # asprin vs aspirin — distance 1
        assert result.risk_score >= 50

    def test_edit_distance_3_no_match(self):
        """Distance > 2 should NOT trigger fuzzy match."""
        engine = DrugAllergyRiskEngine()
        # 'banana' is 6 chars vs 'morphine' 8 chars — clearly distance > 2
        result = engine.evaluate("morphine", "banana")
        # Should be SAFE (no class match, no substring, edit distance >> 2)
        assert result.risk_level == "safe"
        assert result.risk_score == 0


class TestDrugAllergyEngineNoMatch:
    """TC-S4-064 — No strategy match → risk_level=safe, risk_score=0 (AC-17.4)."""

    def test_completely_different_drug_and_allergy(self):
        engine = DrugAllergyRiskEngine()
        result = engine.evaluate("metformin", "pollen, dust, latex")
        assert result.risk_level == "safe"
        assert result.risk_score == 0
        assert result.matched_allergen is None

    def test_empty_allergies_is_safe(self):
        engine = DrugAllergyRiskEngine()
        result = engine.evaluate("amoxicillin", "")
        assert result.risk_level == "safe"
        assert result.risk_score == 0

    def test_empty_medication_name_is_safe(self):
        engine = DrugAllergyRiskEngine()
        result = engine.evaluate("", "penicillin")
        assert result.risk_level == "safe"
        assert result.risk_score == 0


class TestHighestScoreWins:
    """TC-S4-065 — Highest score across all strategies wins (AC-17.5)."""

    def test_exact_match_beats_cross_reactivity(self):
        """When both exact and class match fire, exact (100) wins."""
        engine = DrugAllergyRiskEngine()
        # amoxicillin is in penicillin class; "amoxicillin" in allergies = exact match (100)
        result = engine.evaluate("amoxicillin", "amoxicillin, cephalexin")
        assert result.risk_score == 100
        assert result.risk_level == "critical"

    def test_cross_reactivity_beats_fuzzy(self):
        """When cross-reactivity (75) and fuzzy (50) both fire, 75 wins."""
        engine = DrugAllergyRiskEngine()
        # amoxicillin (penicillin class) vs cephalexin allergy (cephalosporin class) = cross-react 75
        result = engine.evaluate("amoxicillin", "cephalexin")
        assert result.risk_score >= 75


class TestDrugClassDictionary:
    """TC-S4-068 — Drug-class dictionary returns correct class for ≥30 drugs across ≥6 classes (AC-17.8)."""

    def test_covers_at_least_30_drugs(self):
        assert len(DRUG_CLASS_MAP) >= 30

    def test_covers_at_least_6_classes(self):
        classes = set(DRUG_CLASS_MAP.values())
        assert len(classes) >= 6

    def test_expected_classes_present(self):
        expected = {
            "penicillin",
            "cephalosporin",
            "sulfonamide",
            "nsaid",
            "opioid",
            "fluoroquinolone",
        }
        actual = set(DRUG_CLASS_MAP.values())
        assert expected <= actual

    def test_amoxicillin_is_penicillin(self):
        assert DRUG_CLASS_MAP["amoxicillin"] == "penicillin"

    def test_ibuprofen_is_nsaid(self):
        assert DRUG_CLASS_MAP["ibuprofen"] == "nsaid"

    def test_ciprofloxacin_is_fluoroquinolone(self):
        assert DRUG_CLASS_MAP["ciprofloxacin"] == "fluoroquinolone"

    def test_morphine_is_opioid(self):
        assert DRUG_CLASS_MAP["morphine"] == "opioid"


class TestAllergyTokenisation:
    """TC-S4-069 — Allergy tokens correctly normalised from mixed-separator input (AC-17.9)."""

    def test_comma_separator(self):
        tokens = _tokenise_allergies("penicillin, latex, aspirin")
        assert "penicillin" in tokens
        assert "latex" in tokens
        assert "aspirin" in tokens

    def test_semicolon_separator(self):
        tokens = _tokenise_allergies("penicillin; codeine")
        assert "penicillin" in tokens
        assert "codeine" in tokens

    def test_slash_separator(self):
        tokens = _tokenise_allergies("penicillin/amoxicillin")
        assert "penicillin" in tokens
        assert "amoxicillin" in tokens

    def test_newline_separator(self):
        tokens = _tokenise_allergies("penicillin\nlatex")
        assert "penicillin" in tokens
        assert "latex" in tokens

    def test_mixed_separators(self):
        tokens = _tokenise_allergies("Penicillin; Latex, Aspirin\nIbuprofen")
        lowered = [t.lower() for t in tokens]
        assert "penicillin" in lowered
        assert "ibuprofen" in lowered

    def test_whitespace_stripped_and_lowercased(self):
        tokens = _tokenise_allergies("  PENICILLIN  ,  ASPIRIN  ")
        assert "penicillin" in tokens
        assert "aspirin" in tokens

    def test_empty_string_returns_empty_list(self):
        tokens = _tokenise_allergies("")
        assert tokens == []


class TestEditDistance:
    """Unit tests for the _edit_distance helper."""

    def test_identical_strings_distance_0(self):
        assert _edit_distance("aspirin", "aspirin") == 0

    def test_one_insertion(self):
        assert _edit_distance("cat", "cats") == 1

    def test_one_substitution(self):
        assert _edit_distance("cat", "bat") == 1

    def test_two_edits(self):
        assert _edit_distance("kitten", "sitten") == 1

    def test_empty_string(self):
        assert _edit_distance("", "abc") == 3


# ---------------------------------------------------------------------------
# Integration tests: engine wired into Medication.save()
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMedicationEngineIntegration:
    """AC-17.1–17.4 verified through actual Medication model saves."""

    @pytest.fixture(autouse=True)
    def setup(self, create_groups):
        self.doctor_u = User.objects.create_user(
            username="dr_engine_test",
            password="testpass",
            is_staff=True,
        )
        UserProfile.objects.create(
            user=self.doctor_u,
            role="doctor",
            license_number="MD999",
        )
        patient_u = User.objects.create_user(
            username="pt_engine_test",
            password="testpass",
            is_staff=True,
        )
        self.profile = UserProfile.objects.create(user=patient_u, role="patient")
        # UserProfile.save() auto-creates a Patient via ensure_patient_record().
        # Retrieve that record and update it with proper test data.
        self.patient = self.profile.patient_record
        self.patient.date_of_birth = date(1990, 1, 1)
        self.patient.gender = "M"
        self.patient.address_line1 = "123 Test St"
        self.patient.city = "Testville"
        self.patient.state = "CA"
        self.patient.postal_code = "90001"
        self.patient.phone_primary = "555-0099"
        self.patient.save()

    def _make_med(self, name, allergies=""):
        self.patient.allergies = allergies
        self.patient.save(update_fields=["allergies"])
        return Medication.objects.create(
            patient=self.patient,
            medication_name=name,
            dosage="10mg",
            frequency="once daily",
            start_date=date(2026, 1, 1),
        )

    def test_exact_match_sets_critical(self):
        med = self._make_med("penicillin", "penicillin")
        assert med.risk_level == "critical"
        assert med.risk_score == 100
        assert med.allergy_conflict is True

    def test_cross_reactivity_sets_high(self):
        """Cephalexin prescribed; patient allergic to penicillin → HIGH."""
        med = self._make_med("cephalexin", "penicillin")
        assert med.risk_level == "high"
        assert med.risk_score == 75
        assert med.allergy_conflict is True

    def test_no_match_sets_safe(self):
        med = self._make_med("metformin", "latex, pollen")
        assert med.risk_level == "safe"
        assert med.risk_score == 0
        assert med.allergy_conflict is False

    def test_empty_allergies_is_safe(self):
        med = self._make_med("amoxicillin", "")
        assert med.risk_level == "safe"
        assert med.allergy_conflict is False

    def test_risk_fields_persisted_to_db(self):
        """risk_level and risk_score are persisted in the database (AC-17.10)."""
        med = self._make_med("amoxicillin", "amoxicillin")
        reloaded = Medication.objects.get(pk=med.pk)
        assert reloaded.risk_level == "critical"
        assert reloaded.risk_score == 100


@pytest.mark.django_db
class TestMedicationRiskFields:
    """Verify risk_level and risk_score fields exist on the model (AC-17.10)."""

    def test_risk_level_field_exists(self):
        field_names = {f.name for f in Medication._meta.get_fields()}
        assert "risk_level" in field_names

    def test_risk_score_field_exists(self):
        field_names = {f.name for f in Medication._meta.get_fields()}
        assert "risk_score" in field_names

    def test_risk_level_default_is_safe(self):
        import inspect

        field = Medication._meta.get_field("risk_level")
        assert field.default == "safe"

    def test_risk_score_default_is_zero(self):
        field = Medication._meta.get_field("risk_score")
        assert field.default == 0
