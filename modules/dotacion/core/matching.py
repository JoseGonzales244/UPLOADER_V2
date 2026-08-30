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
