from core.readers import _should_use_manual_excel_reader


def test_manual_reader_is_used_for_p025_and_p026_templates():
    assert _should_use_manual_excel_reader("P001-CALIDAD_SA") is True
    assert _should_use_manual_excel_reader("P025-SA_TCAD") is True
    assert _should_use_manual_excel_reader("P026-CROSS_TCAD") is True
    assert _should_use_manual_excel_reader("P026-ENCUESTAS_NPS") is True
    assert _should_use_manual_excel_reader("P030-RETENCION_CONVENIOS") is True
    assert _should_use_manual_excel_reader("P999-OTRA") is False
