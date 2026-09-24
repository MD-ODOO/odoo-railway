# -*- coding: utf-8 -*-
"""Moteur de calcul de la simulation de salaire net."""

from math import floor

TRANSPORT_AMOUNT = 26000.0

# Paramètres utilisés dans les bulletins GAINDE fournis.
IPRES_RG_RATE = 0.056
IPRES_RG_CEILING = 432000.0
IPRES_RC_RATE = 0.024

# TRIMF : montants mensuels par personne imposable, paramétrables plus tard
# selon la grille retenue par l'entreprise.
TRIMF_MONTHLY_TARIFFS = (
    (350000.0, 1000.0),
    (599999.0, 1500.0),
    (999999.0, 2000.0),
    (1199999.0, 2500.0),
    (float('inf'), 3000.0),
)

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
    """Calcule les parts utilisées par le simulateur à partir des informations saisies."""
    children_count = max(int(children_count or 0), 0)
    spouse_has_income = bool(spouse_has_income)

    part_ir = 1.0
    if marital == 'married':
        part_ir += 0.5
        if not spouse_has_income:
            part_ir += 0.5
    part_ir += 0.5 * children_count
    part_ir = min(normalize_part(part_ir), 5.0)

    trimf_persons = 1.0
    if marital == 'married' and not spouse_has_income:
        trimf_persons += 1.0

    return part_ir, trimf_persons


def compute_ir(gross, part_ir):
    """Formule IR fournie par l'utilisateur."""
    gross = max(float(gross or 0.0), 0.0)
    brut = floor(gross / 1000.0) * 1000.0

    annual_gross = brut * 12.0
    abatement = min(0.3 * annual_gross, 900000.0)
    annual_gross_fiscal = annual_gross - abatement

    irrp_before_reduction = 0.0
    for min_c, max_c, base, rate, add in IR_TRANCHES:
        if annual_gross_fiscal >= min_c and annual_gross_fiscal <= max_c:
            irrp_before_reduction = (annual_gross_fiscal - base) * rate + add
            break

    part_ir = normalize_part(part_ir)
    irrp_reduction = 0.0

    if part_ir in IR_REDUCTIONS:
        rate_pct, min_red, max_red = IR_REDUCTIONS[part_ir]
        calc = rate_pct * irrp_before_reduction
        if calc < min_red:
            irrp_reduction = min_red
        elif calc > max_red:
            irrp_reduction = max_red
        else:
            irrp_reduction = calc

    result = max((irrp_before_reduction - irrp_reduction) / 12.0, 0.0)
    return result


def compute_trimf(gross, trimf_persons):
    """
    Calcul TRIMF à partir d'un montant mensuel par personne imposable.
    La grille reste isolée afin de pouvoir être remplacée/configurée.
    """
    gross = max(float(gross or 0.0), 0.0)
    persons = max(float(trimf_persons or 1.0), 1.0)

    rate = 0.0
    for ceiling, monthly_amount in TRIMF_MONTHLY_TARIFFS:
        if gross <= ceiling:
            rate = monthly_amount
            break

    return rate * persons


def compute_ipres(gross, status):
    gross = max(float(gross or 0.0), 0.0)
    rg_base = min(gross, IPRES_RG_CEILING)
    ipres_rg = rg_base * IPRES_RG_RATE
    ipres_rc = gross * IPRES_RC_RATE if status == 'cadre' else 0.0
    return ipres_rg, ipres_rc


def compute_salary(gross, part_ir, trimf_persons, status):
    gross = max(float(gross or 0.0), 0.0)

    ir = compute_ir(gross, part_ir)
    trimf = compute_trimf(gross, trimf_persons)
    ipres_rg, ipres_rc = compute_ipres(gross, status)

    net_before_transport = gross - ir - trimf - ipres_rg - ipres_rc

    return {
        'gross': gross,
        'ir': ir,
        'trimf': trimf,
        'ipres_rg': ipres_rg,
        'ipres_rc': ipres_rc,
        'transport': TRANSPORT_AMOUNT,
        'net_before_transport': net_before_transport,
        'net_to_pay': net_before_transport + TRANSPORT_AMOUNT,
    }


def solve_gross_for_net(target_net, base_salary, part_ir, trimf_persons, status):
    """
    Recherche par dichotomie du brut qui se rapproche le plus du net souhaité.
    Le transport de 26 000 FCFA est intégré dans le net à payer.
    """
    target_net = max(float(target_net or 0.0), 0.0)
    base_salary = max(float(base_salary or 0.0), 0.0)

    target_without_transport = max(target_net - TRANSPORT_AMOUNT, 0.0)

    lower = base_salary
    high = max(100000.0, target_without_transport, base_salary)

    for _ in range(30):
        high_result = compute_salary(high, part_ir, trimf_persons, status)
        if high_result['net_before_transport'] >= target_without_transport:
            break
        high *= 2.0

    for _ in range(80):
        if high - lower <= 1.0:
            break

        middle = floor((lower + high) / 2.0)
        middle_result = compute_salary(middle, part_ir, trimf_persons, status)

        if middle_result['net_before_transport'] < target_without_transport:
            lower = middle + 1.0
        else:
            high = middle

    center = int(round(high))
    candidates = range(max(int(base_salary), center - 3000), center + 3001)

    best = None
    for gross in candidates:
        result = compute_salary(gross, part_ir, trimf_persons, status)
        diff = abs(result['net_to_pay'] - target_net)
        key = (diff, gross)

        if best is None or key < best[0]:
            best = (key, result)

    return best[1]
