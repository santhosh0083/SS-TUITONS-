"""Seed the Grade 11 and 12 syllabus for Physics, Chemistry and Mathematics.

Covers two boards, kept separate because they genuinely differ:

  * CBSE            — NCERT Class 11 and 12
  * TSBIE           — Telangana Intermediate, 1st and 2nd year

and two entrance exams that follow them:

  * JEE Main        — tracks the CBSE/NCERT syllabus
  * TG EAPCET       — tracks the TSBIE syllabus

Chapters are stored per (subject, exam, grade), so the same chapter appears
once per exam it belongs to. EAPCET chapters are cloned from TSBIE and JEE Main
from CBSE, since those exams are drawn from those syllabi. Cloning is done in
code rather than by duplicating the lists, so a correction is made in one place.

Run after `alembic upgrade head`:

    ./.venv/Scripts/python -m scripts.seed_curriculum

Safe to re-run: existing chapters are left untouched.
"""

import asyncio
import sys

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.academics import Exam, Subject
from app.models.content import Chapter
from app.models.enums import Grade

# ---------------------------------------------------------------------------
# CBSE / NCERT
# ---------------------------------------------------------------------------

CBSE_11_PHYSICS = [
    "Units and Measurements",
    "Motion in a Straight Line",
    "Motion in a Plane",
    "Laws of Motion",
    "Work, Energy and Power",
    "System of Particles and Rotational Motion",
    "Gravitation",
    "Mechanical Properties of Solids",
    "Mechanical Properties of Fluids",
    "Thermal Properties of Matter",
    "Thermodynamics",
    "Kinetic Theory",
    "Oscillations",
    "Waves",
]

CBSE_12_PHYSICS = [
    "Electric Charges and Fields",
    "Electrostatic Potential and Capacitance",
    "Current Electricity",
    "Moving Charges and Magnetism",
    "Magnetism and Matter",
    "Electromagnetic Induction",
    "Alternating Current",
    "Electromagnetic Waves",
    "Ray Optics and Optical Instruments",
    "Wave Optics",
    "Dual Nature of Radiation and Matter",
    "Atoms",
    "Nuclei",
    "Semiconductor Electronics",
]

CBSE_11_CHEMISTRY = [
    "Some Basic Concepts of Chemistry",
    "Structure of Atom",
    "Classification of Elements and Periodicity in Properties",
    "Chemical Bonding and Molecular Structure",
    "Thermodynamics",
    "Equilibrium",
    "Redox Reactions",
    "Organic Chemistry: Some Basic Principles and Techniques",
    "Hydrocarbons",
]

CBSE_12_CHEMISTRY = [
    "Solutions",
    "Electrochemistry",
    "Chemical Kinetics",
    "The d- and f-Block Elements",
    "Coordination Compounds",
    "Haloalkanes and Haloarenes",
    "Alcohols, Phenols and Ethers",
    "Aldehydes, Ketones and Carboxylic Acids",
    "Amines",
    "Biomolecules",
]

CBSE_11_MATHS = [
    "Sets",
    "Relations and Functions",
    "Trigonometric Functions",
    "Complex Numbers and Quadratic Equations",
    "Linear Inequalities",
    "Permutations and Combinations",
    "Binomial Theorem",
    "Sequences and Series",
    "Straight Lines",
    "Conic Sections",
    "Introduction to Three Dimensional Geometry",
    "Limits and Derivatives",
    "Statistics",
    "Probability",
]

CBSE_12_MATHS = [
    "Relations and Functions",
    "Inverse Trigonometric Functions",
    "Matrices",
    "Determinants",
    "Continuity and Differentiability",
    "Application of Derivatives",
    "Integrals",
    "Application of Integrals",
    "Differential Equations",
    "Vector Algebra",
    "Three Dimensional Geometry",
    "Linear Programming",
    "Probability",
]

# ---------------------------------------------------------------------------
# TSBIE — Telangana Intermediate
# ---------------------------------------------------------------------------

TSBIE_11_PHYSICS = [
    "Physical World",
    "Units and Measurements",
    "Motion in a Straight Line",
    "Motion in a Plane",
    "Laws of Motion",
    "Work, Energy and Power",
    "Systems of Particles and Rotational Motion",
    "Oscillations",
    "Gravitation",
    "Mechanical Properties of Solids",
    "Mechanical Properties of Fluids",
    "Thermal Properties of Matter",
    "Thermodynamics",
    "Kinetic Theory",
]

TSBIE_12_PHYSICS = [
    "Waves",
    "Ray Optics and Optical Instruments",
    "Wave Optics",
    "Electric Charges and Fields",
    "Electrostatic Potential and Capacitance",
    "Current Electricity",
    "Moving Charges and Magnetism",
    "Magnetism and Matter",
    "Electromagnetic Induction",
    "Alternating Current",
    "Electromagnetic Waves",
    "Dual Nature of Radiation and Matter",
    "Atoms",
    "Nuclei",
    "Semiconductor Electronics",
    "Communication Systems",
]

TSBIE_11_CHEMISTRY = [
    "Atomic Structure",
    "Classification of Elements and Periodicity in Properties",
    "Chemical Bonding and Molecular Structure",
    "States of Matter: Gases and Liquids",
    "Stoichiometry",
    "Thermodynamics",
    "Chemical Equilibrium and Acids-Bases",
    "Hydrogen and its Compounds",
    "The s-Block Elements",
    "The p-Block Elements: Group 13 and 14",
    "Environmental Chemistry",
    "Organic Chemistry: Some Basic Principles and Techniques",
]

TSBIE_12_CHEMISTRY = [
    "Solid State",
    "Solutions",
    "Electrochemistry and Chemical Kinetics",
    "Surface Chemistry",
    "General Principles of Metallurgy",
    "The p-Block Elements: Group 15 to 18",
    "The d- and f-Block Elements",
    "Coordination Compounds",
    "Polymers",
    "Biomolecules",
    "Chemistry in Everyday Life",
    "Haloalkanes and Haloarenes",
    "Organic Compounds Containing C, H and O",
    "Organic Compounds Containing Nitrogen",
]

# Telangana splits Maths into IA/IB in the first year and IIA/IIB in the second.
TSBIE_11_MATHS = [
    "Functions (IA)",
    "Mathematical Induction (IA)",
    "Matrices (IA)",
    "Addition of Vectors (IA)",
    "Product of Vectors (IA)",
    "Trigonometric Ratios up to Transformations (IA)",
    "Trigonometric Equations (IA)",
    "Inverse Trigonometric Functions (IA)",
    "Hyperbolic Functions (IA)",
    "Properties of Triangles (IA)",
    "Locus (IB)",
    "Transformation of Axes (IB)",
    "The Straight Line (IB)",
    "Pair of Straight Lines (IB)",
    "Three Dimensional Coordinates (IB)",
    "Direction Cosines and Direction Ratios (IB)",
    "The Plane (IB)",
    "Limits and Continuity (IB)",
    "Differentiation (IB)",
    "Applications of Derivatives (IB)",
]

TSBIE_12_MATHS = [
    "Complex Numbers (IIA)",
    "De Moivre's Theorem (IIA)",
    "Quadratic Expressions (IIA)",
    "Theory of Equations (IIA)",
    "Permutations and Combinations (IIA)",
    "Binomial Theorem (IIA)",
    "Partial Fractions (IIA)",
    "Measures of Dispersion (IIA)",
    "Probability (IIA)",
    "Random Variables and Probability Distributions (IIA)",
    "Circle (IIB)",
    "System of Circles (IIB)",
    "Parabola (IIB)",
    "Ellipse (IIB)",
    "Hyperbola (IIB)",
    "Integration (IIB)",
    "Definite Integrals (IIB)",
    "Differential Equations (IIB)",
]

# subject_code -> {grade -> chapter list}
CBSE_SYLLABUS = {
    "PHY": {Grade.GRADE_11: CBSE_11_PHYSICS, Grade.GRADE_12: CBSE_12_PHYSICS},
    "CHEM": {Grade.GRADE_11: CBSE_11_CHEMISTRY, Grade.GRADE_12: CBSE_12_CHEMISTRY},
    "MATH": {Grade.GRADE_11: CBSE_11_MATHS, Grade.GRADE_12: CBSE_12_MATHS},
}

TSBIE_SYLLABUS = {
    "PHY": {Grade.GRADE_11: TSBIE_11_PHYSICS, Grade.GRADE_12: TSBIE_12_PHYSICS},
    "CHEM": {Grade.GRADE_11: TSBIE_11_CHEMISTRY, Grade.GRADE_12: TSBIE_12_CHEMISTRY},
    "MATH": {Grade.GRADE_11: TSBIE_11_MATHS, Grade.GRADE_12: TSBIE_12_MATHS},
}

# exam code -> the syllabus that exam is drawn from
EXAM_SYLLABUS = {
    "CBSE": CBSE_SYLLABUS,      # CBSE board exam
    "JEE_MAIN": CBSE_SYLLABUS,  # follows NCERT
    "IPE": TSBIE_SYLLABUS,      # Telangana Intermediate board exam
    "EAMCET": TSBIE_SYLLABUS,   # TG EAPCET follows the Intermediate syllabus
}


async def seed() -> int:
    created = 0
    skipped = 0

    async with SessionLocal() as session:
        # CBSE is a board exam in its own right and was not in the original seed.
        cbse = (
            await session.execute(select(Exam).where(Exam.code == "CBSE"))
        ).scalar_one_or_none()
        if cbse is None:
            session.add(
                Exam(
                    code="CBSE",
                    name="CBSE Board Examination",
                    description="Central Board of Secondary Education, Class 12",
                    is_active=True,
                )
            )
            await session.flush()
            print("  + exam CBSE")

        exams = {
            e.code: e for e in (await session.execute(select(Exam))).scalars().all()
        }
        subjects = {
            s.code: s for s in (await session.execute(select(Subject))).scalars().all()
        }

        existing = {
            (c.subject_id, c.exam_id, c.grade, c.name)
            for c in (await session.execute(select(Chapter))).scalars().all()
        }

        for exam_code, syllabus in EXAM_SYLLABUS.items():
            exam = exams.get(exam_code)
            if exam is None:
                print(f"  ! exam {exam_code} not found, skipping")
                continue

            for subject_code, by_grade in syllabus.items():
                subject = subjects.get(subject_code)
                if subject is None:
                    print(f"  ! subject {subject_code} not found, skipping")
                    continue

                for grade, chapters in by_grade.items():
                    for index, name in enumerate(chapters, start=1):
                        key = (subject.id, exam.id, grade, name)
                        if key in existing:
                            skipped += 1
                            continue
                        session.add(
                            Chapter(
                                subject_id=subject.id,
                                exam_id=exam.id,
                                grade=grade,
                                name=name,
                                sequence=index,
                            )
                        )
                        existing.add(key)
                        created += 1

        await session.commit()

    print(f"\n  chapters created : {created}")
    print(f"  already present  : {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(seed()))
