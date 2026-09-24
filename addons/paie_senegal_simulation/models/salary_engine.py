# -*- coding: utf-8 -*-
"""Moteur autonome de calcul de salaire net."""

from math import floor


TRANSPORT_AMOUNT = 26000.0

# IPRES : paramètres correspondant aux bulletins fournis.
IPRES_RG_RATE = 0.056
IPRES_RG_CEILING = 432000.0
IPRES_RC_RATE = 0.024

# TRIMF : barème annuel par personne imposable.
TRIMF_TARIFFS = (
    (599999.0, 900.0),
    (999999.0, 3600.0),
    (1999999.0, 4800.0),
    (6999999.0, 12000.0),
    (11999999.0, 18000.0),
    (float('inf'), 36000.0),
)

# Formule IR fournie par le demandeur.
IR_TRANCHES = (
    (630001, 1500000, 630001, 0.20, 0),
    (1500000, 4000000, 1500000, 0.30, 174000),
    (4000001, 8000000, 4000001, 0.35, 750000 + 174000),
    (8000001, 13500000, 8000000, 0.37, 1400000 + 750000 + 174000),
    (13500001, 50000000, 13500001, 0.40, 2035000 + 1400000 + 750000 + 174000),
    (50000001, 10**12, 50000001, 0.43, 14600000 + 2035000 + 1400000 + 750000 + 174000),
)

IR_REDUCTIONS = {
    1.5: (0.10, 100000, 300000),
    2.0: (0.15, 200000, 650000),
    2.5: (0.20, 300000, 1100000),
    3.0: (0.25, 400000, 1650000),
    3.5: (0.30, 500000, 2030000),
    4.0: (0.35, 600000, 2490000),
    4.5: (0.40, 700000, 2755000),
    5.0: (0.45, 800000, 3180000),
}


def normalize_part(value):
    value = max(float(value or 1.0), 1.0)
    return round(value * 2.0) / 2.0


def compute_family_parts(marital, children_count, spouse_has_income):
    """Calcule les parts IR et les personnes TRIMF utilisées par le simulateur."""
    children_count = max(int(children_count or 0), 0)
    spouse_has_income = bool(spouse_has_income)

    part_ir = 1.0

    if marital == 'married':
        part_ir += 0.5
        if not spouse_has_income:
            part_ir += 0.5

    part_ir += children_count * 0.5
    part_ir = min(normalize_part(part_ir), 5.0)

    trimf_persons = 1.0
    if marital == 'married' and not spouse_has_income:
        trimf_persons += 1.0

    return part_ir, trimf_persons


def compute_ir(gross, part_ir):
    """Applique exactement la formule IR fournie."""
    gross = max(float(gross or 0.0), 0.0)

    brut = floor(gross / 1000.0) * 1000.0
    annual_gross = brut * 12.0
    abatement = min(0.3 * annual_gross, 900000.0)
    annual_gross_fiscal = annual_gross - abatement

    irrp_before_reduction = 0.0

    for min_c, max_c, base, rate, add in IR_TRANCHES:
        if min_c <= annual_gross_fiscal <= max_c:
            irrp_before_reduction = (
                (annual_gross_fiscal - base) * rate
            ) + add
            break

    part_ir = normalize_part(part_ir)
    irrp_reduction = 0.0

    if part_ir in IR_REDUCTIONS:
        rate_pct, min_red, max_red = IR_REDUCTIONS[part_ir]
        calc = rate_pct * irrp_before_reduction

        if calc < min_red:
            irrp_reduction = float(min_red)
        elif calc > max_red:
            irrp_reduction = float(max_red)
        else:
            irrp_reduction = calc

    return max((irrp_before_reduction - irrp_reduction) / 12.0, 0.0)


def compute_trimf(gross, trimf_persons):
    """Calcule la TRIMF mensuelle selon le brut annuel et les personnes imposables."""
    gross = max(float(gross or 0.0), 0.0)
    persons = max(float(trimf_persons or 1.0), 1.0)
    annual_gross = gross * 12.0

    for ceiling, annual_amount_per_person in TRIMF_TARIFFS:
        if annual_gross <= ceiling:
            return round((annual_amount_per_person * persons) / 12.0)

    return 0.0


def compute_ipres(gross, status):
    """Calcule IPRES RG et, pour un cadre, IPRES RC."""
    gross = max(float(gross or 0.0), 0.0)

    rg_base = min(gross, IPRES_RG_CEILING)
    ipres_rg = round(rg_base * IPRES_RG_RATE)
    ipres_rc = round(gross * IPRES_RC_RATE) if status == 'cadre' else 0.0

    return ipres_rg, ipres_rc


def compute_salary(gross, part_ir, trimf_persons, status):
    """Retourne les éléments de salaire demandés."""
    gross = max(float(gross or 0.0), 0.0)

    ir = round(compute_ir(gross, part_ir))
    trimf = compute_trimf(gross, trimf_persons)
    ipres_rg, ipres_rc = compute_ipres(gross, status)

    net_salary = round(
        gross - ir - trimf - ipres_rg - ipres_rc
    )

    return {
        'gross': round(gross),
        'ir': ir,
        'trimf': trimf,
        'ipres_rg': ipres_rg,
        'ipres_rc': ipres_rc,
        'transport': TRANSPORT_AMOUNT,
        'net_salary': net_salary,
        'net_to_pay': net_salary + TRANSPORT_AMOUNT,
    }


def solve_gross_for_net(target_net, base_salary, part_ir, trimf_persons, status):
    """
    Recherche le brut correspondant au salaire net souhaité.
    Le net cible est hors transport ; le transport de 26 000 FCFA
    est ajouté séparément au net à payer.
    """
    target_net = max(float(target_net or 0.0), 0.0)
    base_salary = max(float(base_salary or 0.0), 0.0)

    lower = base_salary
    high = max(base_salary, target_net, 100000.0)

    for _ in range(30):
        high_result = compute_salary(
            high,
            part_ir,
            trimf_persons,
            status,
        )

        if high_result['net_salary'] >= target_net:
            break

        high *= 2.0

    for _ in range(100):
        if high - lower <= 1.0:
            break

        middle = floor((lower + high) / 2.0)
        middle_result = compute_salary(
            middle,
            part_ir,
            trimf_persons,
            status,
        )

        if middle_result['net_salary'] < target_net:
            lower = middle + 1.0
        else:
            high = middle

    center = int(round(high))
    candidates = range(
        max(int(base_salary), center - 5000),
        center + 5001,
    )

    best = None

    for gross in candidates:
        result = compute_salary(
            gross,
            part_ir,
            trimf_persons,
            status,
        )
        difference = abs(result['net_salary'] - target_net)
        key = (difference, gross)

        if best is None or key < best[0]:
            best = (key, result)

    return best[1]
