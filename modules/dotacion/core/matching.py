def mismo_supervisor(name1, name2):
    """
    Compara dos nombres de supervisores y determina si se refieren al mismo supervisor.
    Interpreta que si todos los tokens del nombre más corto están presentes en el nombre más largo, son el mismo.
    Ejemplo: 'CESSY LILIANA RAMIREZ BRAVO' y 'CESSY RAMIREZ' -> True.
    """
    if not name1 or not name2:
        return False
    
    n1_clean = str(name1).strip().upper().replace("VACACIONES", "").replace("LICENCIA", "").strip()
    n2_clean = str(name2).strip().upper().replace("VACACIONES", "").replace("LICENCIA", "").strip()
    
    if not n1_clean or not n2_clean:
        return False
        
    t1 = set(n1_clean.split())
    t2 = set(n2_clean.split())
    
    if not t1 or not t2:
        return False
        
    # Si ambos son idénticos exactamente
    if n1_clean == n2_clean:
        return True

    short_tokens = t1 if len(t1) <= len(t2) else t2
    long_tokens = t2 if len(t1) <= len(t2) else t1

    # Si el nombre más corto tiene solo 1 token (ej: "MARIA"), no usar subconjunto para evitar falsos positivos
    if len(short_tokens) < 2:
        return t1 == t2

    return short_tokens.issubset(long_tokens)


def detect_supervisor_inconsistencies(records: list) -> list:
    """
    Analiza una lista de diccionarios de asesores y detecta inconsistencias en supervisores:
    1. Un mismo nombre de supervisor con múltiples códigos distintos.
    2. Un mismo código de supervisor con múltiples nombres distintos.
    Retorna una lista de alertas formateadas.
    """
    from collections import defaultdict

    name_to_codes = defaultdict(set)
    code_to_names = defaultdict(set)

    for r in records:
        nom = str(r.get('super') or r.get('nombre_super') or r.get('SUPERVISOR') or r.get('NOM_SUPERVISOR') or '').strip().upper()
        reg = str(r.get('reg_super') or r.get('REG_SUPER') or r.get('REG_SUPERVISOR') or '').strip().upper()
        # Ignorar vacíos o placeholders
        if nom and reg and reg not in ['NONE', 'NULL', '', 'N/A'] and nom not in ['NONE', 'NULL', '', 'N/A', 'SIN SUPERVISOR']:
            name_to_codes[nom].add(reg)
            code_to_names[reg].add(nom)

    alerts = []
    # 1. Un mismo supervisor con múltiples códigos
    for nom, codes in sorted(name_to_codes.items()):
        if len(codes) > 1:
            codigos_str = ", ".join(sorted(codes))
            alerts.append(f"⚠️ SUPERVISOR CON MÚLTIPLES CÓDIGOS: '{nom}' aparece con los códigos: [{codigos_str}]")

    # 2. Un mismo código asignado a múltiples supervisores
    for reg, names in sorted(code_to_names.items()):
        if len(names) > 1:
            nombres_str = ", ".join(f"'{n}'" for n in sorted(names))
            alerts.append(f"⚠️ CÓDIGO CON MÚLTIPLES NOMBRES: Código '{reg}' está asignado a: [{nombres_str}]")

    return alerts
