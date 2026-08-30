def format_nom_ejecutivo_old(name):
    """
    Formatea el nombre del ejecutivo de 'Nombre Apellido' a 'Apellido Nombre' (para NOM_EJECUTIVO_OLD).
    Toma los últimos términos como apellidos y los primeros como nombres.
    """
    if not name:
        return ""
    words = str(name).strip().split()
    if len(words) >= 4 and words[-3].upper() in ["DE", "DEL", "LA"]:
        last_names = " ".join(words[-3:])
        first_names = " ".join(words[:-3])
        return f"{last_names} {first_names}"
    elif len(words) >= 3:
        last_names = " ".join(words[-2:])
        first_names = " ".join(words[:-2])
        return f"{last_names} {first_names}"
    elif len(words) == 2:
        return f"{words[1]} {words[0]}"
    return " ".join(words)
