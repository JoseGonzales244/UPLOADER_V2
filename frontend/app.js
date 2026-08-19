/**
 * Plataforma Calidad Televentas - Interbank
 * App Principal React 18 (Optimizado sin transpilación Babel en runtime)
 */

const { useState, useEffect, useRef, createElement: h } = React;

// Simple Toast Notification Manager
const toastListeners = [];
const showToast = (message, type = 'info', duration = 4000) => {
  const toast = { id: Date.now() + Math.random(), message, type };
  toastListeners.forEach((listener) => listener(toast, duration));
};

function ToastContainer() {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    const handleAddToast = (toast, duration) => {
      setToasts((prev) => [...prev, toast]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== toast.id));
      }, duration);
    };
    toastListeners.push(handleAddToast);
    return () => {
      const idx = toastListeners.indexOf(handleAddToast);
      if (idx > -1) toastListeners.splice(idx, 1);
    };
  }, []);

  if (toasts.length === 0) return null;

  return h('div', { id: 'toast-container' },
    toasts.map((t) => {
      const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
      };
      return h('div', { key: t.id, class: `toast-item toast-${t.type}` },
        h('span', { class: 'text-base' }, icons[t.type] || 'ℹ️'),
        h('div', { class: 'flex-1 font-medium' }, t.message)
      );
    })
  );
}

const TEMPLATE_TABLE_MAP = {
  'P001-CALIDAD_SA': 'DLAB_GEC.M_EXP_CALIDAD_DATA_SPEECH_ANALYTICS',
  'P002-LPDP': 'DLAB_GEC.DATA_LPDP_SA',
  'P003-CD40K': 'DLAB_GEC.DATA_CD40K_SA',
  'P004-ACC_TOMADA': 'DLAB_GEC.M_EXP_NTD_OBSERVACIONES_PRE',
  'P007-CONSULTAS_BT': 'DLAB_GEC.DATA_CONSULTAS_BT',
  'P008-INSIGHT_07_EVALUATIONS': 'DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE',
  'P009-INSIGHT_01_TRAFICO_GENESYS': 'DLAB_GEC.M_EXP_TRAFICO_GENESIS',
  'P010-INSIGHT_02_CONV_ATTRIBUTES': 'DLAB_GEC.M_EXP_BT_CONVERSATIONS_ATTRIBUTES',
  'P011-INSIGHT_03_DERIVA_BT': 'DLAB_GEC.M_EXP_DERIVA_BT_TIEMPOS',
  'P012-INSIGHT_04_CLOUD_MARCA_TRANSF': 'DLAB_GEC.M_EXP_CO_CLOUD_MARCA_TRASNFERENCIA_PRE',
  'P013-INSIGHT_05_BT_TRANSFERENCIA': 'DLAB_GEC.M_DERIVA_BT_EV_TRANSFERENCIA',
  'P014-INSIGHT_06_IVR_VENTAS': 'DLAB_GEC.M_EXP_IVR_VENTAS_2022',
  'P016-MAESTRA_PESOS_PC': 'DLAB_GEC.M_EXP_MAESTRA_PESOS_SA',
  'P021-TELEVENTAS_EJECUTIVOS': 'DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS',
  'P025-SA_TCAD': 'DLAB_GEC.M_EXP_DATA_TCAD_SA_PRE',
  'P026-CROSS_TCAD': 'DLAB_GEC.M_EXP_CROSS_TCAD',
  'P030-RETENCION_CONVENIOS': 'DLAB_GEC.DATA_RET_CONVENIOS_SA',
  'P031-PILOTO_NO_VENTA': 'DLAB_GEC.M_EXP_STAGE_NO_VENTA'
};

function App() {
  const [activeTab, setActiveTab] = useState('upload');
  const [fileType, setFileType] = useState('Excel');
  const [templates, setTemplates] = useState({});
  const [selectedTemplate, setSelectedTemplate] = useState('Ninguno');
  const [convertirSinAcentos, setConvertirSinAcentos] = useState(true);
  const [transformarVarcharLatin, setTransformarVarcharLatin] = useState(false);
  const [maxLenVarchar, setMaxLenVarchar] = useState(3000);
  const [healthStatus, setHealthStatus] = useState(null);
  const [isHealthChecking, setIsHealthChecking] = useState(false);

  const [isRunning, setIsRunning] = useState(false);
  const [currentProcess, setCurrentProcess] = useState('');
  const [progress, setProgress] = useState(0);
  const [currentPhase, setCurrentPhase] = useState(0);
  const [statusMsg, setStatusMsg] = useState('Sistema listo.');
  const [logs, setLogs] = useState([]);
  const [logFilter, setLogFilter] = useState('all');

  const [uploadedFile, setUploadedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [filePreview, setFilePreview] = useState(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [columnsConfig, setColumnsConfig] = useState([]);
  const [tdTable, setTdTable] = useState('');
  const [loadAction, setLoadAction] = useState('Solo agregar nuevos registros');

  const [audioSource, setAudioSource] = useState('outlook');
  const [outlookEmails, setOutlookEmails] = useState([]);
  const [selectedEmailIdx, setSelectedEmailIdx] = useState(null);
  const [isFetchingOutlook, setIsFetchingOutlook] = useState(false);

  const [manualSubTab, setManualSubTab] = useState('direct');
  const [manRegEv, setManRegEv] = useState('');
  const [manDni, setManDni] = useState('');
  const [manPref, setManPref] = useState('AUDIO');
  const [pastedText, setPastedText] = useState('');
  const [parsedSolList, setParsedSolList] = useState([]);

  const getDefaultPeriod = () => {
    const d = new Date();
    const year = d.getFullYear();
    const month = d.getMonth() + 1;
    return `${year}${String(month).padStart(2, '0')}`;
  };

  const [periodoConsumo, setPeriodoConsumo] = useState(getDefaultPeriod());
  const [periodoAudios, setPeriodoAudios] = useState(getDefaultPeriod());
  const [clearConsent, setClearConsent] = useState(false);
  const [consumoPhases, setConsumoPhases] = useState({ f1: true, f2: true, f3: true, f4: true, f5: true });
  const [startScriptConsumo, setStartScriptConsumo] = useState('Todo');

  const [periodoCalidad, setPeriodoCalidad] = useState(getDefaultPeriod());
  const [calidadPhases, setCalidadPhases] = useState({ f1: true, f2: true, f3: true, f4: true, f5: true });
  const [startScriptCalidad, setStartScriptCalidad] = useState('Todo');
  const [soloCierre, setSoloCierre] = useState(false);
  const [cierreScripts, setCierreScripts] = useState({ s1: true, s2: true, s3: true });

  const logConsoleRef = useRef(null);

  useEffect(() => {
    fetch('/api/templates')
      .then((r) => r.json())
      .then((d) => setTemplates(d.templates || {}))
      .catch(console.error);
  }, []);

  useEffect(() => {
    // Solicitar permisos de notificación de escritorio si el navegador lo soporta
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().catch(() => {});
    }
  }, []);

  const wasRunningRef = useRef(false);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/logs`;
    let socket;

    function connectWS() {
      socket = new WebSocket(wsUrl);
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Detectar transición de ejecución finalizada para notificar al escritorio
          if (wasRunningRef.current && data.running === false && data.message) {
            if ('Notification' in window && Notification.permission === 'granted') {
              try {
                new Notification('Uploader V2 - Proceso Finalizado', {
                  body: data.message,
                  icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">📊</text></svg>'
                });
              } catch (e) {
                console.warn('No se pudo emitir la notificación del navegador:', e);
              }
            }
          }
          if (data.running !== undefined) {
            wasRunningRef.current = data.running;
            setIsRunning(data.running);
          }
          if (data.current_process !== undefined) setCurrentProcess(data.current_process || '');

          if (data.message) {
            setStatusMsg(data.message);
            if (data.progress !== undefined) setProgress(data.progress * 100);
            if (data.phase !== undefined) setCurrentPhase(data.phase);

            setLogs((prev) => {
              const newTime = data.timestamp || new Date().toLocaleTimeString();
              const rawText = data.message;
              const isCarriageReturn = rawText.startsWith('\r');
              const newText = rawText.replace(/^\r+/, '').trim();
              const newType = data.type || 'info';

              const getSig = (txt) => {
                if (!txt) return null;
                const clean = txt.replace(/^\r+/, '').trim();
                if (clean.includes('Paso ') || clean.includes('Procesando paso')) {
                  const m = clean.match(/([a-zA-Z0-9_]+\.sql)/i) || clean.match(/^(.*?)[—\-]/);
                  return m ? 'step_' + m[1].toLowerCase() : 'step_' + clean;
                }
                if (clean.includes('Cargando registros') || clean.includes('Procesando carga')) {
                  return 'carga_registros';
                }
                if (clean.includes('Ejecutando sentencia') || clean.includes('Ejecutando:')) {
                  return 'exec_sentencia';
                }
                if (clean.includes('Descargando') && (clean.includes('%') || clean.includes('insumo'))) {
                  return 'descarga_progreso';
                }
                const progressMatch = clean.match(/^(.*?)(\d+%\s*|\(\d+[\/%]\d*\))/i);
                if (progressMatch) {
                  return 'prog_' + progressMatch[1].trim().toLowerCase();
                }
                return null;
              };

              const isMilestone = newText.startsWith('✅') || 
                                  newText.startsWith('🎉') || 
                                  newText.startsWith('🏁') || 
                                  newText.startsWith('⚡') || 
                                  newText.startsWith('📡') || 
                                  newText.startsWith('🚀') || 
                                  newText.startsWith('📥') || 
                                  newText.startsWith('❌') || 
                                  newText.startsWith('⚠️') ||
                                  newType === 'success' ||
                                  newType === 'warning' ||
                                  newType === 'error';

              if (prev.length > 0 && !isMilestone) {
                const lastLog = prev[prev.length - 1];
                if (lastLog.text === newText) {
                  return prev;
                }
                const sigNew = getSig(newText);
                const sigLast = getSig(lastLog.text);

                if (sigNew && sigLast && sigNew === sigLast) {
                  const updated = [...prev];
                  updated[updated.length - 1] = {
                    time: newTime,
                    text: newText,
                    type: newType
                  };
                  return updated;
                }
              }

              return [
                ...prev.slice(-499),
                { time: newTime, text: newText, type: newType }
              ];
            });
          }
        } catch (err) {
          console.error('Error procesando mensaje WS:', err);
        }
      };
      socket.onclose = () => setTimeout(connectWS, 3000);
    }

    connectWS();
    return () => socket && socket.close();
  }, []);

  useEffect(() => {
    if (logConsoleRef.current) {
      logConsoleRef.current.scrollTop = logConsoleRef.current.scrollHeight;
    }
  }, [logs]);

  const handleRunHealthCheck = async () => {
    setIsHealthChecking(true);
    try {
      const res = await fetch('/api/health-check');
      const data = await res.json();
      setHealthStatus(data.health || {});
      showToast('Verificación de entorno completada', 'success');
    } catch (err) {
      showToast('Error verificando entorno: ' + err.message, 'error');
    } finally {
      setIsHealthChecking(false);
    }
  };

  const fetchFilePreview = async (fileObj, typeVal, templateVal) => {
    if (!fileObj) return;
    setIsPreviewLoading(true);

    const formData = new FormData();
    formData.append('file', fileObj);
    formData.append('file_type', typeVal);
    formData.append('selected_template', templateVal);

    try {
      const res = await fetch('/api/upload/preview', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        setFilePreview(data);
        setColumnsConfig(data.columns || []);
        showToast('Vista previa cargada exitosamente', 'info');
      } else {
        showToast('Error leyendo vista previa: ' + (data.detail || 'Fallo desconocido'), 'error');
      }
    } catch (err) {
      showToast('Error enviando archivo: ' + err.message, 'error');
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const processSelectedFile = async (file) => {
    if (!file) return;
    setUploadedFile(file);
    await fetchFilePreview(file, fileType, selectedTemplate);
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    await processSelectedFile(file);
  };

  const handleRemoveFile = (e) => {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    setUploadedFile(null);
    setFilePreview(null);
    setColumnsConfig([]);
    const inputEl = document.getElementById('teradata-file-input');
    if (inputEl) inputEl.value = '';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragging) setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    let file = null;
    if (e.dataTransfer.items) {
      if (e.dataTransfer.items.length > 0 && e.dataTransfer.items[0].kind === 'file') {
        file = e.dataTransfer.items[0].getAsFile();
      }
    } else if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      file = e.dataTransfer.files[0];
    }

    if (file) {
      await processSelectedFile(file);
    }
  };

  const handleTemplateChange = async (e) => {
    const newTpl = e.target.value;
    setSelectedTemplate(newTpl);
    if (TEMPLATE_TABLE_MAP[newTpl]) {
      setTdTable(TEMPLATE_TABLE_MAP[newTpl]);
    } else {
      setTdTable('');
    }
    if (uploadedFile) {
      await fetchFilePreview(uploadedFile, fileType, newTpl);
    }
  };

  const handleFileTypeChange = async (e) => {
    const newType = e.target.value;
    setFileType(newType);
    if (uploadedFile) {
      await fetchFilePreview(uploadedFile, newType, selectedTemplate);
    }
  };

  const handleUploadToTeradata = async () => {
    if (isRunning) return;
    if (!uploadedFile) {
      showToast('Por favor seleccione un archivo primero', 'warning');
      return;
    }
    if (!tdTable) {
      showToast('Por favor ingrese la tabla destino de Teradata', 'warning');
      return;
    }

    const formData = new FormData();
    formData.append('file', uploadedFile);
    formData.append('file_type', fileType);
    formData.append('selected_template', selectedTemplate);
    formData.append('convertir_sin_acentos', convertirSinAcentos);
    formData.append('transformar_varchar_latin', transformarVarcharLatin);
    formData.append('max_len_varchar', maxLenVarchar);
    formData.append('teradata_table', tdTable);
    formData.append('load_action', loadAction);
    if (columnsConfig.length > 0) {
      formData.append('columns_json', JSON.stringify(columnsConfig));
    }

    setIsRunning(true);
    setCurrentProcess(`Ingesta Teradata: ${tdTable}`);
    setLogs([]);

    try {
      const res = await fetch('/api/upload/teradata', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) {
        showToast(data.detail || 'Error iniciando la carga a Teradata', 'error');
        setIsRunning(false);
      } else {
        showToast(`Proceso de ingesta a ${tdTable} iniciado`, 'success');
      }
    } catch (err) {
      showToast('Error enviando solicitud de carga: ' + err.message, 'error');
      setIsRunning(false);
    }
  };

  const handleFetchOutlook = async () => {
    setIsFetchingOutlook(true);
    try {
      const res = await fetch('/api/audios/outlook-fetch');
      const data = await res.json();
      setOutlookEmails(data.correos || []);
      showToast(`Se encontraron ${data.correos ? data.correos.length : 0} correos recientes`, 'info');
    } catch (err) {
      showToast('Error conectando con Outlook: ' + err.message, 'error');
    } finally {
      setIsFetchingOutlook(false);
    }
  };

  useEffect(() => {
    if (!pastedText) {
      setParsedSolList([]);
      return;
    }
    const lines = pastedText.split('\n');
    const list = [];
    const seen = new Set();
    lines.forEach((line) => {
      const mReg = line.match(/\b([A-Za-z]\d{5})\b/);
      const mDni = line.match(/\b(\d{7,8})\b/);
      if (mReg && mDni) {
        const reg = mReg[1].toUpperCase();
        const dni = mDni[1].padStart(8, '0');
        const key = `${reg}_${dni}`;
        if (!seen.has(key)) {
          seen.add(key);
          list.push({
            reg_ev: reg,
            dni: dni,
            nombre_archivo: `${manPref}_${reg}_DNI${dni}`,
            prefijo: manPref
          });
        }
      }
    });
    setParsedSolList(list);
  }, [pastedText, manPref]);

  const handleRunAudios = async () => {
    if (isRunning) return;
    let reqList = [];
    if (audioSource === 'outlook') {
      if (selectedEmailIdx === null || !outlookEmails[selectedEmailIdx]) {
        showToast('Seleccione un correo de Outlook primero', 'warning');
        return;
      }
      reqList = outlookEmails[selectedEmailIdx].solicitudes || [];
    } else {
      if (manualSubTab === 'direct') {
        if (!manRegEv || !manDni) {
          showToast('Ingrese tanto el Registro Ejecutivo como el DNI', 'warning');
          return;
        }
        const regClean = manRegEv.trim().toUpperCase();
        const dniClean = manDni.trim().padStart(8, '0');
        reqList = [{
          reg_ev: regClean,
          dni: dniClean,
          nombre_archivo: `${manPref}_${regClean}_DNI${dniClean}`,
          prefijo: manPref
        }];
      } else {
        if (parsedSolList.length === 0) {
          showToast('No se detectaron solicitudes válidas en el texto pegado', 'warning');
          return;
        }
        reqList = parsedSolList;
      }
    }

    if (reqList.length === 0) {
      showToast('No hay solicitudes válidas para procesar', 'warning');
      return;
    }

    setIsRunning(true);
    setCurrentProcess('Solicitud de Audios (Genesys)');
    setLogs([]);
    try {
      const res = await fetch('/api/audios/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          solicitudes: reqList,
          periodo: periodoAudios
        })
      });
      if (!res.ok) {
        const data = await res.json();
        showToast(data.detail || 'Error iniciando descarga de audios', 'error');
        setIsRunning(false);
      } else {
        showToast('Proceso de descarga de audios iniciado', 'success');
      }
    } catch (err) {
      showToast('Error conectando con el backend: ' + err.message, 'error');
      setIsRunning(false);
    }
  };

  const handleRunConsumo = async () => {
    if (isRunning) return;
    setIsRunning(true);
    setCurrentProcess('PBI Base Consumo');
    setLogs([]);
    try {
      const res = await fetch('/api/orchestrate/consumo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          periodo: periodoConsumo,
          run_phase1: consumoPhases.f1,
          run_phase2: consumoPhases.f2,
          run_phase3: consumoPhases.f3,
          run_phase4: consumoPhases.f4,
          run_phase5: consumoPhases.f5,
          clear_consent: clearConsent,
          start_script: startScriptConsumo === 'Todo' ? null : startScriptConsumo
        })
      });
      if (!res.ok) {
        const data = await res.json();
        showToast(data.detail || 'Error iniciando Consumo', 'error');
        setIsRunning(false);
      } else {
        showToast('Orquestación de PBI Consumo iniciada', 'success');
      }
    } catch (err) {
      showToast('Error conectando con el backend: ' + err.message, 'error');
      setIsRunning(false);
    }
  };

  const handleRunCalidad = async () => {
    if (isRunning) return;
    setIsRunning(true);
    setCurrentProcess(soloCierre ? 'Cierre Mensual (01 Auditoría + 02 KRI)' : 'PBI Evaluaciones Calidad');
    setLogs([]);
    try {
      const res = await fetch('/api/orchestrate/calidad', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          periodo: periodoCalidad,
          run_fase1: calidadPhases.f1,
          run_fase2: calidadPhases.f2,
          run_fase3: calidadPhases.f3,
          run_fase4: calidadPhases.f4,
          run_fase5: calidadPhases.f5,
          start_script: startScriptCalidad === 'Todo' ? null : startScriptCalidad,
          solo_cierre: soloCierre,
          run_cierre_01: cierreScripts.s1,
          run_cierre_02: cierreScripts.s2,
          run_cierre_03: cierreScripts.s3
        })
      });
      if (!res.ok) {
        const data = await res.json();
        showToast(data.detail || 'Error iniciando Calidad/Cierre', 'error');
        setIsRunning(false);
      } else {
        showToast(soloCierre ? 'Proceso de Cierre Mensual iniciado' : 'Orquestación de Calidad iniciada', 'success');
      }
    } catch (err) {
      showToast('Error conectando con el backend: ' + err.message, 'error');
      setIsRunning(false);
    }
  };

  const handleStopProcess = async () => {
    try {
      const res = await fetch('/api/orchestrate/stop', { method: 'POST' });
      const data = await res.json();
      showToast(data.message || 'Solicitud de parada enviada', 'warning');
      setIsRunning(false);
      setCurrentProcess('');
    } catch (err) {
      showToast('Error al detener el proceso: ' + err.message, 'error');
    }
  };

  const filteredLogs = logs.filter((log) => {
    if (logFilter === 'all') return true;
    return log.type === logFilter;
  });

  return h('div', { class: 'flex-1 flex flex-col h-screen overflow-hidden' },
    h(ToastContainer),

    // Header Corporate Navigation Bar
    h('header', { class: 'ib-card rounded-none border-t-0 border-x-0 px-6 py-3.5 flex items-center justify-between z-50 shrink-0' },
      h('div', { class: 'flex items-center gap-3.5' },
        h('div', { class: 'w-11 h-11 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center font-display font-extrabold text-white text-lg shadow-lg shadow-emerald-950/50 tracking-wider' }, 'IB'),
        h('div', null,
          h('h1', { class: 'text-base font-bold text-white font-display tracking-tight flex items-center gap-2' },
            'Plataforma Calidad Televentas',
            h('span', { class: 'text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-950 border border-emerald-700/60 text-emerald-400' }, 'v2.0')
          ),
          h('p', { class: 'text-xs text-slate-400 font-medium' }, 'Ingesta Teradata • Genesys Audios • Orquestador PBI')
        )
      ),

      h('div', { class: 'flex items-center gap-4' },
        h('div', { class: 'flex items-center gap-2.5 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-slate-900/90 border border-slate-700/80 shadow-inner' },
          h('span', { class: `w-2.5 h-2.5 rounded-full ${isRunning ? 'bg-amber-400 animate-pulse shadow-sm shadow-amber-400' : 'bg-emerald-400 shadow-sm shadow-emerald-400'}` }),
          h('span', { class: 'text-slate-200' }, isRunning ? `Ejecutando: ${currentProcess}` : 'Sistema listo')
        ),
        isRunning && h('button', {
          onClick: handleStopProcess,
          class: 'px-3.5 py-1.5 rounded-full text-xs font-bold bg-rose-600 hover:bg-rose-500 text-white shadow-md shadow-rose-950/50 flex items-center gap-1.5 transition cursor-pointer active:scale-95'
        }, '🛑 Detener Proceso')
      )
    ),

    // Main Workspace Layout
    h('div', { class: 'flex-1 flex overflow-hidden' },
      // Left Sidebar Controls
      h('aside', { class: 'sidebar-panel w-80 p-5 flex flex-col gap-6 overflow-y-auto shrink-0' },
        activeTab === 'upload' && h('div', { class: 'space-y-4' },
          h('div', { class: 'flex items-center gap-2 text-slate-200 font-bold text-xs uppercase tracking-wider border-b border-slate-800 pb-2.5 font-display' },
            h('span', null, '⚙️'), 'Configuración de Lectura'
          ),
          h('div', null,
            h('label', { class: 'block text-xs font-medium text-slate-400 mb-1.5' }, 'Tipo de archivo a cargar'),
            h('select', {
              value: fileType,
              onChange: handleFileTypeChange,
              class: 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none transition'
            },
              h('option', { value: 'Excel' }, 'Excel (.xlsx, .xls)'),
              h('option', { value: 'CSV' }, 'CSV (.csv)'),
              h('option', { value: 'Texto Unicode' }, 'Texto Unicode (.txt)')
            )
          ),
          h('div', null,
            h('label', { class: 'block text-xs font-medium text-slate-400 mb-1.5' }, '📋 Plantillas de Mapeo'),
            h('select', {
              value: selectedTemplate,
              onChange: handleTemplateChange,
              class: 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none transition'
            },
              h('option', { value: 'Ninguno' }, 'Ninguno'),
              Object.keys(templates).map((name) => h('option', { key: name, value: name }, name))
            )
          )
        ),

        activeTab === 'upload' && h('div', { class: 'space-y-3' },
          h('div', { class: 'flex items-center gap-2 text-slate-200 font-bold text-xs uppercase tracking-wider border-b border-slate-800 pb-2.5 font-display' },
            h('span', null, '🧹'), 'Limpieza de Datos'
          ),
          h('label', { class: 'flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer select-none' },
            h('input', {
              type: 'checkbox',
              checked: convertirSinAcentos,
              onChange: (e) => setConvertirSinAcentos(e.target.checked),
              class: 'accent-emerald-500 rounded w-4 h-4'
            }),
            h('span', null, 'Eliminar acentos en textos')
          ),
          h('label', { class: 'flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer select-none' },
            h('input', {
              type: 'checkbox',
              checked: transformarVarcharLatin,
              onChange: (e) => setTransformarVarcharLatin(e.target.checked),
              class: 'accent-emerald-500 rounded w-4 h-4'
            }),
            h('span', null, 'Limpiar caracteres especiales (LATIN)')
          ),
          transformarVarcharLatin && h('div', { class: 'mt-2' },
            h('label', { class: 'block text-xs text-slate-400 mb-1' }, 'Longitud máxima VARCHAR'),
            h('input', {
              type: 'number',
              value: maxLenVarchar,
              onChange: (e) => setMaxLenVarchar(Number(e.target.value)),
              class: 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white font-mono-code'
            })
          )
        ),

        h('div', { class: 'space-y-3 pt-2' },
          h('div', { class: 'flex items-center gap-2 text-slate-200 font-bold text-xs uppercase tracking-wider border-b border-slate-800 pb-2.5 font-display' },
            h('span', null, '🩺'), 'Diagnóstico de Entorno'
          ),
          h('button', {
            onClick: handleRunHealthCheck,
            disabled: isHealthChecking,
            class: 'w-full py-2.5 px-3 rounded-lg btn-secondary-ib text-xs font-semibold transition flex items-center justify-center gap-2'
          }, isHealthChecking ? 'Verificando...' : '🔍 Verificar Entorno'),

          healthStatus && h('div', { class: 'space-y-2 text-xs pt-1' },
            Object.entries(healthStatus).map(([key, info]) =>
              h('div', { key: key, class: 'flex items-center gap-2 bg-slate-900/60 p-2 rounded-md border border-slate-800' },
                h('span', null, info.status ? '✅' : '⚠️'),
                h('span', { class: 'text-slate-300 text-[11px] font-medium' }, info.message)
              )
            )
          )
        )
      ),

      // Main Content Area
      h('main', { class: 'flex-1 flex flex-col p-6 overflow-y-auto space-y-6' },
        // Tabs Header
        h('nav', { class: 'ib-card p-1.5 rounded-xl flex gap-2 border border-slate-800 shrink-0', role: 'tablist' },
          [
            { id: 'upload', icon: '📁', label: 'Subir a Teradata' },
            { id: 'audios', icon: '🎧', label: 'Audios Genesys' },
            { id: 'consumo', icon: '⚡', label: 'PBI Base Consumo' },
            { id: 'calidad', icon: '📊', label: 'PBI Evaluaciones Calidad' }
          ].map((tab) =>
            h('button', {
              key: tab.id,
              role: 'tab',
              'aria-selected': activeTab === tab.id,
              onClick: () => setActiveTab(tab.id),
              class: `flex-1 py-3 px-4 rounded-lg text-xs font-bold font-display transition-all duration-200 flex items-center justify-center gap-2 ${
                activeTab === tab.id
                  ? 'bg-gradient-to-r from-emerald-600 to-emerald-500 text-white shadow-lg shadow-emerald-950/60'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`
            },
              h('span', { class: 'text-sm' }, tab.icon),
              tab.label
            )
          )
        ),

        // TAB 1: SUBIR A TERADATA
        activeTab === 'upload' && h('div', { class: 'space-y-6' },
          h('div', { class: 'ib-card p-6 space-y-4' },
            h('h2', { class: 'text-sm font-bold text-white uppercase tracking-wider border-b border-slate-800 pb-2.5 font-display' },
              `📁 Cargar Archivo Origen (${fileType})`
            ),
            h('div', {
              onDragEnter: handleDragOver,
              onDragOver: handleDragOver,
              onDragLeave: handleDragLeave,
              onDrop: handleDrop,
              class: `relative border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-200 ${
                isDragging
                  ? 'border-emerald-400 bg-emerald-950/40 shadow-lg shadow-emerald-950/50 scale-[1.01]'
                  : uploadedFile
                  ? 'border-emerald-600/60 bg-slate-900/50 hover:border-emerald-500 hover:bg-slate-850/60'
                  : 'border-slate-700 bg-slate-900/30 hover:border-slate-500 hover:bg-slate-850/50'
              }`
            },
              uploadedFile && h('button', {
                type: 'button',
                onClick: handleRemoveFile,
                title: 'Quitar archivo',
                class: 'absolute top-3 right-3 z-10 w-7 h-7 rounded-full bg-slate-800/90 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 border border-slate-700 hover:border-rose-500/50 flex items-center justify-center transition-all duration-150 shadow-md group',
                'aria-label': 'Quitar archivo'
              },
                h('span', { class: 'text-xs font-bold leading-none' }, '✕')
              ),
              h('input', {
                type: 'file',
                id: 'teradata-file-input',
                onChange: handleFileChange,
                class: 'hidden'
              }),
              h('label', {
                htmlFor: 'teradata-file-input',
                class: 'cursor-pointer flex flex-col items-center justify-center space-y-2'
              },
                h('div', { class: `w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
                  isDragging ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-400'
                }` },
                  h('span', { class: 'text-2xl' }, isDragging ? '📥' : (uploadedFile ? '📄' : '☁️'))
                ),
                h('div', { class: 'space-y-1' },
                  uploadedFile
                    ? h('div', {},
                        h('p', { class: 'text-xs font-semibold text-emerald-400 font-mono-code' }, uploadedFile.name),
                        h('p', { class: 'text-[11px] text-slate-400' }, `${(uploadedFile.size / 1024).toFixed(1)} KB — Clic o arrastra para cambiar archivo`)
                      )
                    : h('div', {},
                        h('p', { class: 'text-xs font-semibold text-slate-200' },
                          'Arrastra y suelta tu archivo aquí, o ',
                          h('span', { class: 'text-emerald-400 underline decoration-emerald-500/40 underline-offset-2' }, 'examina tus archivos')
                        ),
                        h('p', { class: 'text-[11px] text-slate-400' },
                          `Archivos soportados para tipo ${fileType}: ${
                            fileType === 'Excel' ? '.xlsx, .xls' : fileType === 'CSV' ? '.csv' : '.txt'
                          }`
                        )
                      )
                )
              )
            )
          ),

          filePreview && h('div', { class: 'ib-card p-6 space-y-4' },
            h('div', { class: 'flex justify-between items-center border-b border-slate-800 pb-2.5' },
              h('div', { class: 'flex items-center gap-2' },
                h('h3', { class: 'text-sm font-bold text-white font-display' }, '👀 Vista Previa de Archivo'),
                isPreviewLoading && h('span', { class: 'text-xs text-amber-400 font-semibold animate-pulse' }, 'Actualizando...')
              ),
              h('span', { class: 'text-xs text-emerald-400 font-semibold font-mono-code bg-emerald-950/60 px-3 py-1 rounded-full border border-emerald-800/60' },
                `${filePreview.total_rows} registros | ${filePreview.total_cols} columnas`
              )
            ),

            h('div', { class: 'overflow-x-auto border border-slate-800 rounded-xl max-h-56 relative bg-slate-950/60' },
              h('table', { class: 'w-full text-xs text-left text-slate-300 font-mono-code' },
                h('thead', { class: 'bg-slate-900 text-slate-200 font-semibold border-b border-slate-800 sticky top-0' },
                  h('tr', null,
                    Object.keys(filePreview.preview[0] || {}).map((col) =>
                      h('th', { key: col, class: 'px-3 py-2 whitespace-nowrap bg-slate-900' }, col)
                    )
                  )
                ),
                h('tbody', null,
                  filePreview.preview.map((row, idx) =>
                    h('tr', { key: idx, class: 'border-b border-slate-800/50 hover:bg-slate-800/40' },
                      Object.values(row).map((val, i) =>
                        h('td', { key: i, class: 'px-3 py-1.5 truncate max-w-xs whitespace-nowrap' }, String(val))
                      )
                    )
                  )
                )
              )
            ),

            h('div', { class: 'pt-4 border-t border-slate-800 grid grid-cols-1 md:grid-cols-2 gap-4' },
              h('div', null,
                h('label', { class: 'block text-xs text-slate-400 mb-1 font-medium' }, 'Tabla Destino Teradata'),
                h('input', {
                  type: 'text',
                  value: tdTable,
                  onChange: (e) => setTdTable(e.target.value),
                  placeholder: 'DLAB_GEC.nombre_tabla',
                  class: 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono-code focus:border-emerald-500 outline-none'
                })
              ),
              h('div', null,
                h('label', { class: 'block text-xs text-slate-400 mb-1 font-medium' }, 'Acción de Carga'),
                h('select', {
                  value: loadAction,
                  onChange: (e) => setLoadAction(e.target.value),
                  class: 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:border-emerald-500 outline-none'
                },
                  h('option', { value: 'Solo agregar nuevos registros' }, 'Solo agregar nuevos registros'),
                  h('option', { value: 'Reemplazar registros existentes (Vaciar y cargar)' }, 'Reemplazar registros existentes (Vaciar y cargar)')
                )
              )
            ),

            h('button', {
              onClick: handleUploadToTeradata,
              disabled: isRunning,
              class: `w-full py-3.5 rounded-xl font-bold text-sm shadow-lg transition btn-primary-ib font-display ${
                isRunning ? 'opacity-50 cursor-not-allowed' : ''
              }`
            }, isRunning ? '⏳ Ejecutando proceso...' : '🚀 Cargar a Teradata')
          )
        ),

        // TAB 2: AUDIOS GENESYS
        activeTab === 'audios' && h('div', { class: 'ib-card p-6 space-y-6' },
          h('h2', { class: 'text-sm font-bold text-white uppercase tracking-wider border-b border-slate-800 pb-2.5 font-display' },
            '🎧 Solicitud y Descarga de Audios de Genesys'
          ),
          h('div', { class: 'grid grid-cols-1 md:grid-cols-2 gap-4' },
            h('div', null,
              h('label', { class: 'block text-xs text-slate-400 mb-1 font-medium' }, 'Período de Búsqueda Genesys (YYYYMM)'),
              h('input', {
                type: 'text',
                value: periodoAudios,
                disabled: isRunning,
                onChange: (e) => setPeriodoAudios(e.target.value),
                placeholder: 'Ej: 202608',
                class: 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono-code focus:border-emerald-500 outline-none'
              })
            )
          ),
          h('div', { class: 'flex gap-6' },
            h('label', { class: 'flex items-center gap-2.5 text-xs font-semibold text-white cursor-pointer select-none' },
              h('input', {
                type: 'radio',
                name: 'audioSource',
                checked: audioSource === 'outlook',
                onChange: () => setAudioSource('outlook'),
                class: 'accent-emerald-500 w-4 h-4'
              }),
              '📧 Leer de Outlook'
            ),
            h('label', { class: 'flex items-center gap-2.5 text-xs font-semibold text-white cursor-pointer select-none' },
              h('input', {
                type: 'radio',
                name: 'audioSource',
                checked: audioSource === 'manual',
                onChange: () => setAudioSource('manual'),
                class: 'accent-emerald-500 w-4 h-4'
              }),
              '✏️ Ingreso Manual'
            )
          ),

          audioSource === 'outlook'
            ? h('div', { class: 'space-y-4' },
                h('button', {
                  onClick: handleFetchOutlook,
                  disabled: isFetchingOutlook,
                  class: 'py-2.5 px-4 rounded-xl btn-secondary-ib text-xs font-semibold flex items-center gap-2'
                }, isFetchingOutlook ? 'Consultando Outlook...' : '🔄 Buscar últimos 3 correos'),

                outlookEmails.length > 0 && h('div', { class: 'space-y-2' },
                  h('label', { class: 'block text-xs font-semibold text-slate-300 mb-1' }, 'Seleccione el correo específico:'),
                  outlookEmails.map((c, i) =>
                    h('div', {
                      key: i,
                      onClick: () => setSelectedEmailIdx(i),
                      class: `p-3.5 rounded-xl border cursor-pointer transition ${
                        selectedEmailIdx === i
                          ? 'bg-emerald-950/50 border-emerald-500 shadow-md shadow-emerald-950'
                          : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
                      }`
                    },
                      h('p', { class: 'text-xs font-bold text-white' }, `Correo #${c.index} | Asunto: ${c.asunto}`),
                      h('p', { class: 'text-xs text-slate-400 mt-1' }, `De: ${c.remitente} | Registros: ${c.cant_registros} (${c.fecha})`)
                    )
                  )
                )
              )
            : h('div', { class: 'space-y-4' },
                h('div', { class: 'flex gap-2 border-b border-slate-800 pb-2' },
                  h('button', {
                    onClick: () => setManualSubTab('direct'),
                    class: `px-3.5 py-1.5 rounded-lg text-xs font-bold font-display ${
                      manualSubTab === 'direct' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'
                    }`
                  }, 'Formulario Directo'),
                  h('button', {
                    onClick: () => setManualSubTab('paste'),
                    class: `px-3.5 py-1.5 rounded-lg text-xs font-bold font-display ${
                      manualSubTab === 'paste' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'
                    }`
                  }, '📋 Copiar y Pegar de Excel')
                ),

                manualSubTab === 'direct'
                  ? h('div', { class: 'grid grid-cols-1 md:grid-cols-3 gap-4' },
                      h('div', null,
                        h('label', { class: 'block text-xs text-slate-400 mb-1' }, 'Registro Ejecutivo (Reg EV)'),
                        h('input', {
                          type: 'text',
                          value: manRegEv,
                          onChange: (e) => setManRegEv(e.target.value),
                          placeholder: 'Ej: B12345',
                          class: 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono-code'
                        })
                      ),
                      h('div', null,
                        h('label', { class: 'block text-xs text-slate-400 mb-1' }, 'DNI'),
                        h('input', {
                          type: 'text',
                          value: manDni,
                          onChange: (e) => setManDni(e.target.value),
                          placeholder: 'Ej: 72839405',
                          class: 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono-code'
                        })
                      ),
                      h('div', null,
                        h('label', { class: 'block text-xs text-slate-400 mb-1' }, 'Producto / Prefijo'),
                        h('select', {
                          value: manPref,
                          onChange: (e) => setManPref(e.target.value),
                          class: 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono-code'
                        },
                          ['AUDIO', 'EC', 'CC', 'SEG', 'HIP', 'PP', 'TC'].map((p) => h('option', { key: p, value: p }, p))
                        )
                      )
                    )
                  : h('div', { class: 'space-y-3' },
                      h('textarea', {
                        rows: 4,
                        value: pastedText,
                        onChange: (e) => setPastedText(e.target.value),
                        placeholder: 'Pega celdas de Excel con Ejecutivo y DNI...',
                        class: 'w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-white font-mono-code outline-none focus:border-emerald-500'
                      }),
                      parsedSolList.length > 0 && h('p', { class: 'text-xs text-emerald-400 font-semibold' },
                        `✅ Se detectaron ${parsedSolList.length} solicitudes válidas en el texto.`
                      )
                    )
              ),

          h('button', {
            onClick: handleRunAudios,
            disabled: isRunning,
            class: `w-full py-3.5 rounded-xl btn-primary-ib font-bold text-sm shadow-lg font-display ${
              isRunning ? 'opacity-50 cursor-not-allowed' : ''
            }`
          }, isRunning ? '⏳ Procesando Descarga...' : '▶️ Iniciar Descarga de Audios Genesys')
        ),

        // TAB 3: PBI BASE CONSUMO
        activeTab === 'consumo' && h('div', { class: 'ib-card p-6 space-y-6' },
          h('h2', { class: 'text-sm font-bold text-white uppercase tracking-wider border-b border-slate-800 pb-2.5 font-display' },
            '⚡ Orquestación PBI Base Consumo'
          ),

          h('div', { class: 'grid grid-cols-1 md:grid-cols-2 gap-4' },
            h('div', null,
              h('label', { class: 'block text-xs text-slate-400 mb-1 font-medium' }, 'Período de Ejecución (YYYYMM)'),
              h('input', {
                type: 'text',
                value: periodoConsumo,
                disabled: isRunning,
                onChange: (e) => setPeriodoConsumo(e.target.value),
                class: 'w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono-code'
              })
            ),
            h('div', { class: 'flex items-center pt-5' },
              h('label', { class: 'flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer select-none' },
                h('input', {
                  type: 'checkbox',
                  checked: clearConsent,
                  disabled: isRunning,
                  onChange: (e) => setClearConsent(e.target.checked),
                  class: 'accent-emerald-500 rounded w-4 h-4'
                }),
                'Limpiar registros previos de Consentimiento Diario'
              )
            )
          ),

          h('div', { class: 'space-y-2' },
            h('label', { class: 'block text-xs font-semibold text-slate-300' }, 'Fases a Ejecutar:'),
            h('div', { class: 'grid grid-cols-2 md:grid-cols-5 gap-3' },
              [
                { key: 'f1', label: 'Fase 1: Insight' },
                { key: 'f2', label: 'Fase 2: CD40K' },
                { key: 'f3', label: 'Fase 3: BN Desembolsos' },
                { key: 'f4', label: 'Fase 4: Proceso SQL' },
                { key: 'f5', label: 'Fase 5: SELECT' }
              ].map((f) =>
                h('label', { key: f.key, class: 'flex items-center gap-2.5 p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-300 cursor-pointer select-none hover:border-slate-700' },
                  h('input', {
                    type: 'checkbox',
                    checked: consumoPhases[f.key],
                    disabled: isRunning,
                    onChange: (e) => setConsumoPhases({ ...consumoPhases, [f.key]: e.target.checked }),
                    class: 'accent-emerald-500 rounded w-4 h-4'
                  }),
                  f.label
                )
              )
            )
          ),

          consumoPhases.f4 && h('div', { class: 'p-3.5 bg-slate-900/80 rounded-xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3' },
            h('label', { class: 'text-xs font-semibold text-slate-300' }, '▶️ Iniciar Fase 4 (Teradata) desde:'),
            h('select', {
              value: startScriptConsumo,
              disabled: isRunning,
              onChange: (e) => setStartScriptConsumo(e.target.value),
              class: 'bg-slate-950 border border-slate-700 text-xs text-emerald-400 font-medium rounded-lg px-3 py-2 focus:border-emerald-500 outline-none font-mono-code'
            },
              h('option', { value: 'Todo' }, '▶️ Todo (Secuencia completa)'),
              h('option', { value: 'ventas_dn.sql' }, '1. VENTAS_DN.sql'),
              h('option', { value: 'cd40k.sql' }, '2. CD40K.sql'),
              h('option', { value: 'source_tvl.sql' }, '3. SOURCE_TVL.sql'),
              h('option', { value: 'ca_consentimiento_diario.sql' }, '4. CA_CONSENTIMIENTO_DIARIO.sql'),
              h('option', { value: 'kri_ventas_sin_audio.sql' }, '5. KRI_VENTAS_SIN_AUDIO.sql'),
              h('option', { value: 'tlf_no_autorizado.sql' }, '6. TLF_NO_AUTORIZADO.sql')
            )
          ),

          // Stepper gráfico
          h('div', { class: 'relative py-6 px-4 bg-slate-900/60 rounded-xl border border-slate-800' },
            h('div', { class: 'stepper-line-track' }),
            h('div', {
              class: 'stepper-progress-fill',
              style: { width: `${currentPhase > 0 ? (currentPhase - 1) * 20 + 10 : 0}%` }
            }),
            h('div', { class: 'relative z-10 flex justify-between' },
              ['1. Insight', '2. CD40K', '3. BN Desembolsos', '4. Proceso SQL', '5. SELECT'].map((lbl, idx) => {
                const stepNum = idx + 1;
                const isCompleted = currentPhase > stepNum;
                const isActive = currentPhase === stepNum;
                return h('div', { key: idx, class: 'flex flex-col items-center' },
                  h('div', {
                    class: `w-10 h-10 rounded-full flex items-center justify-center font-bold text-xs font-display transition-all ${
                      isCompleted
                        ? 'bg-emerald-500 text-white border-2 border-emerald-400 shadow-md shadow-emerald-950'
                        : isActive
                        ? 'bg-blue-600 text-white border-2 border-blue-400 shadow-lg shadow-blue-500/50 animate-pulse'
                        : 'bg-slate-800 text-slate-400 border-2 border-slate-700'
                    }`
                  }, isCompleted ? '✔' : stepNum),
                  h('span', { class: `text-[11px] font-semibold mt-2 ${isActive ? 'text-blue-400 font-bold' : 'text-slate-400'}` }, lbl)
                );
              })
            )
          ),

          h('button', {
            onClick: handleRunConsumo,
            disabled: isRunning,
            class: `w-full py-3.5 rounded-xl font-bold text-sm shadow-lg btn-primary-ib font-display ${
              isRunning ? 'opacity-50 cursor-not-allowed' : ''
            }`
          }, isRunning ? '⏳ Ejecutando Orquestación...' : '🚀 Iniciar Orquestación de Consumo')
        ),

        // TAB 4: PBI EVALUACIONES CALIDAD
        activeTab === 'calidad' && h('div', { class: 'ib-card p-6 space-y-6' },
          h('h2', { class: 'text-sm font-bold text-white uppercase tracking-wider border-b border-slate-800 pb-2.5 font-display' },
            '📊 Orquestación PBI Evaluaciones Calidad'
          ),

          h('div', null,
            h('label', { class: 'block text-xs text-slate-400 mb-1 font-medium' }, 'Período de Ejecución (YYYYMM)'),
            h('input', {
              type: 'text',
              value: periodoCalidad,
              disabled: isRunning,
              onChange: (e) => setPeriodoCalidad(e.target.value),
              class: 'w-full max-w-xs bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono-code'
            })
          ),

          h('div', { class: 'p-4 bg-slate-900/90 rounded-xl border border-blue-900/50 flex items-center justify-between' },
            h('label', { class: 'flex items-center gap-3 text-xs text-slate-200 font-semibold cursor-pointer select-none' },
              h('input', {
                type: 'checkbox',
                checked: soloCierre,
                disabled: isRunning,
                onChange: (e) => setSoloCierre(e.target.checked),
                class: 'accent-blue-500 rounded w-4 h-4'
              }),
              h('span', { class: 'text-blue-400 font-bold text-sm font-display' }, '🔒 Modo Cierre Mensual'),
              h('span', { class: 'text-slate-400 text-xs font-normal' }, '(Ejecutar exclusivamente scripts de Cierre: 01 Auditoría y 02 KRI)')
            )
          ),

          !soloCierre
            ? h('div', { class: 'space-y-4' },
                h('div', { class: 'space-y-2' },
                  h('label', { class: 'block text-xs font-semibold text-slate-300' }, 'Fases a Ejecutar:'),
                  h('div', { class: 'grid grid-cols-2 md:grid-cols-5 gap-3' },
                    [
                      { key: 'f1', label: 'Fase 1: Insight PC' },
                      { key: 'f2', label: 'Fase 2: Verint SA' },
                      { key: 'f3', label: 'Fase 3: Acción tomada' },
                      { key: 'f4', label: 'Fase 4: Scripts SQL' },
                      { key: 'f5', label: 'Fase 5: NTD' }
                    ].map((f) =>
                      h('label', { key: f.key, class: 'flex items-center gap-2.5 p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-300 cursor-pointer select-none' },
                        h('input', {
                          type: 'checkbox',
                          checked: calidadPhases[f.key],
                          disabled: isRunning,
                          onChange: (e) => setCalidadPhases({ ...calidadPhases, [f.key]: e.target.checked }),
                          class: 'accent-emerald-500 rounded w-4 h-4'
                        }),
                        f.label
                      )
                    )
                  )
                ),

                calidadPhases.f4 && h('div', { class: 'p-3.5 bg-slate-900/80 rounded-xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3' },
                  h('label', { class: 'text-xs font-semibold text-slate-300' }, '▶️ Iniciar Fase 4 desde:'),
                  h('select', {
                    value: startScriptCalidad,
                    disabled: isRunning,
                    onChange: (e) => setStartScriptCalidad(e.target.value),
                    class: 'bg-slate-950 border border-slate-700 text-xs text-emerald-400 font-medium rounded-lg px-3 py-2 font-mono-code focus:border-emerald-500 outline-none'
                  },
                    h('option', { value: 'Todo' }, '▶️ Todo (Secuencia completa)'),
                    h('option', { value: '01_evaluacion_manual_pc.sql' }, '1. 01_evaluacion_manual_pc.sql'),
                    h('option', { value: '02_sa_marcacion_ventas_lpdp.sql' }, '2. 02_sa_marcacion_ventas_lpdp.sql'),
                    h('option', { value: '03_sa_calculo_pesos_unpivot.sql' }, '3. 03_sa_calculo_pesos_unpivot.sql'),
                    h('option', { value: '04_sa_ajustes_curva.sql' }, '4. 04_sa_ajustes_curva.sql'),
                    h('option', { value: '04_b_sa_parche_nota_cero.sql' }, '5. 04_b_sa_parche_nota_cero.sql'),
                    h('option', { value: '05_consolidacion_nota_final.sql' }, '6. 05_consolidacion_nota_final.sql')
                  )
                ),

                // Stepper gráfico Calidad
                h('div', { class: 'relative py-6 px-4 bg-slate-900/60 rounded-xl border border-slate-800' },
                  h('div', { class: 'stepper-line-track' }),
                  h('div', {
                    class: 'stepper-progress-fill',
                    style: { width: `${currentPhase > 0 ? (currentPhase - 1) * 20 + 10 : 0}%` }
                  }),
                  h('div', { class: 'relative z-10 flex justify-between' },
                    ['1. Insight PC', '2. Verint SA', '3. Acción tomada', '4. Scripts SQL', '5. NTD'].map((lbl, idx) => {
                      const stepNum = idx + 1;
                      const isCompleted = currentPhase > stepNum;
                      const isActive = currentPhase === stepNum;
                      return h('div', { key: idx, class: 'flex flex-col items-center' },
                        h('div', {
                          class: `w-10 h-10 rounded-full flex items-center justify-center font-bold text-xs font-display transition-all ${
                            isCompleted
                              ? 'bg-emerald-500 text-white border-2 border-emerald-400 shadow-md shadow-emerald-950'
                              : isActive
                              ? 'bg-blue-600 text-white border-2 border-blue-400 shadow-lg shadow-blue-500/50 animate-pulse'
                              : 'bg-slate-800 text-slate-400 border-2 border-slate-700'
                          }`
                        }, isCompleted ? '✔' : stepNum),
                        h('span', { class: `text-[11px] font-semibold mt-2 ${isActive ? 'text-blue-400 font-bold' : 'text-slate-400'}` }, lbl)
                      );
                    })
                  )
                )
              )
            : h('div', { class: 'p-4 bg-blue-950/40 border border-blue-800/60 rounded-xl space-y-3 text-xs' },
                h('p', { class: 'font-bold text-blue-300 font-display' }, '🔒 Scripts de Cierre Mensual:'),
                h('div', { class: 'grid grid-cols-1 md:grid-cols-3 gap-3' },
                  h('label', { class: 'flex items-center gap-3 p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-200 cursor-pointer' },
                    h('input', {
                      type: 'checkbox',
                      checked: cierreScripts.s1,
                      disabled: isRunning,
                      onChange: (e) => setCierreScripts({ ...cierreScripts, s1: e.target.checked }),
                      class: 'accent-blue-500 rounded w-4 h-4'
                    }),
                    h('div', null,
                      h('span', { class: 'font-bold text-white block' }, '1. 01_auditoria_y_cierre.sql'),
                      h('span', { class: 'text-slate-400 text-[11px]' }, 'Consolidado Gerencial & Jerarquías')
                    )
                  ),
                  h('label', { class: 'flex items-center gap-3 p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-200 cursor-pointer' },
                    h('input', {
                      type: 'checkbox',
                      checked: cierreScripts.s2,
                      disabled: isRunning,
                      onChange: (e) => setCierreScripts({ ...cierreScripts, s2: e.target.checked }),
                      class: 'accent-blue-500 rounded w-4 h-4'
                    }),
                    h('div', null,
                      h('span', { class: 'font-bold text-white block' }, '2. 02_kri_resumen_total.sql'),
                      h('span', { class: 'text-slate-400 text-[11px]' }, 'Resumen de Métricas KRI')
                    )
                  ),
                  h('label', { class: 'flex items-center gap-3 p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-200 cursor-pointer' },
                    h('input', {
                      type: 'checkbox',
                      checked: cierreScripts.s3,
                      disabled: isRunning,
                      onChange: (e) => setCierreScripts({ ...cierreScripts, s3: e.target.checked }),
                      class: 'accent-blue-500 rounded w-4 h-4'
                    }),
                    h('div', null,
                      h('span', { class: 'font-bold text-white block' }, '3. 03_consolidado_notas_cierre.sql'),
                      h('span', { class: 'text-slate-400 text-[11px]' }, 'Consolidado Notas Cierre')
                    )
                  )
                )
              ),

          h('button', {
            onClick: handleRunCalidad,
            disabled: isRunning,
            class: `w-full py-3.5 rounded-xl font-bold text-sm shadow-lg font-display ${
              isRunning
                ? 'opacity-50 cursor-not-allowed btn-secondary-ib'
                : soloCierre
                ? 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white border border-blue-400/30'
                : 'btn-primary-ib'
            }`
          }, isRunning ? '⏳ Ejecutando...' : (soloCierre ? '🔒 Iniciar Cierre Mensual' : '🚀 Iniciar Orquestación de Calidad'))
        ),

        // WebSocket Live Events Console
        h('div', { class: 'ib-card rounded-2xl p-5 flex flex-col min-h-[300px] shrink-0' },
          h('div', { class: 'flex items-center justify-between pb-3 border-b border-slate-800 mb-3' },
            h('div', { class: 'flex items-center gap-3' },
              h('span', { class: 'w-3 h-3 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500 animate-pulse' }),
              h('h3', { class: 'text-xs font-bold text-white uppercase tracking-wider font-display' }, 'Consola de Eventos en Vivo'),
              h('span', { class: 'text-[11px] font-mono-code px-2 py-0.5 rounded-full bg-slate-800 text-slate-400' },
                `${filteredLogs.length} eventos`
              )
            ),
            h('div', { class: 'flex items-center gap-3' },
              h('div', { class: 'flex bg-slate-900 rounded-lg p-0.5 border border-slate-800 text-[11px] font-mono-code' },
                ['all', 'info', 'success', 'warning', 'error'].map((f) =>
                  h('button', {
                    key: f,
                    onClick: () => setLogFilter(f),
                    class: `px-2 py-0.5 rounded transition uppercase ${
                      logFilter === f ? 'bg-emerald-600 text-white font-bold' : 'text-slate-400 hover:text-slate-200'
                    }`
                  }, f)
                )
              ),
              h('button', {
                onClick: () => setLogs([]),
                class: 'text-xs text-slate-400 hover:text-white px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 transition border border-slate-700'
              }, 'Limpiar Consola')
            )
          ),

          h('div', {
            ref: logConsoleRef,
            'aria-live': 'polite',
            class: 'flex-1 bg-slate-950/80 border border-slate-800/80 rounded-xl p-4 font-mono-code text-xs overflow-y-auto space-y-1.5 max-h-[350px]'
          },
            filteredLogs.length === 0
              ? h('div', { class: 'text-slate-600 text-center py-10 font-sans text-xs' }, 'En espera de eventos de ejecución en tiempo real...')
              : filteredLogs.map((log, index) =>
                  h('div', { key: index, class: 'flex items-start gap-2.5 leading-relaxed' },
                    h('span', { class: 'text-slate-500 shrink-0 select-none' }, `[${log.time}]`),
                    h('span', {
                      class:
                        log.type === 'error'
                          ? 'text-red-400 font-bold'
                          : log.type === 'warning'
                          ? 'text-amber-300'
                          : log.type === 'success'
                          ? 'text-emerald-400 font-bold'
                          : 'text-slate-300'
                    }, log.text)
                  )
                )
          )
        )
      )
    )
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(h(App));
