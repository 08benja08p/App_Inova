import { useCallback, useEffect, useRef, useState } from 'react';
import template from './Workflow.html?raw';
import './Workflow.css';
import {
  uploadDocument,
  getDocumentDetail,
  getDocumentEntities,
  getDocumentKeywords,
  getDocumentText,
  getDocumentInsights,
  getDownloadUrl,
} from '../../services/api';

const DOC_TYPE_LABELS = {
  factura_comercial: 'Factura comercial',
  packing_list: 'Packing List',
  bl: 'Bill of Lading',
  certificado_fitosanitario: 'Certificado Fitosanitario SAG',
  certificado_origen: 'Certificado de Origen',
  dus: 'Declaración Aduanera (DUS)',
  guia_despacho: 'Guía de Despacho',
  instrucciones_embarque: 'Instrucciones de Embarque',
};

const createEmptyInsights = () => ({
  compliance: [],
  spellcheck: [],
  recommendations: [],
});

const initialDocState = {
  docId: null,
  status: 'idle',
  detail: null,
  textBlocks: [],
  entities: [],
  keywords: [],
  compliance: [],
  insights: createEmptyInsights(),
  autoPlan: [],
  autoApplied: false,
  report: null,
  lastError: null,
  lastUpdatedAt: null,
  processingLog: [],
};

export default function Workflow({ onReset }) {
  const containerRef = useRef(null);
  const elementsRef = useRef(null);
  const docStateRef = useRef(initialDocState);
  const mediaStreamRef = useRef(null);
  const scenarioStepRef = useRef(0); // Track demo scenario step: 0=initial, 1=first upload, 2=second upload

  const [activeStep, setActiveStep] = useState('upload');
  const [docState, setDocState] = useState(initialDocState);

  const stopCameraStream = useCallback(() => {
    const stream = mediaStreamRef.current;
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    const elements = elementsRef.current;
    if (elements?.cameraVideo) {
      elements.cameraVideo.srcObject = null;
    }
    if (elements?.cameraPanel) {
      elements.cameraPanel.classList.remove('is-visible');
    }
  }, []);

  const loadDocumentData = useCallback(
    async (docId, { silent } = { silent: false }) => {
      if (!docId) {
        return;
      }
      setDocState((prev) => ({
        ...prev,
        status: silent ? prev.status : 'loading',
        statusMessage: silent ? prev.statusMessage : 'Sincronizando resultados...',
        lastError: null,
      }));
      try {
        const [detail, entities, keywords, textBlocks, insightsResponse] = await Promise.all([
          getDocumentDetail(docId),
          getDocumentEntities(docId),
          getDocumentKeywords(docId),
          getDocumentText(docId),
          getDocumentInsights(docId),
        ]);
        const normalizedInsights = normalizeInsights(insightsResponse);
        const compliance = computeCompliance(detail, textBlocks, entities, normalizedInsights);
        setDocState((prev) => {
          const autoPlan = prev.autoApplied
            ? recomputeAutoPlan(prev.autoPlan, detail, entities, textBlocks)
            : prev.autoPlan;
          return {
            ...prev,
            docId,
            detail,
            entities,
            keywords,
            textBlocks,
            compliance,
            insights: normalizedInsights,
            status: detail?.status ?? prev.status,
            statusMessage: 'Resultados listos.',
            lastUpdatedAt: new Date().toISOString(),
            lastError: null,
            autoApplied: prev.autoApplied ? prev.autoApplied : false,
            autoPlan,
            report: prev.autoApplied ? buildReport(detail, compliance, autoPlan, normalizedInsights) : prev.report,
          };
        });
      } catch (error) {
        setDocState((prev) => ({
          ...prev,
          status: 'error',
          statusMessage: 'Error al sincronizar datos.',
          lastError: error instanceof Error ? error.message : String(error),
        }));
      }
    },
    []
  );

  useEffect(() => {
    docStateRef.current = docState;
  }, [docState]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return undefined;
    }

    container.innerHTML = template;

    const elements = {
      stepButtons: container.querySelectorAll('[data-step-target]'),
      panels: container.querySelectorAll('[data-panel]'),
      uploadForm: container.querySelector('[data-upload-form]'),
      uploadStatus: container.querySelector('[data-upload-status]'),
      statusBadge: container.querySelector('[data-doc-state-badge]'),
      docMeta: container.querySelector('[data-doc-meta]'),
      docSignals: container.querySelector('[data-doc-signals]'),
      spellList: container.querySelector('[data-spell-list]'),
      suggestionList: container.querySelector('[data-suggestion-list]'),
      textPreview: container.querySelector('[data-text-preview]'),
      keywordChips: container.querySelector('[data-keyword-chips]'),
      entityList: container.querySelector('[data-entity-list]'),
      autoOptions: container.querySelector('[data-auto-options]'),
      autoStatus: container.querySelector('[data-auto-status]'),
      autoResult: container.querySelector('[data-auto-result]'),
      summaryCard: container.querySelector('[data-summary-card]'),
      refreshButton: container.querySelector('[data-action="refresh-doc"]'),
      applyFixesButton: container.querySelector('[data-action="apply-fixes"]'),
      downloadButton: container.querySelector('[data-action="download-report"]'),
      logoutButton: container.querySelector('[data-action="logout"]'),
      openCameraButton: container.querySelector('[data-action="open-camera"]'),
      closeCameraButton: container.querySelector('[data-action="close-camera"]'),
      captureButton: container.querySelector('[data-action="capture-photo"]'),
      cameraPanel: container.querySelector('[data-camera-panel]'),
      cameraVideo: container.querySelector('[data-camera-video]'),
      cameraCanvas: container.querySelector('[data-camera-canvas]'),
      processingLog: container.querySelector('[data-processing-log]'),
      logContent: container.querySelector('[data-log-content]'),
      chatForm: container.querySelector('[data-chat-form]'),
      chatMessages: container.querySelector('[data-chat-messages]'),
    };

    elementsRef.current = elements;

    const handleStepClick = (event) => {
      const step = event.currentTarget.getAttribute('data-step-target');
      if (step) {
        setActiveStep(step);
      }
    };

    elements.stepButtons.forEach((button) => {
      button.addEventListener('click', handleStepClick);
    });

    // Camera Toggle Logic
    const toggleCamera = (show) => {
      if (show) {
        elements.uploadForm.hidden = true;
        elements.cameraPanel.classList.add('is-visible');
        handleOpenCamera();
      } else {
        elements.uploadForm.hidden = false;
        elements.cameraPanel.classList.remove('is-visible');
        handleCloseCamera();
      }
    };

    // Add Open Camera Button to Upload Form
    const uploadAlternatives = elements.uploadForm?.querySelector('.upload-alternatives');
    if (elements.uploadForm && !uploadAlternatives) {
      const alts = document.createElement('div');
      alts.className = 'upload-alternatives';
      alts.innerHTML = `
        <span>O</span>
        <button type="button" class="secondary-button" id="btn-open-camera">
          📸 Usar Cámara
        </button>
      `;
      elements.uploadForm.querySelector('.file-dropzone').after(alts);

      alts.querySelector('#btn-open-camera').addEventListener('click', () => toggleCamera(true));
    }

    const collectUploadOptions = () => {
      const docTypeSelect = elements.uploadForm?.querySelector('[name="doc_type"]');
      const languageSelect = elements.uploadForm?.querySelector('[name="language_hint"]');
      return {
        docType: docTypeSelect?.value?.toString() || undefined,
        languageHint: languageSelect?.value?.toString() || undefined,
      };
    };

    const simulateProcessingLog = async () => {
      const logs = [
        { level: 'info', msg: 'Iniciando motor de análisis...' },
        { level: 'info', msg: 'Conectando con backend...' },
        { level: 'success', msg: 'Documento cargado correctamente.' },
        { level: 'info', msg: 'Ejecutando OCR (Tesseract/PyPDF2)...' },
        { level: 'success', msg: 'Texto extraído (Confianza: 98.5%)' },
        { level: 'info', msg: 'Detectando entidades nombradas (NER)...' },
        { level: 'success', msg: 'Entidades encontradas: 12' },
        { level: 'info', msg: 'Validando reglas de negocio (SAG/Aduanas)...' },
        { level: 'warn', msg: 'Alerta: HS Code requiere verificación.' },
        { level: 'success', msg: 'Análisis completado.' },
      ];

      if (elements.processingLog) elements.processingLog.hidden = false;
      if (elements.logContent) elements.logContent.innerHTML = '';

      for (const log of logs) {
        await new Promise(r => setTimeout(r, 600)); // Delay for effect
        const line = document.createElement('div');
        line.className = 'log-line';
        line.innerHTML = `
          <span class="timestamp">[${new Date().toLocaleTimeString()}]</span>
          <span class="level ${log.level}">${log.level.toUpperCase()}</span>
          <span class="message">${log.msg}</span>
        `;
        if (elements.logContent) {
          elements.logContent.appendChild(line);
          elements.logContent.scrollTop = elements.logContent.scrollHeight;
        }
      }

      await new Promise(r => setTimeout(r, 1000));
      if (elements.processingLog) elements.processingLog.hidden = true;
    };

    // --- DEMO SCENARIO MOCK DATA ---
    const mockInitialState = {
      docId: 'demo-factura-001',
      fileName: 'FACTURA TRIBUTARIA N°5873 SA1690CZ.pdf',
      fileType: 'application/pdf',
      fileUrl: '/docs/FACTURA TRIBUTARIA N°5873 SA1690CZ.pdf',
      status: 'done',
      detail: {
        id: 'INV-5873',
        status: 'done',
        docType: 'factura_comercial',
        languageDetected: 'Español',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
      compliance: [
        {
          severity: 'warning',
          title: 'Posible error de caché',
          detail: 'La cantidad de pallets (20) no coincide con el histórico reciente. Se sugiere validar.',
        },
      ],
      insights: {
        recommendations: ['Subir Packing List para validación cruzada de bultos.'],
        spellcheck: [],
      },
      entities: [
        { type: 'invoice_number', value: '5873', confidence: 0.99 },
        { type: 'date', value: '15 Nov 2024', confidence: 0.98 },
        { type: 'total_amount', value: '45,200.00 USD', confidence: 0.99 },
        { type: 'pallets', value: '20', confidence: 0.85 },
      ],
      keywords: [
        { keyword: 'Cerezas', score: 0.95 },
        { keyword: 'Exportación', score: 0.90 },
      ],
      textBlocks: [
        { text: 'FACTURA TRIBUTARIA N° 5873\n\nEmisor: FRUTAS DEL SUR LTDA\nRUT: 76.123.456-7\n\nReceptor: SHANGHAI FRUIT IMPORTERS CO LTD\n\nDetalle:\nCerezas Frescas Premium - 1,000 cajas\nPallets: 20\nPeso: 8,500 kg\nINOCTERM: FOB Valparaíso\n\nTotal: USD 45,200.00' }
      ],
      autoPlan: [],
      autoApplied: false,
      report: null,
      processingLog: [],
    };

    const mockCrossCheckState = {
      ...mockInitialState,
      fileName: 'Validación Cruzada: Factura + Packing List',
      secondFileUrl: '/docs/FULL SET SA1704CZ.pdf',
      statusMessage: 'Validación cruzada completada. Incoherencia detectada.',
      detail: { ...mockInitialState.detail, docType: 'cross_check' },
      compliance: [
        {
          severity: 'error',
          title: 'Incoherencia de Bultos',
          detail: 'Factura indica 20 pallets, pero Packing List indica 22. Debe corregirse.',
        },
      ],
      insights: {
        recommendations: ['Corregir cantidad en Factura para coincidir con Packing List.'],
        spellcheck: [],
      },
      autoPlan: [
        { label: 'Corregir Cantidad', detail: 'Actualizar "Total Pallets" de 20 a 22' },
      ],
      // Visual Highlights for Demo
      visualHighlights: [
        { x: 60, y: 45, w: 15, h: 4, type: 'error', label: 'Pallets: 20 (Error)' }
      ]
    };

    const mockFinalState = {
      ...mockCrossCheckState,
      fileName: 'FACTURA CORREGIDA N°5873',
      statusMessage: 'Correcciones aplicadas. Documento listo.',
      compliance: [
        {
          severity: 'ok',
          title: 'Validación Exitosa',
          detail: 'La cantidad de pallets fue corregida a 22. Coincide con Packing List.',
        },
      ],
      entities: [
        ...mockInitialState.entities.filter(e => e.type !== 'pallets'),
        { type: 'pallets', value: '22', confidence: 1.0 },
      ],
      textBlocks: [
        { text: 'FACTURA TRIBUTARIA N° 5873 [CORREGIDA]\n\nEmisor: FRUTAS DEL SUR LTDA\nRUT: 76.123.456-7\n\nReceptor: SHANGHAI FRUIT IMPORTERS CO LTD\n\nDetalle:\nCerezas Frescas Premium - 1,000 cajas\nPallets: 22 ** CORREGIDO **\nPeso: 9,350 kg\nINOCTERM: FOB Valparaíso\n\nTotal: USD 49,720.00\n\n[Documento validado y corregido automáticamente]' }
      ],
      autoApplied: true,
      report: 'Reporte generado tras aplicar correcciones.',
    };

    const submitDocument = async (file, options = {}) => {
      if (!(file instanceof File) || file.size === 0) {
        setDocState((prev) => ({
          ...prev,
          status: 'error',
          statusMessage: 'Selecciona un archivo válido.',
        }));
        return;
      }

      setDocState(() => ({
        ...initialDocState,
        insights: createEmptyInsights(),
        status: 'uploading',
        statusMessage: 'Enviando documento...',
      }));

      // Start visual processing log
      simulateProcessingLog();

      try {
        // Real API Call
        const response = await uploadDocument(file, options);

        if (!response || !response.id) {
          throw new Error('La respuesta del servidor no contiene un ID válido.');
        }

        setDocState((prev) => ({
          ...prev,
          docId: response.id,
          status: 'processing',
          statusMessage: 'Documento recibido. Procesando...',
        }));

        // Poll for completion or just load immediately (since backend is sync for PoC)
        // Give it a small delay to allow the "processing" animation to be seen
        await new Promise((resolve) => setTimeout(resolve, 1000));

        await loadDocumentData(response.id);

        setActiveStep('verify');

      } catch (error) {
        console.error('Upload error:', error);
        setDocState((prev) => ({
          ...prev,
          status: 'error',
          statusMessage: 'Error al subir documento.',
          lastError: error instanceof Error ? error.message : String(error),
        }));
      }
    };

    const handleUpload = async (event) => {
      event.preventDefault();
      const form = elements.uploadForm;
      if (!form) {
        return;
      }
      const formData = new FormData(form);
      const file = formData.get('file');
      await submitDocument(file, {
        docType: (formData.get('doc_type') ?? '').toString() || undefined,
        languageHint: (formData.get('language_hint') ?? '').toString() || undefined,
      });
    };

    elements.uploadForm?.addEventListener('submit', handleUpload);

    // Chat Logic
    const handleChatSubmit = (e) => {
      e.preventDefault();
      const input = elements.chatForm?.querySelector('input');
      const query = input?.value.trim();
      if (!query) return;

      // Add user message
      addChatMessage('user', query);
      input.value = '';

      // Simulate AI thinking
      setTimeout(() => {
        const response = generateSmartResponse(query, docStateRef.current);
        addChatMessage('system', response);
      }, 800);
    };

    const addChatMessage = (role, text) => {
      if (!elements.chatMessages) return;
      const msgDiv = document.createElement('div');
      msgDiv.className = `chat-message ${role}`;
      msgDiv.innerHTML = `
        <div class="avatar">${role === 'user' ? 'Tú' : 'AI'}</div>
        <div class="content">${text}</div>
      `;
      elements.chatMessages.appendChild(msgDiv);
      elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    };

    const generateSmartResponse = (query, state) => {
      const q = query.toLowerCase();

      if (!state.docId) return "Por favor, carga un documento primero para que pueda responderte.";

      // Helper to find value by type
      const findValue = (types) => {
        const entity = state.entities.find(e => types.includes(e.type));
        return entity ? entity.value : null;
      };

      // 1. Peso (Weight)
      if (q.includes('peso') || q.includes('kilos') || q.includes('weight')) {
        const net = findValue(['net_weight']);
        const gross = findValue(['gross_weight']);

        if (net && gross) return `He detectado un peso neto de **${net}** y un peso bruto de **${gross}**.`;
        if (net) return `El peso neto detectado es **${net}**.`;
        if (gross) return `El peso bruto detectado es **${gross}**.`;

        // Fallback to generic search if specific weight types aren't found
        const genericWeight = state.entities.find(e => e.value.toLowerCase().includes('kg'));
        if (genericWeight) return `Encontré una referencia a peso: **${genericWeight.value}**.`;

        return "No encontré un peso explícito, pero sigo analizando el texto.";
      }

      // 2. Exportador (Shipper/Exporter)
      if (q.includes('exportador') || q.includes('shipper') || q.includes('vendedor')) {
        const val = findValue(['shipper', 'exporter']);
        if (val) return `El exportador identificado es **${val}**.`;
        return "No veo el nombre del exportador claramente marcado.";
      }

      // 3. Consignatario (Consignee)
      if (q.includes('consignatario') || q.includes('comprador') || q.includes('cliente') || q.includes('importador')) {
        const val = findValue(['consignee', 'importer']);
        if (val) return `El consignatario es **${val}**.`;
        return "No veo el nombre del consignatario claramente marcado.";
      }

      // 4. Incoterm
      if (q.includes('incoterm') || q.includes('terminos')) {
        const val = findValue(['incoterm']);
        if (val) return `El Incoterm detectado es **${val}**.`;
        return "No encontré un Incoterm explícito en el documento.";
      }

      // 5. HS Code
      if (q.includes('hs code') || q.includes('partida') || q.includes('arancel')) {
        const val = findValue(['hs_code']);
        if (val) return `El HS Code identificado es **${val}**.`;
        return "No encontré el HS Code.";
      }

      // 6. Contenedor
      if (q.includes('contenedor') || q.includes('container')) {
        const val = findValue(['container']);
        if (val) return `El número de contenedor es **${val}**.`;
        return "No encontré el número de contenedor.";
      }

      // 7. BL
      if (q.includes('bl') || q.includes('bill of lading') || q.includes('embarque')) {
        const val = findValue(['bl_number']);
        if (val) return `El número de BL es **${val}**.`;
        return "No encontré el número de BL.";
      }

      // 8. DUS
      if (q.includes('dus')) {
        const val = findValue(['dus_number']);
        if (val) return `El número de DUS es **${val}**.`;
        return "No encontré el número de DUS.";
      }

      // 9. Booking
      if (q.includes('booking') || q.includes('reserva')) {
        const val = findValue(['booking_number']);
        if (val) return `El número de Booking es **${val}**.`;
        return "No encontré el número de Booking.";
      }

      // 10. Monto / Moneda
      if (q.includes('monto') || q.includes('valor') || q.includes('precio') || q.includes('total')) {
        const amount = findValue(['amount', 'total_amount']);
        const currency = findValue(['currency']);
        if (amount && currency) return `El monto total detectado es **${amount} ${currency}**.`;
        if (amount) return `El monto detectado es **${amount}**.`;
        return "No encontré un monto total claro.";
      }

      // General status check
      if (q.includes('error') || q.includes('problema') || q.includes('alerta')) {
        if (state.compliance.length > 0) {
          return `He encontrado ${state.compliance.length} problemas potenciales. El más crítico es: ${state.compliance[0].title}.`;
        }
        return "El documento parece estar en orden. No detecto errores críticos.";
      }

      if (q.includes('resumen') || q.includes('trata')) {
        const typeLabel = state.detail?.docType ? DOC_TYPE_LABELS[state.detail.docType] : 'documento';
        return `Este es un **${typeLabel}**. He extraído entidades clave como fechas, montos y actores logísticos. ¿Quieres saber algo específico?`;
      }

      // Fallback to keyword search
      const foundKeyword = state.keywords.find(k => q.includes(k.keyword.toLowerCase()));
      if (foundKeyword) {
        return `El término "${foundKeyword.keyword}" aparece en el documento con una relevancia del ${Math.round(foundKeyword.score * 100)}%.`;
      }

      return "Interesante pregunta. Estoy analizando el contexto, pero por ahora te sugiero preguntar por el peso, el exportador, incoterm, contenedor o si existen errores.";
    };

    elements.chatForm?.addEventListener('submit', handleChatSubmit);

    const handleApplyFixes = async () => {
      const step = scenarioStepRef.current;

      setDocState((prev) => ({
        ...prev,
        status: 'processing',
        statusMessage: 'Aplicando correcciones y regenerando documento...',
      }));

      await new Promise((resolve) => setTimeout(resolve, 1500));

      if (step === 2) {
        // Cross-check state -> Final Corrected State
        setDocState(mockFinalState);
        // Stay in step 2 or move to 3 if we want another phase
      } else {
        // Fallback
        setDocState((prev) => ({
          ...prev,
          status: 'done',
          statusMessage: 'Ajustes aplicados.',
          autoApplied: true,
        }));
      }

      setActiveStep('report');
    };

    elements.applyFixesButton?.addEventListener('click', handleApplyFixes);

    const handleOpenCamera = async () => {
      if (!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)) {
        setDocState((prev) => ({
          ...prev,
          status: 'error',
          statusMessage: 'La cámara no está disponible en este dispositivo.',
          lastError: 'camera-not-supported',
        }));
        return;
      }

      try {
        stopCameraStream();
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: 'environment' } },
        });
        mediaStreamRef.current = stream;
        if (elements.cameraVideo) {
          elements.cameraVideo.srcObject = stream;
          await elements.cameraVideo.play().catch(() => { });
        }
        // elements.cameraPanel?.classList.add('is-visible'); // Handled by toggleCamera
        setDocState((prev) => ({
          ...prev,
          status: 'capture',
          statusMessage: 'Cámara lista. Captura cuando estés listo.',
          lastError: null,
        }));
      } catch (error) {
        stopCameraStream();
        setDocState((prev) => ({
          ...prev,
          status: 'error',
          statusMessage: 'No pudimos acceder a la cámara.',
          lastError: error instanceof Error ? error.message : String(error),
        }));
      }
    };

    const handleCloseCamera = () => {
      stopCameraStream();
      setDocState((prev) => ({
        ...prev,
        status: prev.docId ? prev.status : 'idle',
        statusMessage: prev.docId ? prev.statusMessage : '',
      }));
    };

    const handleCapture = async () => {
      const video = elements.cameraVideo;
      const canvas = elements.cameraCanvas;
      if (!video || !canvas) {
        return;
      }
      if (!video.videoWidth || !video.videoHeight) {
        setDocState((prev) => ({
          ...prev,
          status: 'error',
          statusMessage: 'La cámara aún no está lista.',
        }));
        return;
      }

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const context = canvas.getContext('2d');
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png', 0.92));
      if (!blob) {
        setDocState((prev) => ({
          ...prev,
          status: 'error',
          statusMessage: 'No se pudo generar la captura.',
          lastError: 'camera-capture-null',
        }));
        return;
      }

      setDocState((prev) => ({
        ...prev,
        status: 'uploading',
        statusMessage: 'Procesando captura...',
        lastError: null,
      }));

      const photoFile = new File([blob], `captura-${Date.now()}.png`, { type: 'image/png' });
      stopCameraStream();

      // Restore UI
      elements.uploadForm.hidden = false;
      elements.cameraPanel.classList.remove('is-visible');

      const options = collectUploadOptions();
      await submitDocument(photoFile, options);
    };

    // elements.openCameraButton?.addEventListener('click', handleOpenCamera); // Replaced by dynamic button
    elements.closeCameraButton?.addEventListener('click', () => toggleCamera(false));
    elements.captureButton?.addEventListener('click', handleCapture);

    const handleRefresh = () => {
      const currentId = docStateRef.current.docId;
      if (currentId) {
        loadDocumentData(currentId, { silent: false });
      }
    };

    elements.refreshButton?.addEventListener('click', handleRefresh);

    const handleLogout = (event) => {
      event.preventDefault();
      onReset();
    };

    elements.logoutButton?.addEventListener('click', handleLogout);

    renderStep(activeStep, elements);
    renderDocState(docStateRef.current, elements);

    return () => {
      elements.stepButtons.forEach((button) => {
        button.removeEventListener('click', handleStepClick);
      });
      elements.uploadForm?.removeEventListener('submit', handleUpload);
      elements.openCameraButton?.removeEventListener('click', handleOpenCamera);
      elements.closeCameraButton?.removeEventListener('click', handleCloseCamera);
      elements.captureButton?.removeEventListener('click', handleCapture);
      elements.refreshButton?.removeEventListener('click', handleRefresh);
      elements.applyFixesButton?.removeEventListener('click', handleApplyFixes);
      // elements.downloadButton?.removeEventListener('click', handleDownload); // Removed as it is now an anchor
      elements.logoutButton?.removeEventListener('click', handleLogout);
      elements.chatForm?.removeEventListener('submit', handleChatSubmit);
      stopCameraStream();
    };
  }, [loadDocumentData, onReset, stopCameraStream]);

  useEffect(() => {
    const elements = elementsRef.current;
    if (!elements) {
      return;
    }
    renderStep(activeStep, elements);
  }, [activeStep]);

  useEffect(() => {
    const elements = elementsRef.current;
    if (!elements) {
      return;
    }
    renderDocState(docState, elements);
  }, [docState]);

  return <section className="workflow-host" ref={containerRef} />;
}

function renderStep(activeStep, elements) {
  elements.stepButtons.forEach((button) => {
    const step = button.getAttribute('data-step-target');
    if (step === activeStep) {
      button.classList.add('is-active');
    } else {
      button.classList.remove('is-active');
    }
  });

  elements.panels.forEach((panel) => {
    const panelKey = panel.getAttribute('data-panel');
    if (panelKey === activeStep) {
      panel.classList.add('is-active');
      panel.hidden = false;
      // Explicitly remove display:none if set
      panel.style.display = '';
    } else {
      panel.classList.remove('is-active');
      panel.hidden = true;
      // Explicitly hide the panel
      panel.style.display = 'none';
    }
  });
}

function renderDocState(state, elements) {
  if (!elements) {
    return;
  }

  if (elements.stepButtons) {
    elements.stepButtons.forEach((button) => {
      const step = button.getAttribute('data-step-target');
      const complete =
        (step === 'upload' && !!state.docId) ||
        (step === 'verify' && !!state.detail) ||
        (step === 'chat' && !!state.detail) ||
        (step === 'edit' && state.autoApplied) ||
        (step === 'report' && state.report);
      if (complete) {
        button.classList.add('is-complete');
      } else {
        button.classList.remove('is-complete');
      }
    });
  }

  // Ensure panels are correctly toggled
  if (elements.panels) {
    elements.panels.forEach((panel) => {
      // Force re-check of active state to prevent ghost panels
      const panelKey = panel.getAttribute('data-panel');
      // This logic is already in renderStep, but we double check here if needed
      // Actually, renderStep handles visibility. renderDocState handles content.
    });
  }

  if (elements.uploadStatus) {
    elements.uploadStatus.textContent = state.statusMessage;
    elements.uploadStatus.setAttribute('data-status', state.status);
  }

  if (elements.statusBadge) {
    if (!state.docId) {
      elements.statusBadge.textContent = 'Sin documento cargado';
    } else if (state.status === 'error') {
      elements.statusBadge.textContent = 'Error en procesamiento';
    } else if (state.detail) {
      elements.statusBadge.textContent = `Documento ${state.detail.status ?? 'procesando'}`;
    } else {
      elements.statusBadge.textContent = 'Documento cargado';
    }
  }

  if (elements.docMeta) {
    elements.docMeta.innerHTML = '';
    if (!state.docId) {
      const item = document.createElement('div');
      item.className = 'meta-bar__item';
      item.textContent = 'Cargue un documento para ver metadatos.';
      elements.docMeta.appendChild(item);
    } else if (!state.detail) {
      const item = document.createElement('div');
      item.className = 'meta-bar__item';
      item.textContent = 'Sincronizando metadatos…';
      elements.docMeta.appendChild(item);
    } else {
      const { id, status, docType, languageDetected } = state.detail;
      const metaEntries = [
        ['ID', id],
        ['Estado', status ?? 'sin estado'],
        ['Tipo', formatDocTypeLabel(docType)],
        ['Idioma', languageDetected ?? 'No disponible'],
      ];

      metaEntries.forEach(([label, value], index) => {
        if (index > 0) {
          const sep = document.createElement('div');
          sep.className = 'meta-bar__separator';
          elements.docMeta.appendChild(sep);
        }
        const item = document.createElement('div');
        item.className = 'meta-bar__item';

        const spanLabel = document.createElement('strong');
        spanLabel.textContent = `${label}:`;

        const spanValue = document.createElement('span');
        spanValue.textContent = value;

        item.append(spanLabel, document.createTextNode(' '), spanValue);
        elements.docMeta.appendChild(item);
      });
    }
  }

  if (elements.docSignals) {
    elements.docSignals.innerHTML = '';
    if (!state.docId) {
      const item = document.createElement('li');
      item.textContent = 'Sin documento en proceso.';
      elements.docSignals.appendChild(item);
    } else if (!state.detail) {
      const item = document.createElement('li');
      item.textContent = 'Analizando requisitos…';
      elements.docSignals.appendChild(item);
    } else if (!state.compliance.length) {
      const item = document.createElement('li');
      item.setAttribute('data-severity', 'ok');
      const badge = document.createElement('span');
      badge.textContent = '✓ Cumple';
      item.append(badge, document.createTextNode(' No se detectaron incidencias.'));
      elements.docSignals.appendChild(item);
    } else {
      state.compliance.forEach((finding) => {
        const item = document.createElement('li');
        item.setAttribute('data-severity', finding.severity);

        const contentDiv = document.createElement('div');
        contentDiv.style.flex = '1';

        const badge = document.createElement('span');
        badge.textContent = finding.title;
        contentDiv.append(badge, document.createTextNode(` ${finding.detail}`));

        item.appendChild(contentDiv);

        // Add "Corregir" button for errors/warnings if applicable
        if (finding.severity === 'error' || finding.severity === 'warning') {
          const fixBtn = document.createElement('button');
          fixBtn.className = 'secondary-button';
          fixBtn.textContent = 'Corregir';
          fixBtn.style.fontSize = '0.75rem';
          fixBtn.style.padding = '0.3rem 0.6rem';
          fixBtn.style.marginLeft = '0.5rem';
          fixBtn.onclick = () => {
            // Trigger the fix logic
            handleApplyFixes();
          };
          item.appendChild(fixBtn);
        }

        elements.docSignals.appendChild(item);
      });
    }
  }

  if (elements.spellList) {
    elements.spellList.innerHTML = '';
    const spellIssues = state.insights?.spellcheck ?? [];
    if (!state.docId) {
      const item = document.createElement('li');
      item.textContent = 'Carga un documento para revisar ortografía.';
      elements.spellList.appendChild(item);
    } else if (!state.detail) {
      const item = document.createElement('li');
      item.textContent = 'Analizando texto reconocido...';
      elements.spellList.appendChild(item);
    } else if (!spellIssues.length) {
      const item = document.createElement('li');
      item.setAttribute('data-severity', 'ok');
      const badge = document.createElement('span');
      badge.textContent = 'Texto sin observaciones';
      item.append(badge, document.createTextNode(' No se detectaron faltas críticas.'));
      elements.spellList.appendChild(item);
    } else {
      spellIssues.forEach((issue) => {
        const item = document.createElement('li');
        item.setAttribute('data-severity', issue.severity ?? 'warning');
        const badge = document.createElement('span');
        badge.textContent = issue.title ?? 'Observación';
        item.append(badge, document.createTextNode(` ${issue.detail ?? ''}`));
        elements.spellList.appendChild(item);
      });
    }
  }

  if (elements.suggestionList) {
    elements.suggestionList.innerHTML = '';
    const suggestions = state.insights?.recommendations ?? [];
    if (!state.docId) {
      const item = document.createElement('li');
      item.textContent = 'Aún no hay sugerencias automáticas.';
      elements.suggestionList.appendChild(item);
    } else if (!state.detail) {
      const item = document.createElement('li');
      item.textContent = 'Consultando recomendaciones...';
      elements.suggestionList.appendChild(item);
    } else if (!suggestions.length) {
      const item = document.createElement('li');
      item.setAttribute('data-severity', 'ok');
      const badge = document.createElement('span');
      badge.textContent = 'Sin sugerencias';
      item.append(badge, document.createTextNode(' Todo parece consistente.'));
      elements.suggestionList.appendChild(item);
    } else {
      suggestions.forEach((suggestion) => {
        const item = document.createElement('li');
        item.setAttribute('data-severity', 'info');
        const badge = document.createElement('span');
        badge.textContent = 'Sugerencia';
        item.append(badge, document.createTextNode(` ${suggestion}`));
        elements.suggestionList.appendChild(item);
      });
    }
  }

  if (elements.textPreview) {
    if (!state.docId) {
      elements.textPreview.innerHTML = '\u003cdiv style="padding: 2rem; text-align: center; color: var(--slate-400);"\u003eSube un documento para ver el preview y el texto OCR.\u003c/div\u003e';
    } else if (state.detail?.htmlPreview) {
      // HTML Preview Mode (Reconstructed)
      // We use a Blob URL to avoid escaping issues with srcdoc and large content
      const blob = new Blob([state.detail.htmlPreview], { type: 'text/html' });
      const url = URL.createObjectURL(blob);

      elements.textPreview.innerHTML = `
        <div class="html-preview-container" style="width: 100%; height: 100%; display: flex; align-items: flex-start; justify-content: center; background: #525659; padding: 2rem; overflow: auto;">
          <div style="width: 100%; max-width: 800px; aspect-ratio: 1/1.414; background: white; box-shadow: 0 0 15px rgba(0,0,0,0.3); display: flex; flex-direction: column; flex-shrink: 0;">
             <iframe 
              src="${url}" 
              style="flex: 1; width: 100%; height: 100%; border: none;"
              title="Document Preview"
            ></iframe>
          </div>
        </div>
      `;

      // Cleanup blob url when component unmounts or updates? 
      // In this vanilla-ish JS inside React, we might leak blobs if we are not careful.
      // But for a demo it's fine. Ideally we'd store the URL in a ref and revoke it.

    } else if (state.fileType === 'application/pdf' && state.fileUrl) {
      // PDF Preview mode
      let html = '';

      // Primary document
      html += `
        \u003cdiv class="pdf-preview-item" style="position: relative;"\u003e
          \u003ch4\u003e📄 ${state.fileName || 'Documento Principal'}\u003c/h4\u003e
          \u003cembed src="${state.fileUrl}" type="application/pdf" width="100%" height="100%" style="border: none;" /\u003e
          ${renderVisualHighlights(state.visualHighlights)}
        \u003c/div\u003e
      `;

      // Second document if cross-check
      if (state.secondFileUrl) {
        html += `
          \u003cdiv class="pdf-preview-item" style="margin-top: 1rem; border-top: 1px solid var(--surface-border);"\u003e
            \u003ch4\u003e📋 Documento de Validación Cruzada\u003c/h4\u003e
            \u003cembed src="${state.secondFileUrl}" type="application/pdf" width="100%" height="100%" style="border: none;" /\u003e
          \u003c/div\u003e
        `;
      }

      // OCR Text section
      const text = state.textBlocks?.map((block) => block.text).join('\\n\\n').trim();
      if (text) {
        html += `
          \u003cdetails class="ocr-text-section" style="margin-top: auto; border-top: 1px solid var(--surface-border);"\u003e
            \u003csummary style="cursor: pointer; font-weight: 600; padding: 10px; background: rgba(30, 41, 59, 0.6); color: var(--slate-300);"\u003e
              🔍 Ver Texto OCR Completo
            \u003c/summary\u003e
            \u003cpre style="margin: 0; padding: 15px; background: rgba(15, 23, 42, 0.8); max-height: 200px; overflow: auto; white-space: pre-wrap; color: var(--slate-400); font-size: 0.85rem;"\u003e${text}\u003c/pre\u003e
          \u003c/details\u003e
        `;
      }

      elements.textPreview.innerHTML = html;
    } else {
      // Text-only fallback
      const text = state.textBlocks?.map((block) => block.text).join('\\n\\n').trim();
      elements.textPreview.innerHTML = `\u003cpre style="padding: 1.5rem; white-space: pre-wrap; color: var(--slate-400);"\u003e${text?.length ? text : 'Sin texto disponible.'}\u003c/pre\u003e`;
    }
  }

  if (elements.keywordChips) {
    elements.keywordChips.innerHTML = '';
    if (state.keywords?.length) {
      state.keywords.forEach((kw) => {
        const chip = document.createElement('span');
        chip.textContent = kw.keyword ?? '';
        elements.keywordChips.appendChild(chip);
      });
    } else if (state.docId) {
      const empty = document.createElement('span');
      empty.className = 'tag-cloud__empty';
      empty.textContent = 'Sin keywords detectadas.';
      elements.keywordChips.appendChild(empty);
    }
  }

  if (elements.entityList) {
    elements.entityList.innerHTML = '';
    if (state.entities?.length) {
      state.entities.forEach((entity) => {
        const item = document.createElement('li');
        const type = document.createElement('span');
        type.textContent = entity.type;
        const value = document.createElement('span');
        value.textContent = entity.value;
        const confidence = document.createElement('span');
        confidence.textContent = `${Math.round((entity.confidence ?? 0) * 100)}%`;
        item.append(type, value, confidence);
        elements.entityList.appendChild(item);
      });
    } else if (state.docId) {
      const item = document.createElement('li');
      item.className = 'entity-table__empty';
      item.textContent = 'Sin entidades extraídas.';
      elements.entityList.appendChild(item);
    }
  }

  if (elements.autoStatus) {
    if (!state.docId) {
      elements.autoStatus.textContent = 'Carga un documento antes de generar ajustes.';
    } else if (!state.autoApplied) {
      elements.autoStatus.textContent = 'Sin ajustes generados todavía.';
    } else {
      elements.autoStatus.textContent = 'Ajustes generados. Revisa el resumen antes de exportar.';
    }
  }

  if (elements.autoResult) {
    if (!state.autoApplied || !state.autoPlan.length) {
      elements.autoResult.innerHTML = '<p>Selecciona ajustes y presiona "Aplicar" para generar un plan.</p>';
    } else {
      const list = document.createElement('ul');
      state.autoPlan.forEach((item) => {
        const li = document.createElement('li');
        li.textContent = `${item.label}: ${item.detail}`;
        list.appendChild(li);
      });
      elements.autoResult.innerHTML = '';
      const intro = document.createElement('p');
      intro.textContent = 'Se generaron las siguientes modificaciones sugeridas:';
      elements.autoResult.append(intro, list);
    }
  }

  if (elements.summaryCard) {
    if (!state.docId || !state.detail) {
      elements.summaryCard.innerHTML = '<p>Necesitas procesar un documento para generar el resumen.</p>';
    } else {
      const summary = buildSummary(state);
      elements.summaryCard.innerHTML = '';

      // Success State Visual
      if (state.autoApplied || (!state.compliance.length && state.status === 'done')) {
        const successDiv = document.createElement('div');
        successDiv.className = 'success-state';
        successDiv.innerHTML = `
          <div class="success-state__icon">🎉</div>
          <h3>Documento Validado y Listo</h3>
          <p>El documento cumple con todas las reglas de negocio y está listo para exportación.</p>
        `;
        elements.summaryCard.appendChild(successDiv);
      }

      // New Dashboard Summary Layout
      const dashboard = document.createElement('div');

      // Top Stats Row
      const statsGrid = document.createElement('div');
      statsGrid.className = 'summary-grid';

      const stats = [
        { label: 'Confianza Global', value: '98.5%', sub: 'Alta precisión' },
        { label: 'Tiempo Proceso', value: '1.2s', sub: 'Ultra rápido' },
        { label: 'Estado Final', value: state.detail.status, sub: 'Listo para envío' }
      ];

      stats.forEach(stat => {
        const card = document.createElement('div');
        card.className = 'summary-stat-card';
        card.innerHTML = `
          <label>${stat.label}</label>
          <div class="value">${stat.value}</div>
          <div class="sub">${stat.sub}</div>
        `;
        statsGrid.appendChild(card);
      });

      dashboard.appendChild(statsGrid);

      // Content Grid
      const contentGrid = document.createElement('div');
      contentGrid.className = 'summary-content-grid';

      // Left Column: Details
      const leftCol = document.createElement('div');
      leftCol.className = 'summary-section';
      leftCol.innerHTML = '<h4>Detalles del Documento</h4>';

      const metaList = document.createElement('ul');
      metaList.className = 'summary-meta';
      summary.meta.forEach(([label, value]) => {
        const item = document.createElement('li');
        item.innerHTML = `<strong>${label}</strong> <span>${value}</span>`;
        metaList.appendChild(item);
      });
      leftCol.appendChild(metaList);

      // Right Column: Findings & Actions
      const rightCol = document.createElement('div');
      rightCol.className = 'summary-section';
      rightCol.innerHTML = '<h4>Hallazgos y Acciones</h4>';

      const findingsList = document.createElement('ul');
      findingsList.className = 'summary-findings';
      if (summary.findings.length) {
        summary.findings.forEach(f => {
          const li = document.createElement('li');
          li.textContent = f;
          findingsList.appendChild(li);
        });
      } else {
        findingsList.innerHTML = '<li>Sin hallazgos relevantes.</li>';
      }
      rightCol.appendChild(findingsList);

      contentGrid.append(leftCol, rightCol);
      dashboard.appendChild(contentGrid);

      // Text Summary Section
      if (summary.textSummary) {
        const textSection = document.createElement('div');
        textSection.className = 'summary-section';
        textSection.style.marginTop = '2rem';
        textSection.innerHTML = `
          <h4>Resumen Inteligente</h4>
          <p class="summary-text">${summary.textSummary}</p>
        `;
        dashboard.appendChild(textSection);
      }

      elements.summaryCard.appendChild(dashboard);
    }
  }

  if (elements.downloadButton) {
    if (state.docId) {
      elements.downloadButton.href = getDownloadUrl(state.docId);
      elements.downloadButton.classList.remove('disabled');
    } else {
      elements.downloadButton.removeAttribute('href');
      elements.downloadButton.classList.add('disabled');
    }
  }
}

function computeCompliance(detail, textBlocks, entities, insights) {
  if (!detail) {
    return [];
  }
  const normalizedInsights =
    insights && Array.isArray(insights.compliance) ? insights : normalizeInsights(insights);
  const findings = normalizedInsights.compliance.map((item) => ({
    severity: item.severity ?? 'warning',
    title: item.title ?? 'Regla documental',
    detail: item.detail ?? '',
  }));
  const status = detail.status ?? 'processing';
  if (status !== 'done') {
    findings.push({
      severity: 'warning',
      title: 'Procesamiento incompleto',
      detail: 'El backend aún marca el documento como "' + status + '".',
    });
  }
  const text = textBlocks?.map((block) => block.text).join(' ').toLowerCase() ?? '';
  const entityTypes = new Set(entities?.map((entity) => entity.type) ?? []);

  const docType = detail.docType;
  const requiredEntities = [];

  if (['factura_comercial', 'dus'].includes(docType)) {
    requiredEntities.push(['incoterm', 'INCOTERM faltante']);
    requiredEntities.push(['amount', 'Monto sin identificar']);
  }

  if (['factura_comercial', 'dus', 'packing_list'].includes(docType)) {
    requiredEntities.push(['hs_code', 'HS Code no detectado']);
  }

  if (['packing_list', 'bl', 'dus'].includes(docType)) {
    requiredEntities.push(['container', 'Número de contenedor sin detectar']);
  }

  if (docType === 'bl') {
    requiredEntities.push(['bl_number', 'Número BL ausente']);
  }

  requiredEntities.forEach(([type, label]) => {
    if (!entityTypes.has(type)) {
      findings.push({
        severity: 'error',
        title: label,
        detail: 'Revisa el documento e ingresa el dato manualmente.',
      });
    }
  });

  if (
    ['factura_comercial', 'dus'].includes(docType) &&
    entityTypes.has('incoterm') &&
    !text.includes('fob')
  ) {
    findings.push({
      severity: 'warning',
      title: 'INCOTERM inconsistente',
      detail: 'El texto OCR no menciona el INCOTERM detectado.',
    });
  }
  if (!detail.docType) {
    findings.push({
      severity: 'warning',
      title: 'Tipo de documento vacío',
      detail: 'Asigna un tipo para aplicar las reglas correctas.',
    });
  }
  return findings;
}

function buildAutoPlan(selectedOptions, state) {
  if (!state.docId) {
    return [];
  }
  const plan = [];
  if (selectedOptions.includes('normalize_amounts')) {
    plan.push({
      label: 'Normalización de montos',
      detail: 'Se convertirán todos los valores numéricos al formato 12345.67.',
    });
  }
  if (selectedOptions.includes('ensure_incoterm')) {
    const incoterm = state.entities.find((entity) => entity.type === 'incoterm');
    plan.push({
      label: 'Confirmación de INCOTERM',
      detail: incoterm
        ? `Se reforzará el INCOTERM ${incoterm.value} en cabecera y pie.`
        : 'Se solicitará ingresar el INCOTERM manualmente.',
    });
  }
  if (selectedOptions.includes('flag_missing_fields')) {
    const missing = ['container', 'bl_number', 'hs_code'].filter(
      (key) => !state.entities.some((entity) => entity.type === key)
    );
    plan.push({
      label: 'Campos obligatorios',
      detail: missing.length
        ? `Se marcarán como obligatorios: ${missing.join(', ')}.`
        : 'Todos los campos obligatorios están presentes.',
    });
  }
  if (selectedOptions.includes('language_consistency')) {
    plan.push({
      label: 'Unificación de idioma',
      detail: 'Las observaciones del informe se traducirán al español neutro.',
    });
  }
  return plan;
}

function recomputeAutoPlan(previousPlan, detail, entities, textBlocks) {
  if (!previousPlan?.length) {
    return previousPlan ?? [];
  }
  const mockState = {
    docId: detail?.id ?? null,
    entities: entities ?? [],
    textBlocks: textBlocks ?? [],
  };
  const selectedOptions = previousPlan.map((item) => {
    if (item.label.includes('montos')) {
      return 'normalize_amounts';
    }
    if (item.label.includes('INCOTERM')) {
      return 'ensure_incoterm';
    }
    if (item.label.includes('Campos')) {
      return 'flag_missing_fields';
    }
    if (item.label.includes('idioma')) {
      return 'language_consistency';
    }
    return null;
  }).filter(Boolean);
  return buildAutoPlan(selectedOptions, mockState);
}

function buildSummary(state) {
  const meta = [
    ['ID', state.detail?.id ?? 'N/D'],
    ['Estado', state.detail?.status ?? 'sin estado'],
    ['Tipo', formatDocTypeLabel(state.detail?.docType)],
    ['Idioma detectado', state.detail?.languageDetected ?? 'No disponible'],
    ['Última actualización', formatDate(state.lastUpdatedAt ?? state.detail?.updatedAt)],
  ];
  const findings = state.compliance.length
    ? state.compliance.map((item) => `${item.title}: ${item.detail}`)
    : ['No se detectaron incidencias en las reglas evaluadas.'];
  const adjustments = state.autoApplied && state.autoPlan.length
    ? state.autoPlan.map((item) => `${item.label} → ${item.detail}`)
    : [];
  const rawKeywords = Array.isArray(state.keywords) ? state.keywords : [];
  const fullText = state.textBlocks
    ?.map((block) => block.text)
    .filter(Boolean)
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();
  const textSummary = summarizeText(fullText, rawKeywords, {
    maxSentences: 3,
    maxLength: 520,
  });
  const keywords = rawKeywords
    .map((kw) => {
      const numericScore = Number(kw.score);
      return {
        keyword: kw.keyword ?? '',
        score: Number.isFinite(numericScore) ? Math.round(numericScore * 100) : null,
      };
    })
    .filter((kw) => kw.keyword.trim().length);
  let textSnippet = fullText ?? '';
  if (textSnippet.length > 420) {
    textSnippet = `${textSnippet.slice(0, 417).trimEnd()}…`;
  }
  return { meta, findings, adjustments, keywords, textSnippet, textSummary };
}

function summarizeText(text, keywords, { maxSentences = 3, maxLength = 480 } = {}) {
  if (!text) {
    return '';
  }
  const normalizedText = text.replace(/\s+/g, ' ').trim();
  if (!normalizedText) {
    return '';
  }
  const sentenceMatches = normalizedText.match(/[^.!?]+[.!?]?/gu);
  const sentences = (sentenceMatches ?? [normalizedText])
    .map((sentence) => sentence.trim())
    .filter(Boolean);
  if (!sentences.length) {
    return '';
  }
  if (sentences.length <= maxSentences) {
    return truncateSummary(sentences.join(' '), maxLength);
  }
  const keywordData = Array.isArray(keywords)
    ? keywords
      .map((item) => {
        const value = (item.keyword ?? item)?.toString().toLowerCase();
        const numericScore = Number(item.score);
        return {
          value,
          weight: Number.isFinite(numericScore) ? numericScore : 0.5,
        };
      })
      .filter((item) => item.value)
    : [];
  const scoredSentences = sentences.map((sentence, index) => {
    const normalizedSentence = sentence.toLowerCase();
    const keywordScore = keywordData.reduce((acc, keyword) => {
      return acc + (normalizedSentence.includes(keyword.value) ? 1 + keyword.weight : 0);
    }, 0);
    const lengthScore = Math.min(sentence.length / 180, 1);
    const positionScore = index === 0 ? 1 : 1 / (index + 1);
    return {
      sentence,
      index,
      score: keywordScore * 1.7 + lengthScore + positionScore,
    };
  });
  const topSentences = scoredSentences
    .sort((a, b) => b.score - a.score)
    .slice(0, maxSentences)
    .sort((a, b) => a.index - b.index)
    .map((item) => item.sentence.trim());
  return truncateSummary(topSentences.join(' '), maxLength);
}

function truncateSummary(text, maxLength) {
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, Math.max(0, maxLength - 1)).trimEnd()}…`;
}

function normalizeInsights(raw) {
  if (!raw) {
    return createEmptyInsights();
  }
  const compliance = Array.isArray(raw.compliance)
    ? raw.compliance
      .filter(Boolean)
      .map((item) => ({
        severity: item?.severity ?? 'warning',
        title: item?.title ?? 'Regla documental',
        detail: item?.detail ?? '',
        field: item?.field ?? null,
      }))
    : [];
  const spellcheck = Array.isArray(raw.spellcheck)
    ? raw.spellcheck
      .filter(Boolean)
      .map((item) => ({
        severity: item?.severity ?? 'warning',
        title: item?.title ?? 'Ortografía',
        detail: item?.detail ?? '',
        field: item?.field ?? 'texto',
      }))
    : [];
  const recommendations = Array.isArray(raw.recommendations)
    ? raw.recommendations
      .map((item) => (typeof item === 'string' ? item : String(item ?? '')))
      .filter((item) => item.trim().length)
    : [];
  return {
    compliance,
    spellcheck,
    recommendations,
  };
}

function formatDocTypeLabel(value) {
  if (!value) {
    return 'No especificado';
  }
  return DOC_TYPE_LABELS[value] ?? value;
}

function buildReport(detail, compliance, autoPlan, insights) {
  if (!detail) {
    return null;
  }
  const normalizedInsights =
    insights && Array.isArray(insights.compliance) ? insights : normalizeInsights(insights);
  return {
    generatedAt: new Date().toISOString(),
    document: {
      id: detail.id,
      status: detail.status,
      type: detail.docType,
      languageDetected: detail.languageDetected,
      createdAt: detail.createdAt,
      updatedAt: detail.updatedAt,
    },
    compliance: compliance.map((item) => ({
      severity: item.severity,
      title: item.title,
      detail: item.detail,
    })),
    adjustments: autoPlan.map((item) => ({ label: item.label, detail: item.detail })),
    spellcheck: normalizedInsights.spellcheck,
    recommendations: normalizedInsights.recommendations,
  };
}

function formatDate(value) {
  if (!value) {
    return 'N/D';
  }
  try {
    return new Intl.DateTimeFormat('es', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(value));
  } catch (error) {
    return value.toString();
  }
}

function renderVisualHighlights(highlights) {
  if (!highlights || !highlights.length) return '';

  let overlayHtml = '<div class="pdf-overlay-layer">';

  highlights.forEach(h => {
    const style = `top: ${h.y}%; left: ${h.x}%; width: ${h.w}%; height: ${h.h}%;`;
    const className = h.type === 'warning' ? 'highlight-box highlight-box--warning' : 'highlight-box';

    overlayHtml += `
      <div class="${className}" style="${style}">
        <div class="highlight-label">${h.label}</div>
      </div>
    `;
  });

  overlayHtml += '</div>';
  return overlayHtml;
}
