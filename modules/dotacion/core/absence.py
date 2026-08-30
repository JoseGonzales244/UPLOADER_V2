import datetime

def get_last_business_day(year, month, holidays_set):
    # Encontrar el último día del mes
    if month == 12:
        last_day = datetime.date(year, 12, 31)
    else:
        last_day = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        
    curr_date = last_day
    while curr_date.month == month:
        if curr_date.weekday() < 5 and curr_date not in holidays_set:
            return curr_date
        curr_date -= datetime.timedelta(days=1)
    return last_day

def check_absence_status(row_dict, num_business_days, holidays_set, year, month):
    dias_ausente = row_dict.get('DIAS AUSENCIA TOTAL', 0) or row_dict.get('DÍAS AUSENTE', 0) or 0
    try:
        dias_ausente = int(dias_ausente)
    except (ValueError, TypeError):
        dias_ausente = 0

    dias_vac = row_dict.get('DIAS VACACIONES TOTALES', 0)
    try:
        dias_vac = int(dias_vac)
    except (ValueError, TypeError):
        dias_vac = 0
        
    situacion = str(row_dict.get('SITUACIÓN', '')).strip().upper()
    
    # Recolectar y parsear todos los periodos de vacaciones (1, 2, 3...)
    vac_periods = []
    for p_num in range(1, 5):
        s_key = f'INICIO DE VACACIONES {p_num}'
        e_key = f'FIN DE VACACIONES {p_num}'
        v_start = row_dict.get(s_key)
        v_end = row_dict.get(e_key)
        if v_start and v_end:
            if isinstance(v_start, str):
                try: v_start = datetime.datetime.strptime(v_start, "%Y-%m-%d").date()
                except (ValueError, TypeError): v_start = None
            elif isinstance(v_start, datetime.datetime):
                v_start = v_start.date()
                
            if isinstance(v_end, str):
                try: v_end = datetime.datetime.strptime(v_end, "%Y-%m-%d").date()
                except (ValueError, TypeError): v_end = None
            elif isinstance(v_end, datetime.datetime):
                v_end = v_end.date()
            
            if v_start and v_end:
                vac_periods.append((v_start, v_end))

    if situacion == 'CON AUSENCIA':
        # El último día hábil no se cuenta para evaluación
        eval_business_days = num_business_days - 1
        
        # Verificar si alguna de las vacaciones del ejecutivo incluye el último día hábil
        last_b_day = get_last_business_day(year, month, holidays_set)
        is_vac_on_last_day = False
        
        for vs, ve in vac_periods:
            if vs <= last_b_day <= ve:
                is_vac_on_last_day = True
                break
        
        # Ajustar días de vacaciones del ejecutivo para el periodo de evaluación
        eval_vac_days = dias_vac - 1 if is_vac_on_last_day else dias_vac
        
        # Calcular porcentaje de vacaciones respecto a los días de evaluación
        vac_ratio = (eval_vac_days / eval_business_days) if eval_business_days > 0 else 0
        
        # 1. Si las vacaciones cubren el 95% o más (usando redondeo a 2 decimales para incluir 18/19 = 94.74% -> 95%)
        if round(vac_ratio, 2) >= 0.95 or dias_vac >= num_business_days:
            return 'VACACIONES TODO EL MES'
        elif dias_vac >= 5 or vac_ratio >= 0.25:
            return 'VACACIONES'
            
        # 2. Si el ejecutivo está totalmente ausente del mes debido a otras razones (ej. licencia):
        if dias_ausente >= num_business_days:
            return 'LICENCIA'
            
        # 3. Para ausencias que no sean vacaciones (ej. licencias médicas) que cubran casi todo el mes:
        non_vac_absence = dias_ausente - dias_vac
        if non_vac_absence >= num_business_days - 2:
            return 'LICENCIA'
            
    return None
